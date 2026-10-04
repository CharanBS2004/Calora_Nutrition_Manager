import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:workmanager/workmanager.dart';
import '../network/api_client.dart';
import '../constants/api_constants.dart';

const String kMissingMealTaskName = "com.bmsce.aai.checkMissingMealsTask";

/// Top-level callback dispatcher required by Android WorkManager
@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    if (task == kMissingMealTaskName) {
      try {
        final apiClient = ApiClient();
        final alerts = await apiClient.get(ApiConstants.notifCheckMissing);
        if (alerts is List && alerts.isNotEmpty) {
          final notifPlugin = FlutterLocalNotificationsPlugin();
          await notifPlugin.initialize(
            const InitializationSettings(
              android: AndroidInitializationSettings('@mipmap/ic_launcher'),
            ),
          );
          for (var i = 0; i < alerts.length; i++) {
            final alert = alerts[i];
            final title =
                "${alert['meal_type'].toString().toUpperCase()} REMINDER";
            final body =
                alert['message'] ?? "You haven't logged your meal yet.";

            await notifPlugin.show(
              i + 100,
              title,
              body,
              const NotificationDetails(
                android: AndroidNotificationDetails(
                  'meal_reminders_channel',
                  'Meal Reminders',
                  channelDescription:
                      'Proactive reminders when scheduled meals are unlogged',
                  importance: Importance.high,
                  priority: Priority.high,
                  showWhen: true,
                ),
              ),
            );
          }
        }
      } catch (e) {
        debugPrint("WorkManager background check error: $e");
        return Future.value(false);
      }
    }
    return Future.value(true);
  });
}

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FlutterLocalNotificationsPlugin _notificationsPlugin =
      FlutterLocalNotificationsPlugin();
  bool _initialized = false;

  Future<void> initialize() async {
    if (_initialized) return;

    // 1. Initialize Flutter Local Notifications
    const AndroidInitializationSettings androidSettings =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    const InitializationSettings initSettings =
        InitializationSettings(android: androidSettings);

    await _notificationsPlugin.initialize(
      initSettings,
      onDidReceiveNotificationResponse: (details) {
        debugPrint("Notification tapped: ${details.payload}");
      },
    );

    // 2. Initialize Android WorkManager for background periodic scheduling
    try {
      await Workmanager().initialize(
        callbackDispatcher,
        isInDebugMode: kDebugMode,
      );
    } catch (e) {
      debugPrint("Workmanager init error: $e");
    }

    _initialized = true;
  }

  /// Schedule periodic background missing meal check (e.g. every 15-30 minutes on Android)
  Future<void> scheduleBackgroundChecks({bool enabled = true}) async {
    if (!enabled) {
      await Workmanager().cancelByUniqueName(kMissingMealTaskName);
      return;
    }

    await Workmanager().registerPeriodicTask(
      kMissingMealTaskName,
      kMissingMealTaskName,
      frequency: const Duration(minutes: 15),
      constraints: Constraints(
        networkType: NetworkType.connected,
      ),
      existingWorkPolicy: ExistingWorkPolicy.keep,
    );
  }

  Future<bool> requestNotificationPermission() async {
    await initialize();
    final androidNotifications =
        _notificationsPlugin.resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();
    if (androidNotifications == null) return true;

    await androidNotifications.requestNotificationsPermission();
    return await androidNotifications.areNotificationsEnabled() ?? false;
  }

  /// Manually trigger a test meal reminder notification
  Future<void> showMealReminderNotification({
    required String mealType,
    required String message,
  }) async {
    await _notificationsPlugin.show(
      DateTime.now().millisecond,
      "🍽️ ${mealType.toUpperCase()} CHECK-IN",
      message,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'meal_reminders_channel',
          'Meal Reminders',
          channelDescription:
              'Proactive reminders when scheduled meals are unlogged',
          importance: Importance.high,
          priority: Priority.high,
        ),
      ),
    );
  }
}
