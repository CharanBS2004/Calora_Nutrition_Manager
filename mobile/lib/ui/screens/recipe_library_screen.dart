import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/api_constants.dart';
import '../../core/network/api_client.dart';
import '../../core/theme/app_theme.dart';
import '../../models/app_models.dart';
import '../../providers/app_providers.dart';

class RecipeLibraryScreen extends StatefulWidget {
  final bool isSelectMode;
  final String initialMealType;

  const RecipeLibraryScreen({
    super.key,
    this.isSelectMode = false,
    this.initialMealType = "lunch",
  });

  @override
  State<RecipeLibraryScreen> createState() => _RecipeLibraryScreenState();
}

class _RecipeLibraryScreenState extends State<RecipeLibraryScreen> {
  final ApiClient _api = ApiClient();
  final TextEditingController _searchController = TextEditingController();

  List<RecipeItem> _recipes = [];
  bool _isLoading = false;
  String _selectedCategory = "All";

  final List<String> _categories = [
    "All",
    "Curries",
    "Rice Dishes",
    "Breads & Rotis",
    "Dal & Legumes",
    "Healthy / Low Cal",
  ];

  @override
  void initState() {
    super.initState();
    _loadRecipes();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadRecipes() async {
    setState(() => _isLoading = true);
    try {
      final res = await _api.get(ApiConstants.recipes);
      if (res is List) {
        setState(() {
          _recipes = res.map((e) => RecipeItem.fromJson(e)).toList();
        });
      }
    } catch (e) {
      debugPrint("Error loading recipes: $e");
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _quickLogRecipe(
      RecipeItem recipe, double servings, String mealType) async {
    try {
      await _api.post(
          "${ApiConstants.recipes}/${recipe.id}/log?servings=$servings&meal_type=$mealType");
      final nutritionProv =
          Provider.of<NutritionProvider>(context, listen: false);
      await nutritionProv.refreshDashboard();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content:
                Text("Logged ${recipe.name} ($servings serving) as $mealType!"),
            backgroundColor: AppTheme.sagePrimary,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Failed to log recipe: $e")),
        );
      }
    }
  }

  void _showQuickLogDialog(RecipeItem recipe) {
    double selectedServings = 1.0;
    String selectedMealType = widget.initialMealType;

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: Text("Log ${recipe.name}"),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    "${(recipe.caloriesPerServing * selectedServings).round()} kcal",
                    style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.deepTealAccent),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "P: ${(recipe.proteinPerServing * selectedServings).toStringAsFixed(1)}g  •  C: ${(recipe.carbPerServing * selectedServings).toStringAsFixed(1)}g  •  F: ${(recipe.fatPerServing * selectedServings).toStringAsFixed(1)}g",
                    style: const TextStyle(fontSize: 13),
                  ),
                  const Divider(height: 24),
                  const Text("Number of Servings",
                      style:
                          TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [0.5, 1.0, 1.5, 2.0].map((s) {
                      final isSel = selectedServings == s;
                      return ChoiceChip(
                        label: Text("$s"),
                        selected: isSel,
                        onSelected: (val) {
                          if (val) setDialogState(() => selectedServings = s);
                        },
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 16),
                  const Text("Meal Type",
                      style:
                          TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                  const SizedBox(height: 8),
                  DropdownButtonFormField<String>(
                    value: selectedMealType,
                    decoration: InputDecoration(
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 8),
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8)),
                    ),
                    items: ["breakfast", "lunch", "dinner", "snack"]
                        .map((m) => DropdownMenuItem(
                            value: m, child: Text(m.toUpperCase())))
                        .toList(),
                    onChanged: (val) {
                      if (val != null)
                        setDialogState(() => selectedMealType = val);
                    },
                  ),
                ],
              ),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: const Text("Cancel")),
                FilledButton(
                  onPressed: () {
                    Navigator.pop(ctx);
                    _quickLogRecipe(recipe, selectedServings, selectedMealType);
                  },
                  child: const Text("Log Meal"),
                ),
              ],
            );
          },
        );
      },
    );
  }

  void _showRecipeDetails(RecipeItem recipe) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return DraggableScrollableSheet(
          initialChildSize: 0.6,
          maxChildSize: 0.9,
          minChildSize: 0.4,
          expand: false,
          builder: (_, scrollController) {
            return Padding(
              padding: const EdgeInsets.all(20.0),
              child: ListView(
                controller: scrollController,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(recipe.name,
                            style: const TextStyle(
                                fontSize: 20, fontWeight: FontWeight.bold)),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppTheme.sagePrimary.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(recipe.category,
                            style: const TextStyle(
                                fontSize: 12, fontWeight: FontWeight.w600)),
                      ),
                    ],
                  ),
                  if (recipe.description != null &&
                      recipe.description!.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text(recipe.description!,
                        style:
                            const TextStyle(color: Colors.grey, fontSize: 13)),
                  ],
                  const SizedBox(height: 16),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(12.0),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          _nutrientCol(
                              "Calories",
                              "${recipe.caloriesPerServing.round()} kcal",
                              AppTheme.deepTealAccent),
                          _nutrientCol(
                              "Protein",
                              "${recipe.proteinPerServing.toStringAsFixed(1)}g",
                              AppTheme.proteinColor),
                          _nutrientCol(
                              "Carbs",
                              "${recipe.carbPerServing.toStringAsFixed(1)}g",
                              AppTheme.carbColor),
                          _nutrientCol(
                              "Fat",
                              "${recipe.fatPerServing.toStringAsFixed(1)}g",
                              AppTheme.fatColor),
                          _nutrientCol(
                              "Fiber",
                              "${recipe.fiberPerServing.toStringAsFixed(1)}g",
                              AppTheme.fiberColor),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  const Text("Ingredients",
                      style:
                          TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  if (recipe.ingredients.isEmpty)
                    const Text("No ingredients listed.",
                        style: TextStyle(color: Colors.grey))
                  else
                    ...recipe.ingredients.map((ing) {
                      if (ing is Map) {
                        return Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4.0),
                          child: Row(
                            children: [
                              const Icon(Icons.circle,
                                  size: 6, color: AppTheme.sagePrimary),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                    "${ing['food_name']} - ${ing['quantity']} ${ing['unit']}"),
                              ),
                            ],
                          ),
                        );
                      }
                      return Text(ing.toString());
                    }),
                  const SizedBox(height: 24),
                  FilledButton.icon(
                    onPressed: () {
                      Navigator.pop(ctx);
                      _showQuickLogDialog(recipe);
                    },
                    icon: const Icon(Icons.restaurant_rounded),
                    label: const Text("Log this Recipe"),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Widget _nutrientCol(String label, String val, Color color) {
    return Column(
      children: [
        Text(label, style: const TextStyle(fontSize: 11, color: Colors.grey)),
        const SizedBox(height: 2),
        Text(val,
            style: TextStyle(
                fontSize: 13, fontWeight: FontWeight.bold, color: color)),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final query = _searchController.text.toLowerCase();

    final filtered = _recipes.filter((r) {
      final matchesSearch = r.name.toLowerCase().contains(query) ||
          (r.description?.toLowerCase().contains(query) ?? false);
      final matchesCategory =
          _selectedCategory == "All" || r.category == _selectedCategory;
      return matchesSearch && matchesCategory;
    }).toList();

    return Scaffold(
      appBar: widget.isSelectMode
          ? null
          : AppBar(title: const Text("Recipe Library")),
      body: RefreshIndicator(
        onRefresh: _loadRecipes,
        child: Column(
          children: [
            // Search Bar
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
              child: TextField(
                controller: _searchController,
                onChanged: (_) => setState(() {}),
                decoration: InputDecoration(
                  hintText: "Search recipes...",
                  prefixIcon: const Icon(Icons.search_rounded),
                  suffixIcon: _searchController.text.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear),
                          onPressed: () {
                            _searchController.clear();
                            setState(() {});
                          },
                        )
                      : null,
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),

            // Category Chips
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Row(
                children: _categories.map((cat) {
                  final isSel = _selectedCategory == cat;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8.0),
                    child: FilterChip(
                      label: Text(cat,
                          style: TextStyle(
                              fontSize: 12,
                              fontWeight:
                                  isSel ? FontWeight.bold : FontWeight.normal)),
                      selected: isSel,
                      onSelected: (val) {
                        setState(() => _selectedCategory = cat);
                      },
                    ),
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 8),

            // Recipe List
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : filtered.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.menu_book_rounded,
                                  size: 64, color: Colors.grey.shade400),
                              const SizedBox(height: 12),
                              Text("No recipes found in this category",
                                  style:
                                      TextStyle(color: Colors.grey.shade600)),
                            ],
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 8),
                          itemCount: filtered.length,
                          itemBuilder: (context, index) {
                            final recipe = filtered[index];
                            return Card(
                              margin: const EdgeInsets.only(bottom: 12),
                              child: InkWell(
                                borderRadius: BorderRadius.circular(12),
                                onTap: () => widget.isSelectMode
                                    ? _showQuickLogDialog(recipe)
                                    : _showRecipeDetails(recipe),
                                child: Padding(
                                  padding: const EdgeInsets.all(14.0),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        mainAxisAlignment:
                                            MainAxisAlignment.spaceBetween,
                                        children: [
                                          Expanded(
                                            child: Text(
                                              recipe.name,
                                              style: const TextStyle(
                                                  fontWeight: FontWeight.bold,
                                                  fontSize: 16),
                                            ),
                                          ),
                                          Container(
                                            padding: const EdgeInsets.symmetric(
                                                horizontal: 8, vertical: 4),
                                            decoration: BoxDecoration(
                                              color: theme.colorScheme.primary
                                                  .withOpacity(0.1),
                                              borderRadius:
                                                  BorderRadius.circular(6),
                                            ),
                                            child: Text(
                                              recipe.category,
                                              style: TextStyle(
                                                  fontSize: 11,
                                                  color:
                                                      theme.colorScheme.primary,
                                                  fontWeight: FontWeight.w600),
                                            ),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 8),
                                      Row(
                                        children: [
                                          Text(
                                            "${recipe.caloriesPerServing.round()} kcal / serving",
                                            style: const TextStyle(
                                                fontWeight: FontWeight.w600,
                                                color: AppTheme.deepTealAccent),
                                          ),
                                          const Spacer(),
                                          Text(
                                              "P: ${recipe.proteinPerServing.toStringAsFixed(1)}g",
                                              style: const TextStyle(
                                                  fontSize: 12,
                                                  color:
                                                      AppTheme.proteinColor)),
                                          const SizedBox(width: 8),
                                          Text(
                                              "C: ${recipe.carbPerServing.toStringAsFixed(1)}g",
                                              style: const TextStyle(
                                                  fontSize: 12,
                                                  color: AppTheme.carbColor)),
                                          const SizedBox(width: 8),
                                          Text(
                                              "F: ${recipe.fatPerServing.toStringAsFixed(1)}g",
                                              style: const TextStyle(
                                                  fontSize: 12,
                                                  color: AppTheme.fatColor)),
                                        ],
                                      ),
                                      const Divider(height: 16),
                                      Row(
                                        mainAxisAlignment:
                                            MainAxisAlignment.spaceBetween,
                                        children: [
                                          Text(
                                            "Yield: ${recipe.servingsCount.round()} servings",
                                            style: TextStyle(
                                                fontSize: 12,
                                                color: theme.textTheme.bodySmall
                                                    ?.color),
                                          ),
                                          FilledButton.tonalIcon(
                                            onPressed: () =>
                                                _showQuickLogDialog(recipe),
                                            icon:
                                                const Icon(Icons.add, size: 16),
                                            label: const Text("Quick Log",
                                                style: TextStyle(fontSize: 12)),
                                            style: FilledButton.styleFrom(
                                              padding:
                                                  const EdgeInsets.symmetric(
                                                      horizontal: 12,
                                                      vertical: 6),
                                              minimumSize: Size.zero,
                                              tapTargetSize:
                                                  MaterialTapTargetSize
                                                      .shrinkWrap,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }
}

extension ListFilter<E> on List<E> {
  List<E> filter(bool Function(E element) test) {
    final result = <E>[];
    for (var element in this) {
      if (test(element)) {
        result.add(element);
      }
    }
    return result;
  }
}
