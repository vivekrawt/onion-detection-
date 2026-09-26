import 'package:flutter/material.dart';
import '../models/analysis_result.dart';
import '../services/api_service.dart';
import 'onion_detail_screen.dart';
import 'report_screen.dart';

class ResultScreen extends StatelessWidget {
  final ApiService api;
  final AnalysisResult result;
  const ResultScreen({super.key, required this.api, required this.result});
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Quality Results')),
    body: ListView(padding: const EdgeInsets.all(20), children: [
      Text('${result.total} onions detected', style: Theme.of(context).textTheme.headlineMedium),
      const SizedBox(height: 16),
      Card(child: Padding(padding: const EdgeInsets.all(20), child: Wrap(spacing: 36, runSpacing: 16, children: [
        Text('Grade A\n${result.percentage('grade_a').toStringAsFixed(1)}%\n${result.count('grade_a')} onions', style: Theme.of(context).textTheme.titleLarge),
        Text('URS\n${result.urs.toStringAsFixed(1)}%\n${result.ursCount} onions', style: Theme.of(context).textTheme.titleLarge),
      ]))),
      for (final warning in result.warnings) Padding(padding: const EdgeInsets.symmetric(vertical: 8), child: Text(warning)),
      const SizedBox(height: 12),
      Text('Category breakdown', style: Theme.of(context).textTheme.titleLarge),
      for (final entry in labels.entries) ListTile(contentPadding: EdgeInsets.zero,
        title: Text(entry.value), subtitle: LinearProgressIndicator(value: result.percentage(entry.key) / 100),
        trailing: Text('${result.count(entry.key)}  •  ${result.percentage(entry.key).toStringAsFixed(1)}%')),
      Text('${result.data['needs_review_count'] ?? 0} predictions need review. Grade A describes healthy appearance; size is checked separately.'),
      const SizedBox(height: 20),
      Image.network(api.url(result.imageUrl).toString(), errorBuilder: (_, __, ___) => const Text('Analyzed image could not be loaded.')),
      const SizedBox(height: 16),
      FilledButton.icon(onPressed: () => Navigator.push(context, MaterialPageRoute<void>(builder: (_) => ReportScreen(api: api, result: result))),
        icon: const Icon(Icons.description_outlined), label: const Text('Digital Quality Report')),
      const SizedBox(height: 20),
      Text('Individual onions', style: Theme.of(context).textTheme.titleLarge),
      for (final onion in result.onions) ListTile(title: Text('Onion #${onion.id} — ${labels[onion.finalClass]}'),
        subtitle: Text(onion.diameter == null ? 'Size unknown' : '${onion.diameter!.toStringAsFixed(1)} cm'),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => Navigator.push(context, MaterialPageRoute<void>(builder: (_) => OnionDetailScreen(api: api, onion: onion)))),
    ]),
  );
}
