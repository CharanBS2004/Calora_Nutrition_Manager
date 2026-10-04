import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:provider/provider.dart';
import '../../core/constants/api_constants.dart';
import '../../core/network/api_client.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/app_providers.dart';
import '../widgets/app_widgets.dart';

class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen>
    with SingleTickerProviderStateMixin {
  final ApiClient _api = ApiClient();
  late TabController _tabController;

  bool _isLoadingWeekly = false;
  bool _isLoadingMonthly = false;
  Map<String, dynamic>? _weeklyReport;
  Map<String, dynamic>? _monthlyReport;
  String? _weeklyError;
  String? _monthlyError;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(_handleTabChange);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && context.read<NutritionProvider>().dailyData == null) {
        context.read<NutritionProvider>().refreshDashboard();
      }
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _handleTabChange() {
    if (_tabController.indexIsChanging) return;
    if (mounted) setState(() {});
    if (_tabController.index == 1 && _weeklyReport == null) {
      _loadPeriodAnalytics(weekly: true);
    } else if (_tabController.index == 2 && _monthlyReport == null) {
      _loadPeriodAnalytics(weekly: false);
    }
  }

  Future<void> _loadPeriodAnalytics({
    required bool weekly,
    bool force = false,
  }) async {
    if (weekly
        ? (_isLoadingWeekly || (!force && _weeklyReport != null))
        : (_isLoadingMonthly || (!force && _monthlyReport != null))) {
      return;
    }
    setState(() {
      if (weekly) {
        _isLoadingWeekly = true;
        _weeklyError = null;
      } else {
        _isLoadingMonthly = true;
        _monthlyError = null;
      }
    });
    try {
      final response = await _api.get(weekly
          ? ApiConstants.analyticsWeekly
          : ApiConstants.analyticsMonthly);
      if (!mounted) return;
      if (response is! Map<String, dynamic>) {
        throw const FormatException('Analytics response was not an object');
      }
      setState(() {
        if (weekly) {
          _weeklyReport = response;
        } else {
          _monthlyReport = response;
        }
      });
    } catch (e) {
      debugPrint("Error loading analytics: $e");
      if (mounted) {
        setState(() {
          if (weekly) {
            _weeklyError = 'Could not load this report. Try again.';
          } else {
            _monthlyError = 'Could not load this report. Try again.';
          }
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          if (weekly) {
            _isLoadingWeekly = false;
          } else {
            _isLoadingMonthly = false;
          }
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final nutritionProvider = Provider.of<NutritionProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text("Analytics & Insights"),
        bottom: TabBar(
          controller: _tabController,
          onTap: (_) => setState(() {}),
          indicatorColor: theme.colorScheme.primary,
          labelColor: theme.colorScheme.primary,
          unselectedLabelColor:
              theme.textTheme.bodyMedium?.color?.withOpacity(0.6),
          tabs: const [
            Tab(text: "Today"),
            Tab(text: "This Week"),
            Tab(text: "This Month"),
          ],
        ),
      ),
      body: switch (_tabController.index) {
        1 => _buildPeriodTab(_weeklyReport, "Weekly Trends (7 Days)", theme),
        2 => _buildPeriodTab(_monthlyReport, "Monthly Trends (30 Days)", theme),
        _ => _buildDailyTab(nutritionProvider, theme),
      },
    );
  }

  Widget _buildDailyTab(NutritionProvider provider, ThemeData theme) {
    final data = provider.dailyData;
    if (provider.isLoading && data == null) {
      return const Center(child: CircularProgressIndicator());
    }

    if (data == null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.analytics_outlined, size: 64, color: Colors.grey),
            const SizedBox(height: 12),
            Text(provider.dashboardError ??
                "No data for today yet. Pull down to refresh."),
            const SizedBox(height: 8),
            FilledButton.tonal(
              onPressed: () => provider.refreshDashboard(),
              child: const Text("Refresh"),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async {
        await provider.refreshDashboard();
      },
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Hero calorie ring
            Card(
              child: Padding(
                padding: const EdgeInsets.symmetric(
                    vertical: 24.0, horizontal: 16.0),
                child: Center(
                  child: CalorieHeroRing(
                    consumed: data.calories.consumed,
                    target: data.calories.target,
                    remaining: data.calories.remaining,
                    burnedKcal: data.caloriesBurned ?? 0,
                    burnDataAvailable: data.caloriesBurned != null,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Energy Balance Card
            EnergyBalanceCard(
              consumedKcal: data.calories.consumed,
              burnedKcal: data.caloriesBurned,
              netBalanceKcal: data.energyBalanceKcal,
              hasBurnData: data.caloriesBurned != null,
              activeCalories: data.activeCaloriesBurned,
              source: data.burnedSource,
              steps: data.steps,
              onSyncTap: () => provider.syncHealthConnectTelemetry(),
            ),
            const SizedBox(height: 16),

            // Macro Progress Bars
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("Macronutrient Targets",
                        style: theme.textTheme.titleMedium),
                    const SizedBox(height: 16),
                    MacroProgressBar(
                      label: "Protein",
                      consumed: data.protein.consumed,
                      target: data.protein.target,
                      unit: "g",
                      color: AppTheme.proteinColor,
                      expand: false,
                    ),
                    const SizedBox(height: 12),
                    MacroProgressBar(
                      label: "Carbohydrates",
                      consumed: data.carbs.consumed,
                      target: data.carbs.target,
                      unit: "g",
                      color: AppTheme.carbColor,
                      expand: false,
                    ),
                    const SizedBox(height: 12),
                    MacroProgressBar(
                      label: "Fat",
                      consumed: data.fat.consumed,
                      target: data.fat.target,
                      unit: "g",
                      color: AppTheme.fatColor,
                      expand: false,
                    ),
                    const SizedBox(height: 12),
                    MacroProgressBar(
                      label: "Dietary Fiber",
                      consumed: data.fiber.consumed,
                      target: data.fiber.target,
                      unit: "g",
                      color: AppTheme.fiberColor,
                      expand: false,
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Meal Distribution Card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("Calories by Meal",
                        style: theme.textTheme.titleMedium),
                    const SizedBox(height: 12),
                    _buildTodayMealChart(data.mealCalories),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _buildTodayMealChart(Map<String, double> mealCalories) {
    const mealKeys = ['breakfast', 'lunch', 'dinner', 'snack'];
    const mealLabels = ['Breakfast', 'Lunch', 'Dinner', 'Snack'];
    final values = mealKeys.map((key) => mealCalories[key] ?? 0.0).toList();
    final maximum = values.fold<double>(
        0, (current, value) => value > current ? value : current);
    final maxY = maximum > 0 ? maximum * 1.25 : 100.0;

    return Column(
      children: [
        SizedBox(
          height: 160,
          child: BarChart(
            BarChartData(
              maxY: maxY,
              alignment: BarChartAlignment.spaceAround,
              gridData: FlGridData(
                show: true,
                drawVerticalLine: false,
                horizontalInterval: maxY / 4,
              ),
              borderData: FlBorderData(show: false),
              titlesData: FlTitlesData(
                leftTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                topTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles:
                    const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 28,
                    getTitlesWidget: (value, meta) {
                      final index = value.toInt();
                      if (index < 0 || index >= mealLabels.length) {
                        return const SizedBox.shrink();
                      }
                      return SideTitleWidget(
                        axisSide: meta.axisSide,
                        child: Text(mealLabels[index],
                            style: const TextStyle(fontSize: 9)),
                      );
                    },
                  ),
                ),
              ),
              barGroups: List.generate(
                mealLabels.length,
                (index) => BarChartGroupData(
                  x: index,
                  barRods: [
                    BarChartRodData(
                      toY: values[index],
                      color: AppTheme.sagePrimary,
                      width: 24,
                      borderRadius:
                          const BorderRadius.vertical(top: Radius.circular(4)),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
        if (maximum == 0)
          const Padding(
            padding: EdgeInsets.only(top: 4),
            child: Text("Log a meal to see today's calories.",
                style: TextStyle(fontSize: 12, color: Colors.grey)),
          ),
      ],
    );
  }

  Widget _buildPeriodTab(
      Map<String, dynamic>? report, String title, ThemeData theme) {
    final isWeekly = title.startsWith("Weekly");
    final isLoading = isWeekly ? _isLoadingWeekly : _isLoadingMonthly;
    final error = isWeekly ? _weeklyError : _monthlyError;
    if (isLoading && report == null) {
      return const Center(child: CircularProgressIndicator());
    }

    if (report == null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.show_chart_rounded, size: 64, color: Colors.grey),
            const SizedBox(height: 12),
            Text(error ?? "No period analytics available."),
            const SizedBox(height: 8),
            FilledButton.tonal(
              onPressed: () =>
                  _loadPeriodAnalytics(weekly: isWeekly, force: true),
              child: const Text("Retry"),
            ),
          ],
        ),
      );
    }

    final summary = report['summary'] ?? {};
    final List dailyBreakdown = report['daily_breakdown'] ?? [];

    return RefreshIndicator(
      onRefresh: () => _loadPeriodAnalytics(weekly: isWeekly, force: true),
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Summary Header Cards
            Row(
              children: [
                _summaryMetricCard(
                    "Avg Calories",
                    "${(summary['avg_calories'] as num?)?.round() ?? 0} kcal",
                    AppTheme.deepTealAccent),
                const SizedBox(width: 8),
                _summaryMetricCard(
                    "Avg Protein",
                    "${(summary['avg_protein'] as num?)?.toStringAsFixed(1) ?? 0}g",
                    AppTheme.proteinColor),
                const SizedBox(width: 8),
                _summaryMetricCard(
                    "Goal Adherence",
                    "${(summary['goal_adherence_percent'] as num?)?.round() ?? 0}%",
                    AppTheme.sagePrimary),
              ],
            ),
            const SizedBox(height: 16),

            // FlChart: Daily Calories In vs Out Line Chart
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: theme.textTheme.titleMedium),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        _legendDot(AppTheme.sagePrimary, "Consumed"),
                        const SizedBox(width: 16),
                        _legendDot(Colors.orangeAccent, "Burned"),
                      ],
                    ),
                    const SizedBox(height: 20),
                    SizedBox(
                      height: 220,
                      child: dailyBreakdown.isEmpty
                          ? const Center(
                              child: Text("Not enough daily data points yet."))
                          : _buildTrendChart(dailyBreakdown),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Additional Summary Grid
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("Period Insights", style: theme.textTheme.titleMedium),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text("Average Daily Burn:"),
                        Text(
                            "${(summary['avg_calories_burned'] as num?)?.round() ?? 0} kcal",
                            style:
                                const TextStyle(fontWeight: FontWeight.bold)),
                      ],
                    ),
                    const Divider(height: 16),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text("Average Daily Steps:"),
                        Text(
                            "${(summary['avg_steps'] as num?)?.round() ?? 0} steps",
                            style:
                                const TextStyle(fontWeight: FontWeight.bold)),
                      ],
                    ),
                    const Divider(height: 16),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text("Total Meals Logged:"),
                        Text("${summary['total_meals_logged'] ?? 0} meals",
                            style:
                                const TextStyle(fontWeight: FontWeight.bold)),
                      ],
                    ),
                    const Divider(height: 16),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text("Missed Meals:"),
                        Text("${summary['missed_meals_count'] ?? 0}",
                            style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                color: Colors.orange)),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Top Foods
            if (report['top_foods'] != null &&
                (report['top_foods'] as List).isNotEmpty)
              _buildTopItemsList(
                  "Most Frequent Foods", report['top_foods'] as List, theme),

            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildTrendChart(List dailyBreakdown) {
    final List<FlSpot> consumedSpots = [];
    final List<FlSpot> burnedSpots = [];

    for (int i = 0; i < dailyBreakdown.length; i++) {
      final item = dailyBreakdown[i];
      final consumed = (item['consumed_kcal'] as num?)?.toDouble() ?? 0.0;
      final burned = (item['burned_kcal'] as num?)?.toDouble() ?? 0.0;

      consumedSpots.add(FlSpot(i.toDouble(), consumed));
      burnedSpots.add(FlSpot(i.toDouble(), burned));
    }

    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: true, drawVerticalLine: false),
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 22,
              getTitlesWidget: (val, meta) {
                final idx = val.toInt();
                if (idx >= 0 && idx < dailyBreakdown.length && idx % 2 == 0) {
                  final dStr = dailyBreakdown[idx]['date'].toString();
                  final parts = dStr.split('-');
                  return Text(
                      parts.length > 2 ? "${parts[1]}/${parts[2]}" : "$idx",
                      style: const TextStyle(fontSize: 10));
                }
                return const SizedBox.shrink();
              },
            ),
          ),
          topTitles:
              const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles:
              const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: consumedSpots,
            isCurved: true,
            color: AppTheme.sagePrimary,
            barWidth: 3,
            dotData: const FlDotData(show: false),
          ),
          LineChartBarData(
            spots: burnedSpots,
            isCurved: true,
            color: Colors.orangeAccent,
            barWidth: 2,
            dashArray: [4, 4],
            dotData: const FlDotData(show: false),
          ),
        ],
      ),
    );
  }

  Widget _summaryMetricCard(String label, String value, Color color) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 12.0, horizontal: 8.0),
          child: Column(
            children: [
              Text(label,
                  style: const TextStyle(fontSize: 11, color: Colors.grey)),
              const SizedBox(height: 4),
              Text(value,
                  style: TextStyle(
                      fontSize: 14, fontWeight: FontWeight.bold, color: color)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _legendDot(Color color, String text) {
    return Row(
      children: [
        Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: 6),
        Text(text, style: const TextStyle(fontSize: 12)),
      ],
    );
  }

  Widget _buildTopItemsList(String title, List items, ThemeData theme) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: theme.textTheme.titleMedium),
            const SizedBox(height: 12),
            ...items.take(5).map((item) {
              return ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.restaurant_rounded,
                    color: AppTheme.sagePrimary, size: 20),
                title: Text(item['name'] ?? 'Item',
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                trailing: Text("${item['count']}x",
                    style: const TextStyle(fontWeight: FontWeight.bold)),
              );
            }),
          ],
        ),
      ),
    );
  }
}
