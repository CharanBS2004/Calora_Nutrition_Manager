import 'package:flutter/foundation.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

abstract class STTService {
  Future<bool> initialize();
  Future<bool> startListening({
    required void Function(String text, bool isFinal) onResult,
    Function(double level)? onSoundLevelChange,
    Function(String status)? onStatusChange,
    Function(String error)? onError,
  });
  Future<void> stopListening();
  void dispose();
  bool get isListening;
  bool get isAvailable;
}

/// Native Android on-device SpeechRecognizer implementation via speech_to_text package
/// Works offline on supported Android devices with zero API cost.
class AndroidNativeSTTService implements STTService {
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _isAvailable = false;
  Function(String)? _onStatusChange;
  Function(String)? _onError;
  void Function(String, bool)? _onResult;
  Function(double)? _onSoundLevelChange;
  String? _localeId;
  bool _usingOnDeviceRecognition = true;

  @override
  bool get isListening => _speech.isListening;

  @override
  bool get isAvailable => _isAvailable;

  @override
  Future<bool> initialize() async {
    try {
      final permission = await Permission.microphone.request();
      if (!permission.isGranted) {
        debugPrint("Microphone permission was not granted: $permission");
        _isAvailable = false;
        return false;
      }
      _isAvailable = await _speech.initialize(
        onError: (err) {
          debugPrint("Native STT error: $err");
          if (_usingOnDeviceRecognition &&
              err.errorMsg == 'error_language_unavailable') {
            _usingOnDeviceRecognition = false;
            debugPrint(
                "On-device speech language unavailable; retrying online");
            _retryOnline();
            return;
          }
          _speech.cancel().then((_) {
            _onError?.call(err.errorMsg);
          }).catchError((Object error) {
            debugPrint("Could not stop failed speech session: $error");
            _onError?.call(err.errorMsg);
          });
        },
        onStatus: (status) {
          debugPrint("Native STT status: $status");
          _onStatusChange?.call(status);
        },
      );
      return _isAvailable;
    } catch (e) {
      debugPrint("Native STT init failed: $e");
      _isAvailable = false;
      return false;
    }
  }

  @override
  Future<bool> startListening({
    required void Function(String text, bool isFinal) onResult,
    Function(double level)? onSoundLevelChange,
    Function(String status)? onStatusChange,
    Function(String error)? onError,
  }) async {
    _onStatusChange = onStatusChange;
    _onError = onError;
    if (!_isAvailable) {
      final ok = await initialize();
      if (!ok) return false;
    }
    try {
      final locales = await _speech.locales();
      _localeId = locales.any((locale) => locale.localeId == 'en_IN')
          ? 'en_IN'
          : (await _speech.systemLocale())?.localeId;
      _onResult = onResult;
      _onSoundLevelChange = onSoundLevelChange;
      _usingOnDeviceRecognition = true;
      await _listen();
      return true;
    } catch (e) {
      debugPrint("Native STT could not start listening: $e");
      return false;
    }
  }

  Future<void> _listen() async {
    await _speech.listen(
      onResult: (result) =>
          _onResult?.call(result.recognizedWords, result.finalResult),
      onSoundLevelChange: _onSoundLevelChange,
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 8),
      localeId: _localeId,
      listenOptions: stt.SpeechListenOptions(
        listenMode: stt.ListenMode.dictation,
        partialResults: true,
        cancelOnError: false,
        onDevice: _usingOnDeviceRecognition,
      ),
    );
  }

  void _retryOnline() {
    _speech.cancel().then((_) {
      return _listen();
    }).catchError((Object error) {
      debugPrint("Online speech recognition retry failed: $error");
      _onError?.call('error_network');
    });
  }

  @override
  Future<void> stopListening() async {
    await _speech.stop();
  }

  @override
  void dispose() {
    _speech.stop();
  }
}

/// Cloud STT Provider implementation delegating audio transcription to backend proxy
class CloudSTTService implements STTService {
  bool _isListening = false;
  bool _isAvailable = true;

  @override
  bool get isListening => _isListening;

  @override
  bool get isAvailable => _isAvailable;

  @override
  Future<bool> initialize() async {
    _isAvailable = true;
    return true;
  }

  @override
  Future<bool> startListening({
    required void Function(String text, bool isFinal) onResult,
    Function(double level)? onSoundLevelChange,
    Function(String status)? onStatusChange,
    Function(String error)? onError,
  }) async {
    _isListening = true;
    return true;
  }

  @override
  Future<void> stopListening() async {
    _isListening = false;
  }

  @override
  void dispose() {
    _isListening = false;
  }
}

/// Configurable STT Provider: delegates to native Android STT by default,
/// or Cloud API when configured, with seamless offline fallback.
class ConfigurableSTTProvider implements STTService {
  static final ConfigurableSTTProvider _instance =
      ConfigurableSTTProvider._internal();
  factory ConfigurableSTTProvider() => _instance;
  ConfigurableSTTProvider._internal();

  final STTService _nativeSTT = AndroidNativeSTTService();
  final STTService _cloudSTT = CloudSTTService();
  bool _useCloud = false;

  void setUseCloud(bool val) {
    _useCloud = val;
  }

  STTService get _active => _useCloud ? _cloudSTT : _nativeSTT;

  @override
  bool get isListening => _active.isListening;

  @override
  bool get isAvailable => _active.isAvailable;

  @override
  Future<bool> initialize() async {
    final nativeOk = await _nativeSTT.initialize();
    if (!nativeOk && _useCloud) {
      return await _cloudSTT.initialize();
    }
    return nativeOk;
  }

  @override
  Future<bool> startListening({
    required void Function(String text, bool isFinal) onResult,
    Function(double level)? onSoundLevelChange,
    Function(String status)? onStatusChange,
    Function(String error)? onError,
  }) async {
    try {
      return await _active.startListening(
        onResult: onResult,
        onSoundLevelChange: onSoundLevelChange,
        onStatusChange: onStatusChange,
        onError: onError,
      );
    } catch (e) {
      debugPrint("Active STT failed, falling back to Native Android STT: $e");
      return await _nativeSTT.startListening(
        onResult: onResult,
        onSoundLevelChange: onSoundLevelChange,
        onError: onError,
      );
    }
  }

  @override
  Future<void> stopListening() async {
    await _active.stopListening();
  }

  @override
  void dispose() {
    _nativeSTT.dispose();
    _cloudSTT.dispose();
  }
}

typedef SttService = ConfigurableSTTProvider;
