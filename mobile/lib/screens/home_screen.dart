import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/api_service.dart';
import 'image_preview_screen.dart';

class HomeScreen extends StatefulWidget {
  final ApiService api;
  const HomeScreen({super.key, required this.api});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final picker = ImagePicker();
  bool picking = false;
  @override
  void initState() { super.initState(); recover(); }
  Future<void> recover() async {
    try {
      final lost = await picker.retrieveLostData();
      if (lost.files?.isNotEmpty ?? false) { open(lost.files!.first); }
    } catch (_) { /* Recovery is only supported on Android. */ }
  }
  void open(XFile image) {
    if (mounted) {
      Navigator.push(context, MaterialPageRoute<void>(builder: (_) => ImagePreviewScreen(api: widget.api, image: image)));
    }
  }
  Future<void> pick(ImageSource source) async {
    setState(() => picking = true);
    try {
      final image = await picker.pickImage(source: source, imageQuality: 95, maxWidth: 3000, maxHeight: 3000);
      if (image != null) { open(image); }
    } catch (error) {
      if (mounted) { ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Cannot open image: $error'))); }
    } finally { if (mounted) { setState(() => picking = false); } }
  }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Onion Quality Analyzer')),
    body: Center(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 560),
      child: ListView(padding: const EdgeInsets.all(24), shrinkWrap: true, children: [
        const Icon(Icons.eco_outlined, size: 80, color: Color(0xff526c35)),
        const SizedBox(height: 24),
        Text('Know your onion lot', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 12),
        const Text('Place separated onions on a clean contrasting background. Keep the image edges clear. Photograph from above with uniform light.'),
        const SizedBox(height: 12),
        const Text('Include the printed 5 cm ArUco marker to estimate size. Without it, Grade A refers to healthy appearance and size remains unmeasured.'),
        const SizedBox(height: 28),
        FilledButton.icon(onPressed: picking ? null : () => pick(ImageSource.camera), icon: const Icon(Icons.camera_alt_outlined), label: const Text('Capture Image')),
        const SizedBox(height: 12),
        OutlinedButton.icon(onPressed: picking ? null : () => pick(ImageSource.gallery), icon: const Icon(Icons.photo_library_outlined), label: const Text('Upload Image')),
        const SizedBox(height: 24),
        const Text('Academic prototype • Verify results manually. AI appearance scores are not certified grades.', textAlign: TextAlign.center),
      ]))),
  );
}
