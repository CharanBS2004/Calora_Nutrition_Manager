class ApiConstants {
  // Default Android emulator host for local development: 10.0.2.2 points to host machine
  // For physical devices on the same Wi-Fi, change to your LAN IP (e.g. 192.168.1.X)
  static const String defaultBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: "http://10.0.2.2:8000/api/v1",
  );

  static const String authSignup = "/auth/signup";
  static const String authLogin = "/auth/login";
  static const String authMe = "/auth/me";
  static const String authRefresh = "/auth/refresh";

  static const String userProfile = "/users/profile";
  static const String userGoals = "/users/goals";

  static const String foodsSearch = "/foods/search";
  static const String foodsCategories = "/foods/categories";

  static const String recipes = "/recipes";
  static const String recipesCalculate = "/recipes/calculate";

  static const String meals = "/meals";
  static const String mealsToday = "/meals/today";
  static const String mealsParseText = "/meals/parse-text";

  static const String healthRecords = "/health/records";
  static const String healthEnergyBalance = "/health/energy-balance";

  static const String notifSettings = "/notifications/settings";
  static const String notifCheckMissing = "/notifications/check-missing-meals";

  static const String analyticsDaily = "/analytics/daily";
  static const String analyticsWeekly = "/analytics/weekly";
  static const String analyticsMonthly = "/analytics/monthly";
  static const String analyticsComparison = "/analytics/comparison";

  static const String coachChat = "/coach/chat";
  static const String coachHistory = "/coach/history";
  static const String audioTranscribe = "/audio/transcribe";
}
