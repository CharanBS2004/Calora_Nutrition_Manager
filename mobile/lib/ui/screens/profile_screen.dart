import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/api_constants.dart';
import '../../core/network/api_client.dart';
import '../../core/services/health_connect_service.dart';
import '../../core/services/notification_service.dart';
import '../../core/theme/app_theme.dart';
import '../../models/app_models.dart';
import '../../providers/app_providers.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final ApiClient _api = ApiClient();
  final HealthConnectService _hcService = HealthConnectService();

  bool _isLoading = false;
  UserProfile? _profile;
  NutritionGoals? _goals;

  // Notification settings state
  bool _remindersEnabled = true;
  String _quietStart = "22:00";
  String _quietEnd = "07:00";
  String _breakfastTime = "08:30";
  String _lunchTime = "13:00";
  String _dinnerTime = "20:00";
  String _snackTime = "17:00";
  bool _breakfastEnabled = true;
  bool _lunchEnabled = true;
  bool _dinnerEnabled = true;
  bool _snackEnabled = false;

  bool _isHcConnected = false;
  HealthConnectStatus _hcStatus = HealthConnectStatus.disconnected;

  @override
  void initState() {
    super.initState();
    _loadProfileData();
    _checkHealthConnect();
    _loadNotificationSettings();
  }

  Future<void> _loadProfileData() async {
    setState(() => _isLoading = true);
    try {
      final pRes = await _api.get(ApiConstants.userProfile);
      if (pRes != null) {
        _profile = UserProfile.fromJson(pRes);
      }

      final gRes = await _api.get(ApiConstants.userGoals);
      if (gRes != null) {
        _goals = NutritionGoals.fromJson(gRes);
      }
    } catch (e) {
      debugPrint("Error loading profile: $e");
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _checkHealthConnect() async {
    final status = await _hcService.checkAvailability();
    if (mounted) {
      setState(() {
        _hcStatus = status;
        _isHcConnected = status == HealthConnectStatus.connected;
      });
    }
  }

  Future<void> _loadNotificationSettings() async {
    try {
      final res = await _api.get(ApiConstants.notifSettings);
      if (res != null && mounted) {
        setState(() {
          _remindersEnabled = res['reminders_enabled'] ?? true;
          _quietStart = res['quiet_hours_start'] ?? "22:00";
          _quietEnd = res['quiet_hours_end'] ?? "07:00";
          _breakfastTime = res['breakfast_time'] ?? "08:30";
          _lunchTime = res['lunch_time'] ?? "13:00";
          _dinnerTime = res['dinner_time'] ?? "20:00";
          _snackTime = res['snack_time'] ?? "17:00";
          _breakfastEnabled = res['breakfast_enabled'] ?? true;
          _lunchEnabled = res['lunch_enabled'] ?? true;
          _dinnerEnabled = res['dinner_enabled'] ?? true;
          _snackEnabled = res['snack_enabled'] ?? false;
        });
      }
    } catch (e) {
      debugPrint("Error loading notif settings: $e");
    }
  }

  Future<void> _saveNotificationSettings() async {
    try {
      final notifService = NotificationService();
      final notificationsAllowed = !_remindersEnabled ||
          await notifService.requestNotificationPermission();
      final payload = {
        'reminders_enabled': _remindersEnabled,
        'quiet_hours_start': _quietStart,
        'quiet_hours_end': _quietEnd,
        'breakfast_time': _breakfastTime,
        'lunch_time': _lunchTime,
        'dinner_time': _dinnerTime,
        'snack_time': _snackTime,
        'breakfast_enabled': _breakfastEnabled,
        'lunch_enabled': _lunchEnabled,
        'dinner_enabled': _dinnerEnabled,
        'snack_enabled': _snackEnabled,
      };
      await _api.put(ApiConstants.notifSettings, body: payload);

      await notifService.scheduleBackgroundChecks(enabled: _remindersEnabled);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              notificationsAllowed
                  ? "Reminder settings saved."
                  : "Settings saved, but notifications are blocked. Allow them in app settings to receive reminders.",
            ),
            backgroundColor: notificationsAllowed
                ? AppTheme.sagePrimary
                : Theme.of(context).colorScheme.error,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Failed to save settings: $e")),
        );
      }
    }
  }

  Future<void> _connectHealthConnect() async {
    try {
      final status = await _hcService.checkAvailability();
      if (status == HealthConnectStatus.notInstalled) {
        await _hcService.installHealthConnect();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content:
                  Text("Install Health Connect, then return here to connect."),
            ),
          );
        }
        return;
      }
      if (status == HealthConnectStatus.notSupported) {
        throw UnsupportedError("Health Connect is only available on Android.");
      }

      final granted = await _hcService.requestPermissions();
      if (!granted) {
        await _checkHealthConnect();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                "Grant Calora health-data and activity permissions in Health Connect to sync.",
              ),
            ),
          );
        }
        return;
      }

      final nutritionProv =
          Provider.of<NutritionProvider>(context, listen: false);
      final summary = await nutritionProv.syncHealthConnectTelemetry();
      await _checkHealthConnect();
      if (mounted && summary != null) {
        final burnMessage = summary.totalCaloriesBurned > 0
            ? "${summary.totalCaloriesBurned.round()} total kcal"
            : "total calories unavailable; ${summary.activeCaloriesBurned.round()} active kcal";
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              "Health Connect synced: $burnMessage, ${summary.steps} steps.",
            ),
            backgroundColor: AppTheme.sagePrimary,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Health Connect sync failed: $e")),
        );
      }
    }
  }

  void _showEditGoalsDialog() {
    final calCtrl = TextEditingController(
        text: (_goals?.calorieTarget ?? 2000).round().toString());
    final pCtrl = TextEditingController(
        text: (_goals?.proteinG ?? 75).round().toString());
    final cCtrl =
        TextEditingController(text: (_goals?.carbG ?? 250).round().toString());
    final fCtrl =
        TextEditingController(text: (_goals?.fatG ?? 65).round().toString());
    final fibCtrl =
        TextEditingController(text: (_goals?.fiberG ?? 30).round().toString());

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Edit Daily Nutrition Goals"),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                  controller: calCtrl,
                  keyboardType: TextInputType.number,
                  decoration:
                      const InputDecoration(labelText: "Calories (kcal)")),
              TextField(
                  controller: pCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: "Protein (g)")),
              TextField(
                  controller: cCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: "Carbs (g)")),
              TextField(
                  controller: fCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: "Fat (g)")),
              TextField(
                  controller: fibCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: "Fiber (g)")),
            ],
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx), child: const Text("Cancel")),
          FilledButton(
            onPressed: () async {
              Navigator.pop(ctx);
              try {
                final payload = {
                  'calorie_target': double.tryParse(calCtrl.text) ?? 2000.0,
                  'protein_g': double.tryParse(pCtrl.text) ?? 75.0,
                  'carb_g': double.tryParse(cCtrl.text) ?? 250.0,
                  'fat_g': double.tryParse(fCtrl.text) ?? 65.0,
                  'fiber_g': double.tryParse(fibCtrl.text) ?? 30.0,
                  'water_ml': 2500.0,
                };
                await _api.put(ApiConstants.userGoals, body: payload);
                await _loadProfileData();
                if (mounted) {
                  Provider.of<NutritionProvider>(context, listen: false)
                      .refreshDashboard();
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                        content: Text("Goals updated!"),
                        backgroundColor: AppTheme.sagePrimary),
                  );
                }
              } catch (e) {
                if (mounted)
                  ScaffoldMessenger.of(context)
                      .showSnackBar(SnackBar(content: Text("Error: $e")));
              }
            },
            child: const Text("Save Goals"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final authProv = Provider.of<AuthProvider>(context);
    final themeProv = Provider.of<ThemeProvider>(context);

    return Scaffold(
      appBar: AppBar(title: const Text("Profile & Settings")),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // User Profile Header Card
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Row(
                        children: [
                          CircleAvatar(
                            radius: 30,
                            backgroundColor: theme.colorScheme.primary,
                            child: Text(
                              (authProv.userName.isNotEmpty
                                      ? authProv.userName[0]
                                      : "U")
                                  .toUpperCase(),
                              style: const TextStyle(
                                  fontSize: 24,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white),
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(authProv.userName,
                                    style: theme.textTheme.titleMedium
                                        ?.copyWith(
                                            fontWeight: FontWeight.bold)),
                                const SizedBox(height: 2),
                                Text(authProv.userEmail,
                                    style: TextStyle(
                                        color: theme.textTheme.bodySmall?.color,
                                        fontSize: 13)),
                                const SizedBox(height: 4),
                                if (_profile?.dietaryPreference != null)
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 8, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: AppTheme.sagePrimary
                                          .withOpacity(0.15),
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: Text(
                                      _profile!.dietaryPreference!,
                                      style: const TextStyle(
                                          fontSize: 11,
                                          color: AppTheme.sagePrimary,
                                          fontWeight: FontWeight.bold),
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Nutrition Goals Card
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text("Daily Nutrition Goals",
                                  style: theme.textTheme.titleMedium),
                              IconButton(
                                icon: const Icon(Icons.edit_outlined, size: 20),
                                onPressed: _showEditGoalsDialog,
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceAround,
                            children: [
                              _goalPill(
                                  "Calories",
                                  "${(_goals?.calorieTarget ?? 2000).round()} kcal",
                                  AppTheme.deepTealAccent),
                              _goalPill(
                                  "Protein",
                                  "${(_goals?.proteinG ?? 75).round()}g",
                                  AppTheme.proteinColor),
                              _goalPill(
                                  "Carbs",
                                  "${(_goals?.carbG ?? 250).round()}g",
                                  AppTheme.carbColor),
                              _goalPill(
                                  "Fat",
                                  "${(_goals?.fatG ?? 65).round()}g",
                                  AppTheme.fatColor),
                              _goalPill(
                                  "Fiber",
                                  "${(_goals?.fiberG ?? 30).round()}g",
                                  AppTheme.fiberColor),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Android Health Connect Card
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(Icons.health_and_safety_rounded,
                                  color: theme.colorScheme.primary),
                              const SizedBox(width: 8),
                              Text("Android Health Connect",
                                  style: theme.textTheme.titleMedium),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(
                            "Connect Google Fit to Health Connect, then grant Calora permission to read today's activity and calorie data.",
                            style: TextStyle(
                                fontSize: 13,
                                color: theme.textTheme.bodyMedium?.color
                                    ?.withOpacity(0.7)),
                          ),
                          const SizedBox(height: 12),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Row(
                                children: [
                                  Icon(
                                    _isHcConnected
                                        ? Icons.check_circle
                                        : Icons.radio_button_unchecked,
                                    size: 16,
                                    color: _isHcConnected
                                        ? Colors.green
                                        : Colors.grey,
                                  ),
                                  const SizedBox(width: 6),
                                  Text(
                                    _isHcConnected
                                        ? "Connected"
                                        : _hcStatus ==
                                                HealthConnectStatus.notInstalled
                                            ? "Health Connect not installed"
                                            : _hcStatus ==
                                                    HealthConnectStatus
                                                        .permissionsNeeded
                                                ? "Permission needed"
                                                : _hcStatus ==
                                                        HealthConnectStatus
                                                            .notSupported
                                                    ? "Not supported"
                                                    : "Disconnected",
                                    style: const TextStyle(
                                        fontWeight: FontWeight.w600,
                                        fontSize: 13),
                                  ),
                                ],
                              ),
                              FilledButton.tonal(
                                onPressed: _connectHealthConnect,
                                child: Text(
                                  _hcStatus == HealthConnectStatus.notInstalled
                                      ? "Install"
                                      : _isHcConnected
                                          ? "Sync Now"
                                          : "Connect",
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Proactive Notifications & Quiet Hours Card
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(12.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(Icons.notifications_active_outlined,
                                  color: theme.colorScheme.primary),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text("Meal Reminders",
                                    style: theme.textTheme.titleMedium),
                              ),
                              Switch(
                                value: _remindersEnabled,
                                onChanged: (val) =>
                                    setState(() => _remindersEnabled = val),
                                materialTapTargetSize:
                                    MaterialTapTargetSize.shrinkWrap,
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            "Get notified about scheduled meals.",
                            style: TextStyle(
                                fontSize: 12,
                                color: theme.textTheme.bodyMedium?.color
                                    ?.withOpacity(0.7)),
                          ),
                          const Divider(height: 20),

                          // Quiet Hours
                          Text("Quiet Hours (No notifications)",
                              style: theme.textTheme.labelLarge),
                          const SizedBox(height: 4),
                          Row(
                            children: [
                              Expanded(
                                child: OutlinedButton(
                                  onPressed: () => _pickTime(
                                      _quietStart,
                                      (val) =>
                                          setState(() => _quietStart = val)),
                                  child: Text("Start: $_quietStart"),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: OutlinedButton(
                                  onPressed: () => _pickTime(_quietEnd,
                                      (val) => setState(() => _quietEnd = val)),
                                  child: Text("End: $_quietEnd"),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),

                          // Meal Schedules
                          Text("Meal Schedules",
                              style: theme.textTheme.labelLarge),
                          const SizedBox(height: 6),
                          _scheduleRow(
                              "Breakfast",
                              _breakfastTime,
                              _breakfastEnabled,
                              (t) => setState(() => _breakfastTime = t),
                              (e) => setState(() => _breakfastEnabled = e)),
                          _scheduleRow(
                              "Lunch",
                              _lunchTime,
                              _lunchEnabled,
                              (t) => setState(() => _lunchTime = t),
                              (e) => setState(() => _lunchEnabled = e)),
                          _scheduleRow(
                              "Dinner",
                              _dinnerTime,
                              _dinnerEnabled,
                              (t) => setState(() => _dinnerTime = t),
                              (e) => setState(() => _dinnerEnabled = e)),
                          _scheduleRow(
                              "Snacks",
                              _snackTime,
                              _snackEnabled,
                              (t) => setState(() => _snackTime = t),
                              (e) => setState(() => _snackEnabled = e)),

                          const SizedBox(height: 12),
                          SizedBox(
                            width: double.infinity,
                            child: FilledButton.tonal(
                              onPressed: _saveNotificationSettings,
                              child: const Text("Save Reminder Settings"),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // App Theme Preferences Card
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text("Appearance",
                              style: theme.textTheme.titleMedium),
                          const SizedBox(height: 12),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                            children: [
                              _themeOption("Light", ThemeMode.light,
                                  Icons.light_mode_outlined, themeProv),
                              _themeOption("Dark", ThemeMode.dark,
                                  Icons.dark_mode_outlined, themeProv),
                              _themeOption("System", ThemeMode.system,
                                  Icons.brightness_auto_outlined, themeProv),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Logout Button
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: OutlinedButton.icon(
                      style:
                          OutlinedButton.styleFrom(foregroundColor: Colors.red),
                      onPressed: () async {
                        await authProv.logout();
                      },
                      icon: const Icon(Icons.logout_rounded),
                      label: const Text("Log Out"),
                    ),
                  ),
                  const SizedBox(height: 32),
                ],
              ),
            ),
    );
  }

  Widget _goalPill(String label, String value, Color color) {
    return Column(
      children: [
        Text(label, style: const TextStyle(fontSize: 11, color: Colors.grey)),
        const SizedBox(height: 2),
        Text(value,
            style: TextStyle(
                fontSize: 12, fontWeight: FontWeight.bold, color: color)),
      ],
    );
  }

  Widget _scheduleRow(String name, String time, bool enabled,
      Function(String) onTimeChanged, Function(bool) onToggle) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Checkbox(value: enabled, onChanged: (v) => onToggle(v ?? false)),
              Text(name, style: const TextStyle(fontSize: 13)),
            ],
          ),
          TextButton(
            onPressed: enabled ? () => _pickTime(time, onTimeChanged) : null,
            child: Text(time,
                style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: enabled ? null : Colors.grey)),
          ),
        ],
      ),
    );
  }

  Future<void> _pickTime(String current, Function(String) onSelected) async {
    final parts = current.split(":");
    final initial = TimeOfDay(
      hour: int.tryParse(parts[0]) ?? 12,
      minute: parts.length > 1 ? (int.tryParse(parts[1]) ?? 0) : 0,
    );

    final picked = await showTimePicker(context: context, initialTime: initial);
    if (picked != null) {
      final h = picked.hour.toString().padLeft(2, '0');
      final m = picked.minute.toString().padLeft(2, '0');
      onSelected("$h:$m");
    }
  }

  Widget _themeOption(
      String label, ThemeMode mode, IconData icon, ThemeProvider prov) {
    final isSelected = prov.themeMode == mode;
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () => prov.setThemeMode(mode),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected
              ? Theme.of(context).colorScheme.primary.withOpacity(0.15)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
              color: isSelected
                  ? Theme.of(context).colorScheme.primary
                  : Colors.grey.withOpacity(0.3)),
        ),
        child: Column(
          children: [
            Icon(icon,
                color: isSelected
                    ? Theme.of(context).colorScheme.primary
                    : Colors.grey),
            const SizedBox(height: 4),
            Text(label,
                style: TextStyle(
                    fontSize: 12,
                    fontWeight:
                        isSelected ? FontWeight.bold : FontWeight.normal)),
          ],
        ),
      ),
    );
  }
}
