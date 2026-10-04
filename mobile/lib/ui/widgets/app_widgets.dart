import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

// ----------------- Calorie Hero Ring Component -----------------
class CalorieHeroRing extends StatelessWidget {
  final double consumedKcal;
  final double targetKcal;
  final double burnedKcal;
  final bool burnDataAvailable;

  const CalorieHeroRing({
    super.key,
    double? consumedKcal,
    double? targetKcal,
    double? burnedKcal,
    double? consumed,
    double? target,
    double? remaining,
    this.burnDataAvailable = true,
  })  : consumedKcal = consumedKcal ?? consumed ?? 0.0,
        targetKcal = targetKcal ?? target ?? 2000.0,
        burnedKcal = burnedKcal ?? 0.0;

  @override
  Widget build(BuildContext context) {
    final remaining = (targetKcal - consumedKcal).clamp(0.0, targetKcal);
    final progress =
        (consumedKcal / (targetKcal > 0 ? targetKcal : 1.0)).clamp(0.0, 1.0);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text("Today's Energy",
                    style: Theme.of(context).textTheme.titleMedium),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: isDark
                        ? AppColors.elevatedSurfaceDark
                        : AppColors.softSurfaceLight,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.local_fire_department,
                          color: AppColors.activity, size: 16),
                      const SizedBox(width: 4),
                      Text(
                        burnDataAvailable
                            ? "${burnedKcal.toInt()} kcal out"
                            : "Burn data unavailable",
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: AppColors.activity,
                            fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.lg),
            Center(
              child: SizedBox(
                width: 170,
                height: 170,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    SizedBox(
                      width: 170,
                      height: 170,
                      child: CircularProgressIndicator(
                        value: progress,
                        strokeWidth: 14,
                        strokeCap: StrokeCap.round,
                        backgroundColor: isDark
                            ? AppColors.borderDark
                            : AppColors.borderLight,
                        valueColor: const AlwaysStoppedAnimation<Color>(
                            AppColors.calories),
                      ),
                    ),
                    Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          "${consumedKcal.toInt()}",
                          style: Theme.of(context)
                              .textTheme
                              .displayLarge
                              ?.copyWith(
                                color: isDark
                                    ? AppColors.textPrimaryDark
                                    : AppColors.textPrimaryLight,
                                letterSpacing: -1.0,
                              ),
                        ),
                        Text(
                          "/ ${targetKcal.toInt()} kcal",
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          "${remaining.toInt()} kcal remaining",
                          style:
                              Theme.of(context).textTheme.labelSmall?.copyWith(
                                    color: AppColors.calories,
                                    fontWeight: FontWeight.w600,
                                  ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ----------------- Macro Progress Cards -----------------
class MacroProgressBar extends StatelessWidget {
  final String label;
  final double consumed;
  final double target;
  final String unit;
  final Color color;
  final bool expand;

  const MacroProgressBar({
    super.key,
    required this.label,
    required this.consumed,
    required this.target,
    required this.unit,
    required this.color,
    this.expand = true,
  });

  @override
  Widget build(BuildContext context) {
    final progress = (consumed / (target > 0 ? target : 1.0)).clamp(0.0, 1.0);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final targetLabel =
        target.toStringAsFixed(target.truncateToDouble() == target ? 0 : 1);

    final card = Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
      decoration: BoxDecoration(
        color: isDark ? AppColors.surfaceDark : AppColors.surfaceLight,
        borderRadius: BorderRadius.circular(AppRadius.small),
        border: Border.all(
            color: isDark ? AppColors.borderDark : AppColors.borderLight),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelSmall),
          const SizedBox(height: 4),
          Text(
            "${consumed.toInt()}/$targetLabel$unit",
            maxLines: 1,
            softWrap: false,
            overflow: TextOverflow.clip,
            style: Theme.of(context)
                .textTheme
                .labelSmall
                ?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 6,
              backgroundColor:
                  isDark ? AppColors.borderDark : AppColors.borderLight,
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          ),
        ],
      ),
    );
    return expand ? Expanded(child: card) : card;
  }
}

// ----------------- Energy Balance Card -----------------
class EnergyBalanceCard extends StatelessWidget {
  final double caloriesIn;
  final double caloriesOut;
  final double netBalance;
  final String source;
  final int? steps;
  final VoidCallback? onSyncTap;
  final bool hasBurnData;
  final double activeCalories;

