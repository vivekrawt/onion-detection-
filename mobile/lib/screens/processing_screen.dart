import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/api_service.dart';
import 'result_screen.dart';

class ProcessingScreen extends StatefulWidget {
  final ApiService api;
  final XFile image;
  const ProcessingScreen({super.key, required this.api, required this.image});
  @override
  State<ProcessingScreen> createState() => _ProcessingScreenState();
}
class _ProcessingScreenState extends State<ProcessingScreen> {
  String? error;
  @override
  void initState() { super.initState(); analyze(); }
  Future<void> analyze() async {
    setState(() => error = null);
    try {
      final result = await widget.api.analyze(widget.image);
      if (!mounted) { return; }
      Navigator.pushReplacement(context, MaterialPageRoute<void>(builder: (_) => ResultScreen(api: widget.api, result: result)));
    } catch (exception) { if (mounted) { setState(() => error = exception.toString()); } }
  }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Processing')),
    body: Center(child: Padding(padding: const EdgeInsets.all(28), child: Column(mainAxisSize: MainAxisSize.min, children: [
      if (error == null) ...[
        const CircularProgressIndicator(), const SizedBox(height: 24), const Text('Analyzing onion quality...'),
      ] else ...[
        Text(error!, textAlign: TextAlign.center), const SizedBox(height: 16),
        FilledButton(onPressed: analyze, child: const Text('Retry')),
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Back to Image')),
      ],
    ]))),
  );
}
