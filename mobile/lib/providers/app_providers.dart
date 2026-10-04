import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/network/api_client.dart';
import '../core/constants/api_constants.dart';
import '../models/app_models.dart';
import '../core/services/health_connect_service.dart';

// ----------------- Theme Provider -----------------
class ThemeProvider with ChangeNotifier {
  ThemeMode _themeMode = ThemeMode.system;
  ThemeMode get themeMode => _themeMode;

  ThemeProvider() {
    _loadTheme();
  }

  Future<void> _loadTheme() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString('app_theme_mode');
    if (saved == 'light') _themeMode = ThemeMode.light;
    if (saved == 'dark') _themeMode = ThemeMode.dark;
    if (saved == 'system') _themeMode = ThemeMode.system;
    notifyListeners();
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    _themeMode = mode;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    if (mode == ThemeMode.light)
      await prefs.setString('app_theme_mode', 'light');
    if (mode == ThemeMode.dark) await prefs.setString('app_theme_mode', 'dark');
    if (mode == ThemeMode.system)
      await prefs.setString('app_theme_mode', 'system');
  }
}

// ----------------- Auth Provider -----------------
class AuthProvider with ChangeNotifier {
  final ApiClient _api = ApiClient();
  bool _isLoading = false;
  bool get isLoading => _isLoading;

  String? _token;
  String? get token => _token;
  bool get isAuthenticated => _token != null && _token!.isNotEmpty;

  String _userName = "User";
  String get userName => _userName;

  String _userEmail = "";
  String get userEmail => _userEmail;

  int _userId = 0;
  int get userId => _userId;

  Future<bool> tryAutoLogin() async {
    _token = await _api.getToken();
    if (_token != null) {
      try {
        final res = await _api.get(ApiConstants.authMe);
        _userId = res['user_id'] ?? 0;
        _userEmail = res['email'] ?? '';
        _userName = res['name'] ?? 'User';
        notifyListeners();
        return true;
      } catch (e) {
        if (e.toString().contains('Unauthorized:')) {
          await logout();
          return false;
        }
        debugPrint("Could not verify saved login; keeping it for retry: $e");
        notifyListeners();
        return true;
      }
    }
    return false;
  }

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    notifyListeners();
    try {
      final res = await _api.post(ApiConstants.authLogin, body: {
        'email': email.trim(),
        'password': password,
      });
      _token = res['access_token'];
      _userId = res['user_id'];
      _userEmail = res['email'];
      _userName = res['name'] ?? 'User';
      await _api.setToken(_token);
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      rethrow;
    }
  }

  Future<bool> signup(String name, String email, String password) async {
    _isLoading = true;
    notifyListeners();
    try {
      final res = await _api.post(ApiConstants.authSignup, body: {
        'name': name.trim(),
        'email': email.trim(),
        'password': password,
      });
      _token = res['access_token'];
      _userId = res['user_id'];
      _userEmail = res['email'];
      _userName = res['name'] ?? name;
      await _api.setToken(_token);
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      rethrow;
    }
  }

  Future<void> logout() async {
    _token = null;
    _userId = 0;
    _userName = "User";
    _userEmail = "";
    await _api.setToken(null);
    notifyListeners();
  }
}

// ----------------- Nutrition & Dashboard Provider -----------------
class NutritionProvider with ChangeNotifier {
  final ApiClient _api = ApiClient();

  DailyAnalyticsData? _dailyData;
  DailyAnalyticsData? get dailyData => _dailyData;

  List<MealRecord> _todayMeals = [];
  List<MealRecord> get todayMeals => _todayMeals;

  List<RecipeItem> _savedRecipes = [];
  List<RecipeItem> get savedRecipes => _savedRecipes;

  bool _isLoading = false;
  bool get isLoading => _isLoading;
  String? _dashboardError;
  String? get dashboardError => _dashboardError;
  Future<void>? _dashboardRefresh;

  Future<void> refreshDashboard() async {
    if (_dashboardRefresh != null) {
      return _dashboardRefresh!;
    }
    final refresh = _performDashboardRefresh();
    _dashboardRefresh = refresh;
    try {
      await refresh;
    } finally {
      if (identical(_dashboardRefresh, refresh)) {
        _dashboardRefresh = null;
      }
    }
  }

