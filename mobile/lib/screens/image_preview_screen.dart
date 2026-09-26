import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/api_service.dart';
import 'processing_screen.dart';

class ImagePreviewScreen extends StatefulWidget {
  final ApiService api;
  final XFile image;
  const ImagePreviewScreen({super.key, required this.api, required this.image});
  @override
  State<ImagePreviewScreen> createState() => _ImagePreviewScreenState();
}
class _ImagePreviewScreenState extends State<ImagePreviewScreen> {
  late final Future<Uint8List> bytes = widget.image.readAsBytes();
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Image Preview')),
    body: Column(children: [
      Expanded(child: FutureBuilder<Uint8List>(future: bytes, builder: (context, snapshot) {
        if (snapshot.hasError) { return const Center(child: Text('Image could not be opened. Select JPEG or PNG.')); }
        if (!snapshot.hasData) { return const Center(child: CircularProgressIndicator()); }
        return InteractiveViewer(child: Image.memory(snapshot.data!, fit: BoxFit.contain));
      })),
      Padding(padding: const EdgeInsets.all(20), child: Row(children: [
        Expanded(child: OutlinedButton(onPressed: () => Navigator.pop(context), child: const Text('Retake / Reselect'))),
        const SizedBox(width: 12),
        Expanded(child: FilledButton(onPressed: () => Navigator.push(context,
          MaterialPageRoute<void>(builder: (_) => ProcessingScreen(api: widget.api, image: widget.image))),
          child: const Text('Analyze Quality'))),
      ])),
    ]),
  );
}
