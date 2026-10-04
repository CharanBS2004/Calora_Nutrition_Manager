import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/api_constants.dart';
import '../../core/network/api_client.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/app_providers.dart';

class RecipeBuilderScreen extends StatefulWidget {
  const RecipeBuilderScreen({super.key});

  @override
  State<RecipeBuilderScreen> createState() => _RecipeBuilderScreenState();
}

class _RecipeBuilderScreenState extends State<RecipeBuilderScreen> {
  final ApiClient _api = ApiClient();

  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _descController = TextEditingController();
  final TextEditingController _servingsController = TextEditingController(text: "4");
  final TextEditingController _cookedWeightController = TextEditingController(text: "800");

  String _category = "Curries";
  final List<String> _categories = [
    "Curries",
    "Rice Dishes",
    "Breads & Rotis",
    "Dal & Legumes",
    "Snacks & Chaat",
    "Beverages",
    "Healthy / Low Cal",
  ];

  // Dynamic ingredients list
  final List<Map<String, dynamic>> _ingredients = [];

  final TextEditingController _newFoodNameController = TextEditingController();
  final TextEditingController _newQtyController = TextEditingController(text: "100");
  String _newUnit = "g";

  bool _isCalculating = false;
  bool _isSaving = false;
  Map<String, dynamic>? _calculationResult;

  @override
  void dispose() {
    _nameController.dispose();
    _descController.dispose();
    _servingsController.dispose();
    _cookedWeightController.dispose();
    _newFoodNameController.dispose();
    _newQtyController.dispose();
    super.dispose();
  }

  void _addIngredient() {
    final name = _newFoodNameController.text.trim();
    final qty = double.tryParse(_newQtyController.text.trim()) ?? 100.0;
    if (name.isEmpty) return;

    setState(() {
      _ingredients.add({
        "food_name": name,
        "quantity": qty,
        "unit": _newUnit,
      });
      _newFoodNameController.clear();
      _newQtyController.text = "100";
      _newUnit = "g";
      _calculationResult = null; // Invalidate cached calculation
    });
  }

  Future<void> _calculateNutrition() async {
    if (_ingredients.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Add at least one ingredient.")),
      );
      return;
    }

    setState(() => _isCalculating = true);
    final servings = double.tryParse(_servingsController.text.trim()) ?? 4.0;
    final cookedWeight = double.tryParse(_cookedWeightController.text.trim()) ?? 800.0;

