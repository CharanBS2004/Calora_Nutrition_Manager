import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../constants/api_constants.dart';

class ApiClient {
  static const _requestTimeout = Duration(seconds: 8);
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;
  ApiClient._internal();

  String _baseUrl = ApiConstants.defaultBaseUrl;
  String? _token;

  void setBaseUrl(String url) {
    _baseUrl = url.endsWith('/') ? url.substring(0, url.length - 1) : url;
  }

  String get baseUrl => _baseUrl;

  Future<void> setToken(String? token) async {
    _token = token;
    final prefs = await SharedPreferences.getInstance();
    if (token != null) {
      await prefs.setString('jwt_access_token', token);
    } else {
      await prefs.remove('jwt_access_token');
    }
  }

  Future<String?> getToken() async {
    if (_token != null) return _token;
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString('jwt_access_token');
    return _token;
  }

  Future<Map<String, String>> _headers() async {
    final token = await getToken();
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  Future<dynamic> get(String endpoint,
      {Map<String, dynamic>? queryParams}) async {
    var uriString = '$_baseUrl$endpoint';
    if (queryParams != null && queryParams.isNotEmpty) {
      final query = queryParams.entries
          .map((e) => '${e.key}=${Uri.encodeComponent(e.value.toString())}')
          .join('&');
      uriString += '?$query';
    }

    final headers = await _headers();
    final response = await http
        .get(Uri.parse(uriString), headers: headers)
        .timeout(_requestTimeout);
    return _handleResponse(response);
  }

  Future<dynamic> post(String endpoint, {dynamic body}) async {
    final headers = await _headers();
    final response = await http
        .post(
          Uri.parse('$_baseUrl$endpoint'),
          headers: headers,
          body: body != null ? jsonEncode(body) : null,
        )
        .timeout(_requestTimeout);
    return _handleResponse(response);
  }

  Future<dynamic> put(String endpoint, {dynamic body}) async {
    final headers = await _headers();
    final response = await http
        .put(
          Uri.parse('$_baseUrl$endpoint'),
          headers: headers,
          body: body != null ? jsonEncode(body) : null,
        )
        .timeout(_requestTimeout);
    return _handleResponse(response);
  }

  Future<dynamic> delete(String endpoint) async {
    final headers = await _headers();
    final response = await http
        .delete(Uri.parse('$_baseUrl$endpoint'), headers: headers)
        .timeout(_requestTimeout);
    return _handleResponse(response);
  }

  dynamic _handleResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      return jsonDecode(response.body);
    } else if (response.statusCode == 401) {
      throw Exception("Unauthorized: Please log in again.");
    } else {
      String errMsg = "Request failed (${response.statusCode})";
      try {
        final errJson = jsonDecode(response.body);
        if (errJson is Map && errJson.containsKey('detail')) {
          errMsg = errJson['detail'].toString();
        }
      } catch (_) {}
      throw Exception(errMsg);
    }
  }
}
