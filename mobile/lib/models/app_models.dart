class UserProfile {
  final int userId;
  final String name;
  final int? age;
  final String? gender;
  final double? heightCm;
  final double? weightKg;
  final String? activityLevel;
  final String? dietaryPreference;
  final List<String> allergies;
  final List<String> foodPreferences;

  UserProfile({
    required this.userId,
    required this.name,
    this.age,
    this.gender,
    this.heightCm,
    this.weightKg,
    this.activityLevel,
    this.dietaryPreference,
    required this.allergies,
    required this.foodPreferences,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) => UserProfile(
        userId: json['user_id'] ?? 0,
        name: json['name'] ?? '',
        age: json['age'],
        gender: json['gender'],
        heightCm: (json['height_cm'] as num?)?.toDouble(),
        weightKg: (json['weight_kg'] as num?)?.toDouble(),
        activityLevel: json['activity_level'],
        dietaryPreference: json['dietary_preference'],
        allergies:
            (json['allergies'] as List?)?.map((e) => e.toString()).toList() ??
                [],
        foodPreferences: (json['food_preferences'] as List?)
                ?.map((e) => e.toString())
                .toList() ??
            [],
      );
}

class NutritionGoals {
  final double calorieTarget;
  final double proteinG;
  final double carbG;
  final double fatG;
  final double fiberG;
  final double waterMl;

  NutritionGoals({
    required this.calorieTarget,
    required this.proteinG,
    required this.carbG,
    required this.fatG,
    required this.fiberG,
    required this.waterMl,
  });

  factory NutritionGoals.fromJson(Map<String, dynamic> json) => NutritionGoals(
        calorieTarget: (json['calorie_target'] as num?)?.toDouble() ?? 2000.0,
        proteinG: (json['protein_g'] as num?)?.toDouble() ?? 75.0,
        carbG: (json['carb_g'] as num?)?.toDouble() ?? 250.0,
        fatG: (json['fat_g'] as num?)?.toDouble() ?? 65.0,
        fiberG: (json['fiber_g'] as num?)?.toDouble() ?? 30.0,
        waterMl: (json['water_ml'] as num?)?.toDouble() ?? 2500.0,
      );
}

class FoodItem {
  final int id;
  final String? foodCode;
  final String foodName;
  final String? category;
  final String source;
  final double servingSize;
  final String servingUnit;
  final double weightG;
  final double energyKcal;
  final double proteinG;
  final double carbG;
  final double fatG;
  final double fiberG;
  final double? unitServingEnergyKcal;

  FoodItem({
    required this.id,
    this.foodCode,
    required this.foodName,
    this.category,
    required this.source,
    required this.servingSize,
    required this.servingUnit,
    required this.weightG,
    required this.energyKcal,
    required this.proteinG,
    required this.carbG,
    required this.fatG,
    required this.fiberG,
    this.unitServingEnergyKcal,
  });

  factory FoodItem.fromJson(Map<String, dynamic> json) => FoodItem(
        id: json['id'] ?? 0,
        foodCode: json['food_code'],
        foodName: json['food_name'] ?? '',
        category: json['category'],
        source: json['source'] ?? 'INDB',
        servingSize: (json['serving_size'] as num?)?.toDouble() ?? 100.0,
        servingUnit: json['serving_unit'] ?? 'g',
        weightG: (json['weight_g'] as num?)?.toDouble() ?? 100.0,
        energyKcal: (json['energy_kcal'] as num?)?.toDouble() ?? 0.0,
        proteinG: (json['protein_g'] as num?)?.toDouble() ?? 0.0,
        carbG: (json['carbohydrate_g'] as num?)?.toDouble() ?? 0.0,
        fatG: (json['fat_g'] as num?)?.toDouble() ?? 0.0,
        fiberG: (json['fiber_g'] as num?)?.toDouble() ?? 0.0,
        unitServingEnergyKcal:
            (json['unit_serving_energy_kcal'] as num?)?.toDouble(),
      );
}

class RecipeItem {
  final int id;
  final String name;
  final String? description;
  final String category;
  final double servingsCount;
  final String servingUnit;
  final double caloriesPerServing;
  final double proteinPerServing;
  final double carbPerServing;
  final double fatPerServing;
  final double fiberPerServing;
  final double totalCalories;
  final List<dynamic> ingredients;

  RecipeItem({
    required this.id,
    required this.name,
    this.description,
    required this.category,
    required this.servingsCount,
    required this.servingUnit,
    required this.caloriesPerServing,
    required this.proteinPerServing,
    required this.carbPerServing,
    required this.fatPerServing,
    required this.fiberPerServing,
    required this.totalCalories,
    required this.ingredients,
  });

  factory RecipeItem.fromJson(Map<String, dynamic> json) => RecipeItem(
        id: json['id'] ?? 0,
        name: json['name'] ?? '',
        description: json['description'],
        category: json['category'] ?? 'My Recipes',
        servingsCount: (json['servings_count'] as num?)?.toDouble() ?? 1.0,
        servingUnit: json['serving_unit'] ?? 'serving',
        caloriesPerServing:
            (json['calories_per_serving'] as num?)?.toDouble() ?? 0.0,
        proteinPerServing:
            (json['protein_per_serving'] as num?)?.toDouble() ?? 0.0,
        carbPerServing: (json['carb_per_serving'] as num?)?.toDouble() ?? 0.0,
        fatPerServing: (json['fat_per_serving'] as num?)?.toDouble() ?? 0.0,
        fiberPerServing: (json['fiber_per_serving'] as num?)?.toDouble() ?? 0.0,
        totalCalories: (json['total_calories'] as num?)?.toDouble() ?? 0.0,
        ingredients: json['ingredients'] ?? [],
      );
}

class MealRecord {
  final int id;
  final String mealType;
  final DateTime loggedAt;
  final double totalCalories;
  final double totalProtein;
  final double totalCarbs;
  final double totalFat;
  final double totalFiber;
  final double confidenceScore;
  final List<dynamic> items;

  MealRecord({
    required this.id,
    required this.mealType,
    required this.loggedAt,
    required this.totalCalories,
    required this.totalProtein,
    required this.totalCarbs,
    required this.totalFat,
    required this.totalFiber,
    required this.confidenceScore,
    required this.items,
  });

  factory MealRecord.fromJson(Map<String, dynamic> json) => MealRecord(
        id: json['id'] ?? 0,
        mealType: json['meal_type'] ?? 'lunch',
        loggedAt: DateTime.tryParse(json['logged_at'] ?? '') ?? DateTime.now(),
        totalCalories: (json['total_calories'] as num?)?.toDouble() ?? 0.0,
        totalProtein: (json['total_protein'] as num?)?.toDouble() ?? 0.0,
        totalCarbs: (json['total_carbs'] as num?)?.toDouble() ?? 0.0,
        totalFat: (json['total_fat'] as num?)?.toDouble() ?? 0.0,
        totalFiber: (json['total_fiber'] as num?)?.toDouble() ?? 0.0,
        confidenceScore: (json['confidence_score'] as num?)?.toDouble() ?? 1.0,
        items: json['items'] ?? [],
      );
}

class NutrientMetric {
  final double consumed;
  final double target;
  final double percentage;
  final double remaining;

  NutrientMetric({
    required this.consumed,
    required this.target,
    required this.percentage,
    required this.remaining,
  });

  factory NutrientMetric.fromJson(Map<String, dynamic> json) => NutrientMetric(
        consumed: (json['consumed'] as num?)?.toDouble() ?? 0.0,
        target: (json['target'] as num?)?.toDouble() ?? 1.0,
        percentage: (json['percentage'] as num?)?.toDouble() ?? 0.0,
        remaining: (json['remaining'] as num?)?.toDouble() ?? 0.0,
      );
}

class DailyAnalyticsData {
  final NutrientMetric calories;
  final NutrientMetric protein;
  final NutrientMetric carbs;
  final NutrientMetric fat;
  final NutrientMetric fiber;
  final double? caloriesBurned;
  final double activeCaloriesBurned;
  final String burnedSource;
  final double? energyBalanceKcal;
  final int steps;
  final int mealsCount;
  final Map<String, bool> mealsLogged;
  final Map<String, double> mealCalories;

  DailyAnalyticsData({
    required this.calories,
    required this.protein,
    required this.carbs,
    required this.fat,
    required this.fiber,
    required this.caloriesBurned,
    required this.activeCaloriesBurned,
    required this.burnedSource,
    required this.energyBalanceKcal,
    required this.steps,
    required this.mealsCount,
    required this.mealsLogged,
    required this.mealCalories,
  });

  factory DailyAnalyticsData.fromJson(Map<String, dynamic> json) =>
      DailyAnalyticsData(
        calories: NutrientMetric.fromJson(json['calories'] ?? {}),
        protein: NutrientMetric.fromJson(json['protein_g'] ?? {}),
        carbs: NutrientMetric.fromJson(json['carb_g'] ?? {}),
        fat: NutrientMetric.fromJson(json['fat_g'] ?? {}),
        fiber: NutrientMetric.fromJson(json['fiber_g'] ?? {}),
        caloriesBurned: (json['calories_burned'] as num?)?.toDouble(),
        activeCaloriesBurned:
            (json['active_calories_burned'] as num?)?.toDouble() ?? 0.0,
        burnedSource:
            json['burned_source'] ?? 'Health Connect data unavailable',
        energyBalanceKcal: (json['energy_balance_kcal'] as num?)?.toDouble(),
        steps: json['steps'] ?? 0,
        mealsCount: json['meals_count'] ?? 0,
        mealsLogged: (json['meals_logged'] as Map<String, dynamic>?)
                ?.map((k, v) => MapEntry(k, v == true)) ??
            {},
        mealCalories: (json['meal_calories'] as Map<String, dynamic>?)
                ?.map((k, v) => MapEntry(k, (v as num).toDouble())) ??
            {},
      );
}

class ActionButtonModel {
  final String label;
  final String actionType;
  final Map<String, dynamic> payload;

  ActionButtonModel(
      {required this.label, required this.actionType, required this.payload});

  factory ActionButtonModel.fromJson(Map<String, dynamic> json) =>
      ActionButtonModel(
        label: json['label'] ?? '',
        actionType: json['action_type'] ?? '',
        payload: json['payload'] ?? {},
      );
}

class ChatMessageModel {
  final int id;
  final String role;
  final String content;
  final bool uncertaintyFlag;
  final String? clarificationNeeded;
  final List<String> suggestedOptions;
  final List<ActionButtonModel> actionButtons;
  final DateTime createdAt;

  ChatMessageModel({
    required this.id,
    required this.role,
    required this.content,
    required this.uncertaintyFlag,
    this.clarificationNeeded,
    this.suggestedOptions = const [],
    this.actionButtons = const [],
    required this.createdAt,
  });

  factory ChatMessageModel.fromJson(Map<String, dynamic> json) =>
      ChatMessageModel(
        id: json['id'] ?? json['message_id'] ?? 0,
        role: json['role'] ?? 'assistant',
        content: json['content'] ?? json['reply'] ?? '',
        uncertaintyFlag: json['uncertainty_flag'] ?? false,
        clarificationNeeded: json['clarification_needed'],
        suggestedOptions: (json['suggested_options'] as List?)
                ?.map((e) => e.toString())
                .toList() ??
            [],
        actionButtons: (json['action_buttons'] as List?)
                ?.map((e) => ActionButtonModel.fromJson(e))
                .toList() ??
            [],
        createdAt:
            DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
      );
}