    try {
      final payload = {
        "recipe_name": _nameController.text.trim().isEmpty ? "Custom Recipe" : _nameController.text.trim(),
        "ingredients": _ingredients,
        "servings_count": servings,
        "total_cooked_weight_g": cookedWeight,
        "consumed_quantity": 1.0,
        "consumed_unit": "serving",
      };

      final res = await _api.post(ApiConstants.recipesCalculate, body: payload);
      setState(() {
        _calculationResult = res;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Calculation error: $e")),
        );
      }
    } finally {
      if (mounted) setState(() => _isCalculating = false);
    }
  }

  Future<void> _saveRecipe({bool andLog = false}) async {
    final name = _nameController.text.trim();
    if (name.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Please enter a recipe name.")),
      );
      return;
    }
    if (_ingredients.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Add at least one ingredient.")),
      );
      return;
    }

    setState(() => _isSaving = true);
    final servings = double.tryParse(_servingsController.text.trim()) ?? 4.0;
    final cookedWeight = double.tryParse(_cookedWeightController.text.trim()) ?? 800.0;

    try {
      final payload = {
        "name": name,
        "description": _descController.text.trim(),
        "category": _category,
        "servings_count": servings,
        "serving_unit": "serving",
        "total_cooked_weight_g": cookedWeight,
        "ingredients": _ingredients,
      };

      final res = await _api.post(ApiConstants.recipes, body: payload);
      final recipeId = res['id'];

      final nutritionProv = Provider.of<NutritionProvider>(context, listen: false);
      await nutritionProv.refreshDashboard();

      if (andLog && recipeId != null) {
        // Quick log 1 serving as lunch
        await _api.post("${ApiConstants.recipes}/$recipeId/log?servings=1.0&meal_type=lunch");
        await nutritionProv.refreshDashboard();
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(andLog ? "Recipe saved and 1 serving logged as meal!" : "Recipe '$name' saved to library!"),
            backgroundColor: AppTheme.sagePrimary,
          ),
        );
        if (!andLog) {
          Navigator.maybePop(context);
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Error saving recipe: $e")),
        );
      }
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text("Method C: Recipe Builder"),
        actions: [
          IconButton(
            tooltip: "Calculate Macros",
            icon: const Icon(Icons.calculate_rounded),
            onPressed: _isCalculating ? null : _calculateNutrition,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header Info
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("Recipe Details", style: theme.textTheme.titleMedium),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _nameController,
                      decoration: InputDecoration(
                        labelText: "Recipe Name *",
                        hintText: "e.g., Homestyle Aloo Matar",
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: DropdownButtonFormField<String>(
                            value: _category,
                            decoration: InputDecoration(
                              labelText: "Category",
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            ),
                            items: _categories.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
                            onChanged: (val) {
                              if (val != null) setState(() => _category = val);
                            },
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: _servingsController,
                            keyboardType: TextInputType.number,
                            decoration: InputDecoration(
                              labelText: "Servings Yield",
                              hintText: "4",
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _cookedWeightController,
                      keyboardType: TextInputType.number,
                      decoration: InputDecoration(
                        labelText: "Total Cooked Weight (grams)",
                        hintText: "800",
                        helperText: "Used for accurate cooked 100g density calculations",
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Ingredients Section
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text("Ingredients (${_ingredients.length})", style: theme.textTheme.titleMedium),
                TextButton.icon(
                  icon: const Icon(Icons.calculate_outlined, size: 18),
                  label: const Text("Recalculate"),
                  onPressed: _isCalculating ? null : _calculateNutrition,
                ),
              ],
            ),
            const SizedBox(height: 8),

            // List of Current Ingredients
            ..._ingredients.asMap().entries.map((entry) {
              final idx = entry.key;
              final ing = entry.value;
              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: theme.colorScheme.primary.withOpacity(0.1),
                    child: Text("${idx + 1}", style: TextStyle(color: theme.colorScheme.primary, fontWeight: FontWeight.bold)),
                  ),
                  title: Text(ing['food_name'], style: const TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: Text("${ing['quantity']} ${ing['unit']}"),
                  trailing: IconButton(
                    icon: const Icon(Icons.delete_outline_rounded, color: Colors.red),
                    onPressed: () {
                      setState(() {
                        _ingredients.removeAt(idx);
                        _calculationResult = null;
                      });
                    },
                  ),
                ),
              );
            }),

            // Add Ingredient Row
            Card(
              color: theme.colorScheme.surfaceVariant.withOpacity(0.4),
              child: Padding(
                padding: const EdgeInsets.all(12.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("Add Ingredient", style: theme.textTheme.labelLarge),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          flex: 3,
                          child: TextField(
                            controller: _newFoodNameController,
                            decoration: InputDecoration(
                              hintText: "e.g., Paneer, Dal, Ghee",
                              isDense: true,
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          flex: 2,
                          child: TextField(
                            controller: _newQtyController,
                            keyboardType: TextInputType.number,
                            decoration: InputDecoration(
                              hintText: "100",
                              isDense: true,
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        DropdownButton<String>(
                          value: _newUnit,
                          items: ["g", "cup", "tbsp", "tsp", "piece", "bowl", "ml"]
                              .map((u) => DropdownMenuItem(value: u, child: Text(u)))
                              .toList(),
                          onChanged: (val) {
                            if (val != null) setState(() => _newUnit = val);
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Align(
                      alignment: Alignment.centerRight,
                      child: FilledButton.tonalIcon(
                        onPressed: _addIngredient,
                        icon: const Icon(Icons.add, size: 18),
                        label: const Text("Add Ingredient"),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Calculation Results Card
            if (_calculationResult != null) ...[
              Card(
                color: theme.colorScheme.primaryContainer.withOpacity(0.3),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text("Calculated Nutrition", style: theme.textTheme.titleMedium),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: AppTheme.sagePrimary.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: const Text("Method C", style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      _buildMacroGrid("Per Serving", _calculationResult!['per_serving']),
                      const Divider(height: 24),
                      _buildMacroGrid("Per 100g Cooked", _calculationResult!['per_100g']),
                      const Divider(height: 24),
                      _buildMacroGrid("Entire Recipe Total", _calculationResult!['total_recipe']),
                      if (_calculationResult!['notes'] != null) ...[
                        const SizedBox(height: 8),
                        Text(
                          _calculationResult!['notes'],
                          style: TextStyle(fontSize: 12, color: theme.textTheme.bodySmall?.color),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Action Buttons
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _isSaving ? null : () => _saveRecipe(andLog: false),
                    icon: const Icon(Icons.bookmark_add_outlined),
                    label: const Text("Save Recipe"),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: _isSaving ? null : () => _saveRecipe(andLog: true),
                    icon: const Icon(Icons.restaurant_rounded),
                    label: const Text("Save & Log 1 Serving"),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildMacroGrid(String title, Map<String, dynamic>? data) {
    if (data == null) return const SizedBox.shrink();
    final cal = (data['energy_kcal'] as num?)?.round() ?? 0;
    final p = (data['protein_g'] as num?)?.toStringAsFixed(1) ?? "0";
    final c = (data['carbohydrate_g'] as num?)?.toStringAsFixed(1) ?? "0";
    final f = (data['fat_g'] as num?)?.toStringAsFixed(1) ?? "0";
    final fib = (data['fiber_g'] as num?)?.toStringAsFixed(1) ?? "0";

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
            Text("$cal kcal", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppTheme.deepTealAccent)),
          ],
        ),
        const SizedBox(height: 6),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text("P: ${p}g", style: const TextStyle(fontSize: 12, color: AppTheme.proteinColor)),
            Text("C: ${c}g", style: const TextStyle(fontSize: 12, color: AppTheme.carbColor)),
            Text("F: ${f}g", style: const TextStyle(fontSize: 12, color: AppTheme.fatColor)),
            Text("Fib: ${fib}g", style: const TextStyle(fontSize: 12, color: AppTheme.fiberColor)),
          ],
        ),
      ],
    );
  }
}