  const EnergyBalanceCard({
    super.key,
    double? caloriesIn,
    double? caloriesOut,
    double? netBalance,
    String? source,
    double? consumedKcal,
    double? burnedKcal,
    double? netBalanceKcal,
    this.steps,
    this.onSyncTap,
    this.hasBurnData = true,
    this.activeCalories = 0,
  })  : caloriesIn = caloriesIn ?? consumedKcal ?? 0.0,
        caloriesOut = caloriesOut ?? burnedKcal ?? 0.0,
        netBalance = netBalance ?? netBalanceKcal ?? 0.0,
        source = source ?? 'Health Connect';

  @override
  Widget build(BuildContext context) {
    final isDeficit = hasBurnData && netBalance < 0;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text("Energy Balance",
                    style: Theme.of(context).textTheme.titleMedium),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                  decoration: BoxDecoration(
                    color: isDeficit
                        ? AppColors.success.withOpacity(0.15)
                        : AppColors.warning.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    !hasBurnData
                        ? "NO BURN DATA"
                        : isDeficit
                            ? "DEFICIT"
                            : "SURPLUS",
                    style: TextStyle(
                      color: isDeficit ? AppColors.success : AppColors.warning,
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildStat(context, "🍛 Consumed", "${caloriesIn.toInt()} kcal",
                    AppColors.calories),
                const Text("−",
                    style: TextStyle(fontSize: 20, color: Colors.grey)),
                _buildStat(
                  context,
                  "🔥 Burned",
                  hasBurnData ? "${caloriesOut.toInt()} kcal" : "Unavailable",
                  AppColors.activity,
                ),
                const Text("=",
                    style: TextStyle(fontSize: 20, color: Colors.grey)),
                _buildStat(
                  context,
                  "⚡ Balance",
                  hasBurnData ? "${netBalance.toInt()} kcal" : "—",
                  isDeficit ? AppColors.success : AppColors.warning,
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            if (activeCalories > 0)
              Text(
                "Active calories: ${activeCalories.round()} kcal",
                style: Theme.of(context).textTheme.labelSmall,
              ),
            Text(
              "Source: $source",
              style: Theme.of(context)
                  .textTheme
                  .labelSmall
                  ?.copyWith(fontSize: 10, fontStyle: FontStyle.italic),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStat(
      BuildContext context, String title, String value, Color color) {
    return Column(
      children: [
        Text(title, style: Theme.of(context).textTheme.labelSmall),
        const SizedBox(height: 2),
        Text(value,
            style: TextStyle(
                fontWeight: FontWeight.bold, color: color, fontSize: 13)),
      ],
    );
  }
}

// ----------------- Meal Checkmark Card -----------------
class MealStatusTile extends StatelessWidget {
  final String mealName;
  final bool isLogged;
  final double calories;
  final VoidCallback onTap;

  const MealStatusTile({
    super.key,
    required this.mealName,
    required this.isLogged,
    required this.calories,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.small),
        child: Container(
          padding: const EdgeInsets.symmetric(
              vertical: AppSpacing.md, horizontal: 8),
          decoration: BoxDecoration(
            color: isDark ? AppColors.surfaceDark : AppColors.surfaceLight,
            borderRadius: BorderRadius.circular(AppRadius.small),
            border: Border.all(
              color: isLogged
                  ? AppColors.primaryLight
                  : (isDark ? AppColors.borderDark : AppColors.borderLight),
              width: isLogged ? 1.5 : 1.0,
            ),
          ),
          child: Column(
            children: [
              Icon(
                isLogged ? Icons.check_circle : Icons.add_circle_outline,
                color: isLogged ? AppColors.primaryLight : Colors.grey,
                size: 22,
              ),
              const SizedBox(height: 6),
              Text(mealName,
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontSize: 12)),
              const SizedBox(height: 2),
              Text(
                isLogged ? "${calories.toInt()} kcal" : "Pending",
                style: Theme.of(context)
                    .textTheme
                    .labelSmall
                    ?.copyWith(fontSize: 10),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
