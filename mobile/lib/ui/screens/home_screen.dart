import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/app_providers.dart';
import '../widgets/app_widgets.dart';
import 'log_food_screen.dart';
import 'recipe_builder_screen.dart';
import 'coach_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  String get _timeGreeting {
    final hour = DateTime.now().hour;
    if (hour >= 5 && hour < 12) return "Good morning";
    if (hour >= 12 && hour < 17) return "Good afternoon";
    if (hour >= 17 && hour < 21) return "Good evening";
    return "Good night";
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<NutritionProvider>().refreshDashboard();
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final nutrition = context.watch<NutritionProvider>();
    final data = nutrition.dailyData;

    final consumedKcal = data?.calories.consumed ?? 0.0;
    final targetKcal = data?.calories.target ?? 2000.0;
    final burnedKcal = data?.caloriesBurned ?? 0.0;
    final netBalance = data?.energyBalanceKcal ?? 0.0;

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("$_timeGreeting, ${auth.userName} 👋",
                style: Theme.of(context).textTheme.headlineSmall),
            Text("Your nutrition and energy balance",
                style: Theme.of(context).textTheme.labelSmall),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.sync),
            tooltip: "Sync Health Connect",
            onPressed: () async {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                    content: Text("Syncing Health Connect activity data..."),
                    duration: Duration(seconds: 1)),
              );
              try {
                final summary = await context
                    .read<NutritionProvider>()
                    .syncHealthConnectTelemetry();
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(summary == null
                        ? "Connect Health Connect and grant permissions from Profile first."
                        : summary.totalCaloriesBurned > 0
                            ? "Health data synced: ${summary.totalCaloriesBurned.round()} total kcal burned."
                            : "Health data synced, but no total calories were shared. Active calories: ${summary.activeCaloriesBurned.round()} kcal."),
                  ),
                );
              } catch (e) {
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text("Health Connect sync failed: $e")),
                );
              }
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => context.read<NutritionProvider>().refreshDashboard(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 1. Calorie Hero Ring
              CalorieHeroRing(
                consumedKcal: consumedKcal,
                targetKcal: targetKcal,
                burnedKcal: burnedKcal,
                burnDataAvailable: data?.caloriesBurned != null,
              ),
              const SizedBox(height: AppSpacing.lg),

              // 2. Macro Progress Bars
              Text("Macronutrients",
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: AppSpacing.sm),
              Row(
                children: [
                  MacroProgressBar(
                    label: "Protein",
                    consumed: data?.protein.consumed ?? 0,
                    target: data?.protein.target ?? 75,
                    unit: "g",
                    color: AppColors.protein,
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  MacroProgressBar(
                    label: "Carbs",
                    consumed: data?.carbs.consumed ?? 0,
                    target: data?.carbs.target ?? 250,
                    unit: "g",
                    color: AppColors.carbohydrates,
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  MacroProgressBar(
                    label: "Fat",
                    consumed: data?.fat.consumed ?? 0,
                    target: data?.fat.target ?? 65,
                    unit: "g",
                    color: AppColors.fat,
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  MacroProgressBar(
                    label: "Fiber",
                    consumed: data?.fiber.consumed ?? 0,
                    target: data?.fiber.target ?? 30,
                    unit: "g",
                    color: AppColors.fiber,
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.lg),

              // 3. Energy Balance Card
              EnergyBalanceCard(
                caloriesIn: consumedKcal,
                caloriesOut: burnedKcal,
                netBalance: netBalance,
                hasBurnData: data?.caloriesBurned != null,
                activeCalories: data?.activeCaloriesBurned ?? 0,
                source: data?.burnedSource ?? "Health Connect not synced",
              ),
              const SizedBox(height: AppSpacing.lg),

              // 4. Today's Meals Checkmarks
              Text("Today's Meals",
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: AppSpacing.sm),
              Row(
                children: [
                  MealStatusTile(
                    mealName: "Breakfast",
                    isLogged: data?.mealsLogged['breakfast'] ?? false,
                    calories: data?.mealCalories['breakfast'] ?? 0,
                    onTap: () => _openLog(context, "breakfast"),
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  MealStatusTile(
                    mealName: "Lunch",
                    isLogged: data?.mealsLogged['lunch'] ?? false,
                    calories: data?.mealCalories['lunch'] ?? 0,
                    onTap: () => _openLog(context, "lunch"),
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  MealStatusTile(
                    mealName: "Snack",
                    isLogged: data?.mealsLogged['snack'] ?? false,
                    calories: data?.mealCalories['snack'] ?? 0,
                    onTap: () => _openLog(context, "snack"),
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  MealStatusTile(
                    mealName: "Dinner",
                    isLogged: data?.mealsLogged['dinner'] ?? false,
                    calories: data?.mealCalories['dinner'] ?? 0,
                    onTap: () => _openLog(context, "dinner"),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.xl),

              // 5. Quick Actions Row
              Text("Quick Actions",
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: AppSpacing.sm),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      icon:
                          const Icon(Icons.add, color: AppColors.primaryLight),
                      label: const Text("Log Food"),
                      onPressed: () => _openLog(context, "lunch"),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: OutlinedButton.icon(
                      icon: const Icon(Icons.soup_kitchen,
                          color: AppColors.secondaryLight),
                      label: const Text("Build Recipe"),
                      onPressed: () {
                        Navigator.push(
                            context,
                            MaterialPageRoute(
                                builder: (_) => const RecipeBuilderScreen()));
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      icon: const Icon(Icons.mic, color: Colors.white),
                      label: const Text("Voice Log"),
                      style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primaryLight),
                      onPressed: () =>
                          _openLog(context, "lunch", initialTab: 1),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: ElevatedButton.icon(
                      icon: const Icon(Icons.auto_awesome, color: Colors.white),
                      label: const Text("Ask Coach"),
                      style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primaryDarkLight),
                      onPressed: () {
                        Navigator.push(
                            context,
                            MaterialPageRoute(
                                builder: (_) => const CoachScreen()));
                      },
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _openLog(BuildContext context, String mealType, {int initialTab = 0}) {
    Navigator.push(
      context,
      MaterialPageRoute(
          builder: (_) =>
              LogFoodScreen(initialMealType: mealType, initialTab: initialTab)),
    );
  }
}
