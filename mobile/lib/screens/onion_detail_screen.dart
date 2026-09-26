import 'package:flutter/material.dart';
import '../models/analysis_result.dart';
import '../services/api_service.dart';

class OnionDetailScreen extends StatelessWidget {
  final ApiService api;
  final Onion onion;
  const OnionDetailScreen({super.key, required this.api, required this.onion});
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text('Onion #${onion.id}')),
    body: ListView(padding: const EdgeInsets.all(24), children: [
      if (onion.cropUrl != null) Image.network(api.url(onion.cropUrl!).toString(), height: 220,
        errorBuilder: (_, __, ___) => const Text('Crop unavailable')),
      Text('Final classification: ${labels[onion.finalClass]}', style: Theme.of(context).textTheme.titleLarge),
      const SizedBox(height: 16),
      Text('CLIP condition: ${labels[onion.condition]}'),
      if (onion.data['needs_review'] == true) const Text('Low confidence — review this prediction.'),
      Text('Relative confidence score: ${(onion.confidence * 100).toStringAsFixed(1)}%'),
      Text('Estimated diameter: ${onion.diameter == null ? 'Unknown (no scale)' : '${onion.diameter!.toStringAsFixed(1)} cm'}'),
      const SizedBox(height: 24),
      const Text('CLIP diagnostics', style: TextStyle(fontWeight: FontWeight.bold)),
      for (final entry in onion.scores.entries) ListTile(contentPadding: EdgeInsets.zero,
        title: Text(labels[entry.key] ?? entry.key),
        subtitle: Text('Cosine similarity: ${(onion.similarities[entry.key] as num).toStringAsFixed(3)}'),
        trailing: Text('${((entry.value as num) * 100).toStringAsFixed(1)}%')),
      const Text('Relative scores are not calibrated probabilities. Physical sizing comes from geometry, not CLIP.'),
    ]),
  );
}
