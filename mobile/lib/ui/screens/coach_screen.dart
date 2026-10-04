import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/services/stt_service.dart';
import '../../models/app_models.dart';
import '../../providers/app_providers.dart';

class CoachScreen extends StatefulWidget {
  const CoachScreen({super.key});

  @override
  State<CoachScreen> createState() => _CoachScreenState();
}

class _CoachScreenState extends State<CoachScreen> {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final SttService _sttService = SttService();

  bool _isListening = false;

  final List<String> _quickPrompts = [
    "How is my energy balance today?",
    "Suggest high-protein Indian snacks",
    "Did I meet my fiber goal today?",
    "What should I eat for dinner to stay in deficit?",
    "How many calories are in 2 rotis with dal?",
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final coachProv = Provider.of<CoachProvider>(context, listen: false);
      if (coachProv.messages.isEmpty) {
        coachProv.loadHistory();
      }
    });
  }

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    _sttService.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent + 60,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage([String? customText]) async {
    final text = customText ?? _textController.text.trim();
    if (text.isEmpty) return;

    _textController.clear();
    final coachProv = Provider.of<CoachProvider>(context, listen: false);
    _scrollToBottom();
    await coachProv.sendMessage(text);
    _scrollToBottom();
  }

  Future<void> _toggleVoiceRecording() async {
    if (_isListening) {
      await _sttService.stopListening();
      setState(() => _isListening = false);
    } else {
      setState(() => _isListening = true);
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
                "Voice recognition unavailable. Allow microphone access and check that speech services are installed.",
              ),
            ),
          );
        }
      }
    }
  }

  void _handleActionButton(ActionButtonModel button) {
    if (button.actionType == 'log_meal') {
      Navigator.pushNamed(context, '/log');
    } else if (button.actionType == 'clarify') {
      _sendMessage("I want to clarify: ${button.label}");
    } else {
      _sendMessage("Tell me more about: ${button.label}");
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final coachProv = Provider.of<CoachProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            CircleAvatar(
              radius: 16,
              backgroundColor: theme.colorScheme.primary.withOpacity(0.15),
              child: Icon(Icons.psychology_rounded,
                  color: theme.colorScheme.primary, size: 20),
            ),
            const SizedBox(width: 10),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("AI Nutrition Coach",
                    style:
                        TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                Text("Powered by INDB & LangGraph",
                    style: TextStyle(fontSize: 11, color: Colors.grey)),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_sweep_outlined),
            tooltip: "Clear History",
            onPressed: () => _confirmClearHistory(context, coachProv),
          ),
        ],
      ),
      body: Column(
        children: [
          // Medical Safety Disclaimer Banner
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
            color: theme.colorScheme.secondaryContainer.withOpacity(0.3),
            child: Row(
              children: [
                Icon(Icons.shield_outlined,
                    size: 14, color: theme.colorScheme.secondary),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    "AI Coach provides nutritional guidance, not medical diagnosis or treatment.",
                    style: TextStyle(fontSize: 11),
                  ),
                ),
              ],
            ),
          ),

          // Messages List
          Expanded(
            child: coachProv.messages.isEmpty && !coachProv.isSending
                ? _buildEmptyState(theme)
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 12),
                    itemCount: coachProv.messages.length +
                        (coachProv.isSending ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index == coachProv.messages.length) {
                        return _buildThinkingIndicator(theme);
                      }
                      final msg = coachProv.messages[index];
                      return _buildMessageBubble(msg, theme);
                    },
                  ),
          ),

          // Quick Prompt Suggestions (Horizontal Chips)
          Container(
            height: 44,
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: _quickPrompts.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (context, index) {
                return ActionChip(
                  label: Text(_quickPrompts[index],
                      style: const TextStyle(fontSize: 11)),
                  onPressed: () => _sendMessage(_quickPrompts[index]),
                );
              },
            ),
          ),

          // Bottom Input Bar
          Container(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            decoration: BoxDecoration(
              color: theme.scaffoldBackgroundColor,
              border: Border(
                  top: BorderSide(color: theme.dividerColor.withOpacity(0.1))),
            ),
            child: Row(
              children: [
                // Voice button
                IconButton.filledTonal(
                  onPressed: _toggleVoiceRecording,
                  icon: Icon(
                      _isListening ? Icons.stop_rounded : Icons.mic_rounded),
                  style: IconButton.styleFrom(
                    backgroundColor:
                        _isListening ? Colors.red.withOpacity(0.2) : null,
                    foregroundColor:
                        _isListening ? Colors.red : theme.colorScheme.primary,
                  ),
                ),
                const SizedBox(width: 8),

                // Text field
                Expanded(
                  child: TextField(
                    controller: _textController,
                    minLines: 1,
                    maxLines: 4,
                    decoration: InputDecoration(
                      hintText: _isListening
                          ? "Listening..."
                          : "Ask your coach or log food...",
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24)),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 10),
                      isDense: true,
                    ),
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                const SizedBox(width: 8),

                // Send button
                IconButton.filled(
                  onPressed: coachProv.isSending ? null : () => _sendMessage(),
                  icon: const Icon(Icons.send_rounded, size: 20),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(ThemeData theme) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircleAvatar(
              radius: 36,
              backgroundColor: theme.colorScheme.primary.withOpacity(0.1),
              child: Icon(Icons.psychology_rounded,
                  size: 40, color: theme.colorScheme.primary),
            ),
            const SizedBox(height: 16),
            Text("Namaste! I'm your Nutrition Coach.",
                style: theme.textTheme.titleMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(
              "I monitor your calories, macros, energy balance, and Indian recipes. Ask me anything or tell me what you ate!",
              textAlign: TextAlign.center,
              style: TextStyle(
                  color: theme.textTheme.bodyMedium?.color?.withOpacity(0.7),
                  fontSize: 13),
            ),
            const SizedBox(height: 20),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: _quickPrompts.map((prompt) {
                return ActionChip(
                  avatar: const Icon(Icons.auto_awesome, size: 14),
                  label: Text(prompt, style: const TextStyle(fontSize: 12)),
                  onPressed: () => _sendMessage(prompt),
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMessageBubble(ChatMessageModel msg, ThemeData theme) {
    final isUser = msg.role.toLowerCase() == 'user';

    return Padding(
      padding: const EdgeInsets.only(bottom: 12.0),
      child: Row(
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isUser) ...[
            CircleAvatar(
              radius: 14,
              backgroundColor: theme.colorScheme.primary,
              child: const Icon(Icons.smart_toy_rounded,
                  size: 16, color: Colors.white),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Column(
              crossAxisAlignment:
                  isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: isUser
                        ? theme.colorScheme.primary
                        : theme.colorScheme.surfaceVariant.withOpacity(0.7),
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(16),
                      topRight: const Radius.circular(16),
                      bottomLeft: isUser
                          ? const Radius.circular(16)
                          : const Radius.circular(4),
                      bottomRight: isUser
                          ? const Radius.circular(4)
                          : const Radius.circular(16),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        msg.content,
                        style: TextStyle(
                          color: isUser
                              ? Colors.white
                              : theme.textTheme.bodyLarge?.color,
                          fontSize: 14,
                          height: 1.4,
                        ),
                      ),
                      if (msg.uncertaintyFlag) ...[
                        const SizedBox(height: 6),
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.help_outline,
                                size: 13,
                                color: isUser
                                    ? Colors.white70
                                    : Colors.amber.shade800),
                            const SizedBox(width: 4),
                            Text(
                              "Portion estimates flagged for review",
                              style: TextStyle(
                                fontSize: 11,
                                color: isUser
                                    ? Colors.white70
                                    : Colors.amber.shade900,
                                fontStyle: FontStyle.italic,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),

                // Suggested clarification options
                if (msg.suggestedOptions.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: msg.suggestedOptions.map((opt) {
                      return ActionChip(
                        label: Text(opt, style: const TextStyle(fontSize: 11)),
                        onPressed: () => _sendMessage(opt),
                      );
                    }).toList(),
                  ),
                ],

                // Action Buttons
                if (msg.actionButtons.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: msg.actionButtons.map((btn) {
                      return FilledButton.tonalIcon(
                        onPressed: () => _handleActionButton(btn),
                        icon: const Icon(Icons.touch_app_rounded, size: 14),
                        label: Text(btn.label,
                            style: const TextStyle(fontSize: 11)),
                        style: FilledButton.styleFrom(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 4),
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                      );
                    }).toList(),
                  ),
                ],
              ],
            ),
          ),
          if (isUser) ...[
            const SizedBox(width: 8),
            CircleAvatar(
              radius: 14,
              backgroundColor: theme.colorScheme.secondary,
              child: const Icon(Icons.person, size: 16, color: Colors.white),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildThinkingIndicator(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          CircleAvatar(
            radius: 14,
            backgroundColor: theme.colorScheme.primary,
            child: const Icon(Icons.smart_toy_rounded,
                size: 16, color: Colors.white),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: theme.colorScheme.surfaceVariant.withOpacity(0.5),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
                SizedBox(width: 8),
                Text("Analyzing nutrition & goals...",
                    style:
                        TextStyle(fontSize: 12, fontStyle: FontStyle.italic)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _confirmClearHistory(BuildContext context, CoachProvider provider) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Clear Chat History?"),
        content: const Text(
            "This will delete previous coach messages from this device."),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx), child: const Text("Cancel")),
          FilledButton(
            onPressed: () {
              provider.clearHistory();
              Navigator.pop(ctx);
            },
            child: const Text("Clear"),
          ),
        ],
      ),
    );
  }
}
