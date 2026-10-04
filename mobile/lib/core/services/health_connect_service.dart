import 'dart:io';
import 'dart:math' show max;

import 'package:flutter/foundation.dart';
import 'package:health/health.dart';
import 'package:permission_handler/permission_handler.dart';

import '../network/api_client.dart';
import '../constants/api_constants.dart';

enum HealthConnectStatus {
  connected,
  permissionsNeeded,
  notInstalled,
  notSupported,
  disconnected
}

class HealthDataSummary {
  final DateTime date;
  final double totalCaloriesBurned;
  final double activeCaloriesBurned;
  final int steps;
  final double distanceMeters;
  final int activeMinutes;
  final double? restingHeartRate;
  final String source;

  HealthDataSummary({
    required this.date,
    required this.totalCaloriesBurned,
    required this.activeCaloriesBurned,
    required this.steps,
    required this.distanceMeters,
    required this.activeMinutes,
    this.restingHeartRate,
    required this.source,
  });

  Map<String, dynamic> toJson() => {
        'recorded_date':
            "${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}",
        'total_calories_burned': totalCaloriesBurned,
        'active_calories_burned': activeCaloriesBurned,
        'steps': steps,
        'distance_m': distanceMeters,
        'active_minutes': activeMinutes,
        'resting_heart_rate': restingHeartRate,
        'source': source,
      };
}

class HealthConnectService {
  static final HealthConnectService _instance =
      HealthConnectService._internal();
  factory HealthConnectService() => _instance;
  HealthConnectService._internal();

  static const List<HealthDataType> _readTypes = [
    HealthDataType.TOTAL_CALORIES_BURNED,
    HealthDataType.ACTIVE_ENERGY_BURNED,
    HealthDataType.STEPS,
    HealthDataType.DISTANCE_DELTA,
    HealthDataType.RESTING_HEART_RATE,
    HealthDataType.WORKOUT,
  ];

  final Health _health = Health();
  bool _configured = false;
  HealthConnectStatus _status = HealthConnectStatus.disconnected;
  HealthConnectStatus get status => _status;

  DateTime? _lastSyncTime;
  DateTime? get lastSyncTime => _lastSyncTime;

  HealthDataSummary? _latestData;
  HealthDataSummary? get latestData => _latestData;

  Future<void> _configure() async {
    if (_configured) return;
    await _health.configure();
    _configured = true;
  }

  Future<HealthConnectStatus> checkAvailability() async {
    if (kIsWeb || !Platform.isAndroid) {
      _status = HealthConnectStatus.notSupported;
      return _status;
    }

    try {
      await _configure();
      if (!await _health.isHealthConnectAvailable()) {
        _status = HealthConnectStatus.notInstalled;
      } else {
        final hasPermission = await _health.hasPermissions(_readTypes);
        _status = hasPermission == true
            ? HealthConnectStatus.connected
            : HealthConnectStatus.permissionsNeeded;
      }
    } catch (e) {
      debugPrint("Health Connect availability check failed: $e");
      _status = HealthConnectStatus.disconnected;
    }
    return _status;
  }

  Future<bool> isHealthConnectAvailable() async {
    final status = await checkAvailability();
    return status != HealthConnectStatus.notSupported &&
        status != HealthConnectStatus.notInstalled;
  }

  Future<bool> hasPermissions() async {
    await checkAvailability();
    return _status == HealthConnectStatus.connected;
  }

  Future<void> installHealthConnect() async {
    await _configure();
    await _health.installHealthConnect();
  }

  Future<bool> requestPermissions() async {
    try {
      await _configure();
      if (!await _health.isHealthConnectAvailable()) {
        _status = HealthConnectStatus.notInstalled;
        return false;
      }

      final activityPermission = await Permission.activityRecognition.request();
      if (!activityPermission.isGranted) {
        _status = HealthConnectStatus.permissionsNeeded;
        return false;
      }

      if (await _health.hasPermissions(_readTypes) != true) {
        final authorized = await _health.requestAuthorization(_readTypes);
        if (!authorized) {
          _status = HealthConnectStatus.permissionsNeeded;
          return false;
        }
      }

      _status = await _health.hasPermissions(_readTypes) == true
          ? HealthConnectStatus.connected
          : HealthConnectStatus.permissionsNeeded;
      return _status == HealthConnectStatus.connected;
    } catch (e) {
      debugPrint("Health Connect permission request failed: $e");
      _status = HealthConnectStatus.permissionsNeeded;
      return false;
    }
  }

