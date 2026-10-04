import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/api_constants.dart';
import '../../core/network/api_client.dart';
import '../../core/services/stt_service.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/app_providers.dart';
import 'recipe_builder_screen.dart';
import 'recipe_library_screen.dart';

class LogFoodScreen extends StatefulWidget {
  final String? initialMealType;
  final int initialTab;

  const LogFoodScreen({super.key, this.initialMealType, this.initialTab = 0});

  @override
  State<LogFoodScreen> createState() => _LogFoodScreenState();
}

class _LogFoodScreenState extends State<LogFoodScreen>
    with SingleTickerProviderStateMixin {
  final ApiClient _api = ApiClient();
  final SttService _sttService = SttService();
  final TextEditingController _textController = TextEditingController();

  late TabController _tabController;
  String _selectedMealType = 'lunch';
  bool _isParsing = false;
  bool _isLogging = false;
  bool _isListening = false;

  List<Map<String, dynamic>> _parsedItems = [];
  List<Map<String, dynamic>> _pendingMealItems = [];
  final Map<String, List<String>> _selectedMealOptions = {};
  Map<String, dynamic>? _lastParseResult;

  final List<String> _mealTypes = ['breakfast', 'lunch', 'dinner', 'snack'];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(
      length: 3,
      vsync: this,
      initialIndex: widget.initialTab.clamp(0, 2),
    );
    if (widget.initialMealType != null) {
      _selectedMealType = widget.initialMealType!.toLowerCase();
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    _textController.dispose();
    _sttService.dispose();
    super.dispose();
  }

  Future<void> _toggleVoiceRecording() async {
    if (_isListening) {
      await _sttService.stopListening();
      setState(() => _isListening = false);
    } else {
      setState(() {
        _isListening = true;
      });

      final success = await _sttService.startListening(
        onResult: (text, isFinal) {
          if (!mounted) return;
          setState(() {
            _textController.text = text;
            if (isFinal) _isListening = false;
          });
        },
        onStatusChange: (status) {
          if (!mounted) return;
          setState(() => _isListening = status == 'listening');
        },
        onError: (error) {
          if (!mounted) return;
          setState(() => _isListening = false);
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                error == 'error_network'
                    ? "Speech recognition needs internet access. Check the emulator's connection and try again."
                    : "Speech recognition failed ($error). Check microphone access and installed speech languages.",
              ),
            ),
          );
        },
      );

      if (!success) {
        if (mounted) setState(() => _isListening = false);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
                content: Text(
                    "Voice recognition unavailable. Allow microphone access and check that speech services are installed.")),
          );
        }
      }
    }
  }

  Future<void> _parseText({
    String? textOverride,
    bool isClarification = false,
  }) async {
    final text = (textOverride ?? _textController.text).trim();
    if (text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text("Please enter or speak a meal description")),
      );
      return;
    }

    if (!isClarification) {
      _pendingMealItems = [];
      _selectedMealOptions.clear();
    }

    setState(() => _isParsing = true);
    try {
      final query = <String, String>{
        'text': text,
        'meal_type': _selectedMealType,
        if (isClarification && _pendingMealItems.isNotEmpty)
          'parsed_items': jsonEncode(
            _pendingMealItems
                .map((item) => {
                      'food_query': item['food_query'],
                      'quantity': item['quantity'],
                      'unit': item['unit'],
                    })
                .toList(),
          ),
        if (isClarification && _selectedMealOptions.isNotEmpty)
          'selected_options': jsonEncode(_selectedMealOptions),
      }
          .entries
          .map((entry) =>
              '${Uri.encodeQueryComponent(entry.key)}=${Uri.encodeQueryComponent(entry.value)}')
          .join('&');
      final res = await _api.post(
        "${ApiConstants.mealsParseText}?$query",
      );

      setState(() {
        _lastParseResult = res;
        _pendingMealItems =
            List<Map<String, dynamic>>.from(res['pending_items'] ?? []);
        _parsedItems =
            List<Map<String, dynamic>>.from(res['recognized_items'] ?? []);
      });

      // If uncertain, show clarification dialog
      if (res['has_uncertainty'] == true && res['clarifications'] != null) {
        final List clarifications = res['clarifications'];
        if (clarifications.isNotEmpty && mounted) {
          _showClarificationDialog(clarifications);
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Parsing failed: $e")),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isParsing = false);
      }
    }
  }

  void _showClarificationDialog(List clarifications) {
    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: Row(
            children: [
              Icon(Icons.help_outline_rounded,
                  color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  "A little more detail",
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  "Select the option that best matches what you had. We’ll update the food details from the dataset.",
                  style: TextStyle(fontSize: 13),
                ),
                const SizedBox(height: 12),
                ...clarifications.map((item) {
                  final itemName = item['item_name'] ?? 'Item';
                  final itemKey =
                      item['item_key']?.toString() ?? itemName.toString();
                  final question = item['question'] ?? 'Select portion';
                  final List options = item['options'] ?? [];
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(question,
                            style: const TextStyle(
                                fontWeight: FontWeight.w600, fontSize: 13)),
                        const SizedBox(height: 6),
                        Wrap(
                          spacing: 6,
                          runSpacing: 6,
                          children: options.map<Widget>((opt) {
                            return ActionChip(
                              label: Text(opt.toString(),
                                  style: const TextStyle(fontSize: 11)),
                              onPressed: () {
                                Navigator.pop(ctx);
                                _applyClarificationOption(
                                  itemKey,
                                  opt.toString(),
                                );
                              },
                            );
                          }).toList(),
                        ),
                      ],
                    ),
                  );
                }),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text("Close"),
            ),
          ],
        );
      },
    );
  }

  Future<void> _applyClarificationOption(
      String itemKey, String optionText) async {
    final originalText = _textController.text.trim();
    final options = _selectedMealOptions.putIfAbsent(itemKey, () => []);
    if (!options.contains(optionText)) {
      options.add(optionText);
    }
    await _parseText(
      textOverride: originalText,
      isClarification: true,
    );
  }

  Future<void> _logMeal() async {
    if (_parsedItems.isEmpty) return;
    if (_lastParseResult?['has_uncertainty'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            "Please clarify every food before logging the complete meal.",
          ),
        ),
      );
      return;
    }

    setState(() => _isLogging = true);
    final nutritionProvider =
        Provider.of<NutritionProvider>(context, listen: false);

    try {
      final itemsPayload = _parsedItems.map((item) {
        return {
          'food_id': item['food_id'],
          'recipe_id': item['recipe_id'],
          'dietary_confirmed': item['dietary_confirmed'] ?? false,
          'item_name': item['item_name'],
          'quantity': item['quantity'],
          'unit': item['unit'] ?? item['serving_unit'],
          'weight_g': item['weight_g'],
          'calories': item['calories'],
          'protein': item['protein'],
          'carbs': item['carbs'],
          'fat': item['fat'],
          'fiber': item['fiber'],
          'confidence_score': item['confidence_score'] ?? 1.0,
        };
      }).toList();

      await nutritionProvider.logMealDirect(
        mealType: _selectedMealType,
        items: itemsPayload,
        notes: _textController.text.trim(),
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("Logged $_selectedMealType meal successfully!"),
            backgroundColor: AppTheme.sagePrimary,
          ),
        );
        Navigator.pop(context);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Error logging meal: $e")),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLogging = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text("Log Food"),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: theme.colorScheme.primary,
          labelColor: theme.colorScheme.primary,
          unselectedLabelColor:
              theme.textTheme.bodyMedium?.color?.withOpacity(0.6),
          tabs: const [
            Tab(icon: Icon(Icons.edit_note_rounded), text: "Quick / Voice"),
            Tab(icon: Icon(Icons.menu_book_rounded), text: "Saved Recipes"),
            Tab(icon: Icon(Icons.soup_kitchen_rounded), text: "Recipe Builder"),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildQuickVoiceTab(theme),
          RecipeLibraryScreen(
            isSelectMode: true,
            initialMealType: _selectedMealType,
          ),
          const RecipeBuilderScreen(),
        ],
      ),
    );
  }

  Widget _buildQuickVoiceTab(ThemeData theme) {
    double totalCalories = 0;
    double totalProtein = 0;
    double totalCarbs = 0;
    double totalFat = 0;

    for (var i in _parsedItems) {
      totalCalories += (i['calories'] as num?)?.toDouble() ?? 0;
      totalProtein += (i['protein'] as num?)?.toDouble() ?? 0;
      totalCarbs += (i['carbs'] as num?)?.toDouble() ?? 0;
      totalFat += (i['fat'] as num?)?.toDouble() ?? 0;
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Meal Type Selector
          Text("Meal Category", style: theme.textTheme.titleSmall),
          const SizedBox(height: 8),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: _mealTypes.map((type) {
                final isSelected = _selectedMealType == type;
                return Padding(
                  padding: const EdgeInsets.only(right: 8.0),
                  child: ChoiceChip(
                    label: Text(
                      type[0].toUpperCase() + type.substring(1),
                      style: TextStyle(
                        color: isSelected
                            ? Colors.white
                            : theme.textTheme.bodyLarge?.color,
                        fontWeight:
                            isSelected ? FontWeight.bold : FontWeight.normal,
                      ),
                    ),
                    selected: isSelected,
                    selectedColor: theme.colorScheme.primary,
                    onSelected: (val) {
                      if (val) setState(() => _selectedMealType = type);
                    },
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 16),

          // Voice and Text Input Card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text("Describe what you ate",
                          style: theme.textTheme.titleMedium),
                      if (_isListening)
                        Row(
                          children: [
                            Container(
                              width: 10,
                              height: 10,
                              decoration: const BoxDecoration(
                                  color: Colors.red, shape: BoxShape.circle),
                            ),
                            const SizedBox(width: 6),
                            const Text("Listening...",
                                style:
                                    TextStyle(color: Colors.red, fontSize: 12)),
                          ],
                        ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _textController,
                    maxLines: 3,
                    decoration: InputDecoration(
                      hintText:
                          "e.g., 2 rotis with 1 cup dal tadka and 1 bowl cucumber salad",
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12)),
                      contentPadding: const EdgeInsets.all(12),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      // Voice Record Button
                      IconButton.filledTonal(
                        onPressed: _toggleVoiceRecording,
                        icon: Icon(_isListening
                            ? Icons.stop_rounded
                            : Icons.mic_rounded),
                        style: IconButton.styleFrom(
                          backgroundColor:
                              _isListening ? Colors.red.withOpacity(0.2) : null,
                          foregroundColor: _isListening
                              ? Colors.red
                              : theme.colorScheme.primary,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _isParsing ? null : _parseText,
                          icon: _isParsing
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child:
                                      CircularProgressIndicator(strokeWidth: 2))
                              : const Icon(Icons.auto_awesome_rounded),
                          label: Text(_isParsing
                              ? "Analyzing INDB..."
                              : "Analyze Meal"),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Parsed Items Preview
          if (_parsedItems.isNotEmpty) ...[
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text("Recognized Foods", style: theme.textTheme.titleMedium),
                Text(
                  "${totalCalories.round()} kcal",
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: theme.colorScheme.primary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Macro summary pills
            Row(
              children: [
                _macroBadge("Protein", "${totalProtein.toStringAsFixed(1)}g",
                    AppTheme.proteinColor),
                const SizedBox(width: 8),
                _macroBadge("Carbs", "${totalCarbs.toStringAsFixed(1)}g",
                    AppTheme.carbColor),
                const SizedBox(width: 8),
                _macroBadge("Fat", "${totalFat.toStringAsFixed(1)}g",
                    AppTheme.fatColor),
              ],
            ),
            const SizedBox(height: 12),
            if (_lastParseResult?['has_uncertainty'] == true)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  "These totals include only matched foods. Clarify the remaining items to calculate the complete meal.",
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.error,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),

            ..._parsedItems.asMap().entries.map((entry) {
              final idx = entry.key;
              final item = entry.value;
              final confidence =
                  (item['confidence_score'] as num?)?.toDouble() ?? 1.0;
              final isLowConfidence = confidence < 0.70;

              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  title: Text(item['item_name'] ?? 'Food Item',
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "${item['quantity']} ${item['unit']} (~${(item['weight_g'] as num?)?.round() ?? 100}g)  •  ${(item['calories'] as num?)?.round()} kcal",
                        style: const TextStyle(fontSize: 13),
                      ),
                      if (isLowConfidence)
                        Padding(
                          padding: const EdgeInsets.only(top: 4.0),
                          child: Row(
                            children: [
                              Icon(Icons.info_outline,
                                  size: 14, color: Colors.amber.shade800),
                              const SizedBox(width: 4),
                              Text(
                                "Generic portion fallback (${(confidence * 100).toInt()}% conf)",
                                style: TextStyle(
                                    color: Colors.amber.shade900, fontSize: 11),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                  trailing: IconButton(
                    icon: const Icon(Icons.remove_circle_outline,
                        color: Colors.red),
                    onPressed: () {
                      setState(() {
                        _parsedItems.removeAt(idx);
                      });
                    },
                  ),
                ),
              );
            }),
            const SizedBox(height: 16),

            // Log Meal Button
            SizedBox(
              width: double.infinity,
              height: 50,
              child: FilledButton.icon(
                onPressed: _isLogging ? null : _logMeal,
                icon: _isLogging
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                            color: Colors.white, strokeWidth: 2))
                    : const Icon(Icons.check_circle_rounded),
                label:
                    Text(_isLogging ? "Saving Meal..." : "Confirm & Log Meal"),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _macroBadge(String name, String value, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 8),
        decoration: BoxDecoration(
          color: color.withOpacity(0.12),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Column(
          children: [
            Text(name,
                style: TextStyle(
                    fontSize: 11, color: color, fontWeight: FontWeight.w600)),
            const SizedBox(height: 2),
            Text(value,
                style: TextStyle(
                    fontSize: 13, color: color, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }
}