  Future<T?> _fetchDashboardValue<T>(
      String endpoint, T Function(dynamic) parse) async {
    try {
      return parse(await _api.get(endpoint));
    } catch (e) {
      debugPrint("Error loading $endpoint: $e");
      return null;
    }
  }

  Future<void> _performDashboardRefresh() async {
    _isLoading = true;
    _dashboardError = null;
    notifyListeners();
    try {
      final results = await Future.wait<Object?>([
        _fetchDashboardValue<DailyAnalyticsData>(
          ApiConstants.analyticsDaily,
          (response) => response == null
              ? throw const FormatException(
                  'Daily analytics response was empty')
              : DailyAnalyticsData.fromJson(response),
        ),
        _fetchDashboardValue<List<MealRecord>>(
          ApiConstants.mealsToday,
          (response) => response is List
              ? response.map((item) => MealRecord.fromJson(item)).toList()
              : throw const FormatException('Meals response was not a list'),
        ),
        _fetchDashboardValue<List<RecipeItem>>(
          ApiConstants.recipes,
          (response) => response is List
              ? response.map((item) => RecipeItem.fromJson(item)).toList()
              : throw const FormatException('Recipes response was not a list'),
        ),
      ]);
      final daily = results[0] as DailyAnalyticsData?;
      final meals = results[1] as List<MealRecord>?;
      final recipes = results[2] as List<RecipeItem>?;
      if (daily != null) {
        _dailyData = daily;
      } else {
        _dashboardError = 'Could not load today’s nutrition data.';
      }
      if (meals != null) _todayMeals = meals;
      if (recipes != null) _savedRecipes = recipes;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> logMealDirect({
    required String mealType,
    required List<Map<String, dynamic>> items,
    String? notes,
  }) async {
    await _api.post(ApiConstants.meals, body: {
      'meal_type': mealType,
      'items': items,
      'notes': notes,
    });
    await refreshDashboard();
  }

  Future<HealthDataSummary?> syncHealthConnectTelemetry() async {
    final hcService = HealthConnectService();
    final summary = await hcService.syncHealthData();
    if (summary != null) {
      await refreshDashboard();
    }
    return summary;
  }
}

// ----------------- AI Coach Provider -----------------
class CoachProvider with ChangeNotifier {
  final ApiClient _api = ApiClient();
  final List<ChatMessageModel> _messages = [];
  List<ChatMessageModel> get messages => _messages;

  bool _isSending = false;
  bool get isSending => _isSending;

  Future<void> loadHistory() async {
    try {
      final res = await _api.get(ApiConstants.coachHistory);
      if (res is List) {
        _messages.clear();
        for (var item in res) {
          _messages.add(ChatMessageModel.fromJson(item));
        }
        notifyListeners();
      }
    } catch (e) {
      debugPrint("Error loading chat history: $e");
    }
  }

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;

    // Add user message locally
    final userMsg = ChatMessageModel(
      id: DateTime.now().millisecondsSinceEpoch,
      role: 'user',
      content: text.trim(),
      uncertaintyFlag: false,
      createdAt: DateTime.now(),
    );
    _messages.add(userMsg);
    _isSending = true;
    notifyListeners();

    try {
      final res = await _api.post(ApiConstants.coachChat, body: {
        'message': text.trim(),
      });
      final assistantMsg = ChatMessageModel.fromJson(res);
      _messages.add(assistantMsg);
    } catch (e) {
      _messages.add(
        ChatMessageModel(
          id: DateTime.now().millisecondsSinceEpoch,
          role: 'assistant',
          content:
              "I encountered a connection issue while analyzing your nutrition data. Please verify your connection and try again.",
          uncertaintyFlag: false,
          createdAt: DateTime.now(),
        ),
      );
    } finally {
      _isSending = false;
      notifyListeners();
    }
  }

  Future<void> clearHistory() async {
    await _api.delete(ApiConstants.coachHistory);
    _messages.clear();
    notifyListeners();
  }
}
