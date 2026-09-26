import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import '../models/analysis_result.dart';

class ApiService {
  // Android emulator -> host PC. Override for iOS or a physical phone.
  final String baseUrl;
  ApiService({this.baseUrl = const String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8001')});
  Uri url(String path) => Uri.parse('${baseUrl.replaceAll(RegExp(r'/+$'), '')}$path');

  Map<String, dynamic> decode(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      String message = 'Server error ${response.statusCode}';
      try { message = (jsonDecode(response.body) as Map)['detail'].toString(); } catch (_) { /* Non-JSON proxy error. */ }
      throw Exception(message);
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<AnalysisResult> analyze(XFile image) async {
    if (await image.length() > 12 * 1024 * 1024) {
      throw Exception('Choose an image smaller than 12 MB.');
    }
    final client = http.Client();
    try {
      final request = http.MultipartRequest('POST', url('/analyze'));
      request.files.add(http.MultipartFile.fromBytes('image', await image.readAsBytes(), filename: image.name));
      final response = await client.send(request).then(http.Response.fromStream).timeout(const Duration(minutes: 3));
      return AnalysisResult(decode(response));
    } finally { client.close(); }
  }

  Future<String> createReport(String id) async {
    final response = await http.post(url('/generate-report'),
        headers: {'Content-Type': 'application/json'}, body: jsonEncode({'report_id': id}))
        .timeout(const Duration(seconds: 45));
    return decode(response)['pdf_url'] as String;
  }

  Future<Uint8List> download(String path) async {
    final response = await http.get(url(path)).timeout(const Duration(seconds: 45));
    if (response.statusCode != 200) { throw Exception('PDF download failed.'); }
    return response.bodyBytes;
  }
}