  Future<HealthDataSummary?> syncHealthData() async {
    await _configure();
    if (!await _health.isHealthConnectAvailable()) {
      _status = HealthConnectStatus.notInstalled;
      return null;
    }
    if (await _health.hasPermissions(_readTypes) != true) {
      _status = HealthConnectStatus.permissionsNeeded;
      return null;
    }

    final now = DateTime.now();
    final startOfDay = DateTime(now.year, now.month, now.day);
    final points = await _health.getHealthDataFromTypes(
      types: _readTypes,
      startTime: startOfDay,
      endTime: now,
    );

    double sumWithoutOverlappingRecords(HealthDataType type) {
      final records = points.where((point) => point.type == type).map((point) {
        final value =
            (point.value as NumericHealthValue).numericValue.toDouble();
        final from =
            point.dateFrom.isAfter(startOfDay) ? point.dateFrom : startOfDay;
        final to = point.dateTo.isBefore(now) ? point.dateTo : now;
        return (from: from, to: to, value: value);
      }).toList();
      final boundaries = records
          .where((record) => record.to.isAfter(record.from))
          .expand((record) => [record.from, record.to])
          .toSet()
          .toList()
        ..sort();

      var total = records
          .where((record) => !record.to.isAfter(record.from))
          .fold<double>(0, (sum, record) => sum + record.value);
      for (var i = 0; i + 1 < boundaries.length; i++) {
        final from = boundaries[i];
        final to = boundaries[i + 1];
        final durationSeconds = to.difference(from).inSeconds;
        if (durationSeconds <= 0) continue;
        final rate = records
            .where(
          (record) => !record.from.isAfter(from) && !record.to.isBefore(to),
        )
            .fold<double>(
          0,
          (highestRate, record) {
            final recordSeconds = record.to.difference(record.from).inSeconds;
            if (recordSeconds <= 0) return highestRate;
            return max(
              highestRate,
              record.value / recordSeconds,
            );
          },
        );
        total += rate * durationSeconds;
      }
      return total;
    }

    final totalCalories =
        sumWithoutOverlappingRecords(HealthDataType.TOTAL_CALORIES_BURNED);
    final activeCalories =
        sumWithoutOverlappingRecords(HealthDataType.ACTIVE_ENERGY_BURNED);
    final distanceMeters =
        sumWithoutOverlappingRecords(HealthDataType.DISTANCE_DELTA);
    final steps = await _health.getTotalStepsInInterval(startOfDay, now) ?? 0;
    final restingHeartRates = points
        .where((point) => point.type == HealthDataType.RESTING_HEART_RATE)
        .map((point) =>
            (point.value as NumericHealthValue).numericValue.toDouble())
        .toList();
    final activeMinutes = points
        .where((point) => point.type == HealthDataType.WORKOUT)
        .fold<int>(0, (total, point) {
      final from =
          point.dateFrom.isAfter(startOfDay) ? point.dateFrom : startOfDay;
      final to = point.dateTo.isBefore(now) ? point.dateTo : now;
      return total + (to.isAfter(from) ? to.difference(from).inMinutes : 0);
    });

    final summary = HealthDataSummary(
      date: now,
      totalCaloriesBurned: totalCalories,
      activeCaloriesBurned: activeCalories,
      steps: steps,
      distanceMeters: distanceMeters,
      activeMinutes: activeMinutes,
      restingHeartRate: restingHeartRates.isEmpty
          ? null
          : restingHeartRates.reduce((a, b) => a + b) /
              restingHeartRates.length,
      source: totalCalories > 0
          ? 'health_connect'
          : 'health_connect_total_calories_unavailable',
    );

    await ApiClient().post(ApiConstants.healthRecords, body: summary.toJson());

    _latestData = summary;
    _lastSyncTime = DateTime.now();
    _status = HealthConnectStatus.connected;
    return summary;
  }
}
