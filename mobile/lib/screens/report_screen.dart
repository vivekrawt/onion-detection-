import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/analysis_result.dart';
import '../services/api_service.dart';

class ReportScreen extends StatefulWidget {
  final ApiService api;
  final AnalysisResult result;
  const ReportScreen({super.key, required this.api, required this.result});
  @override
  State<ReportScreen> createState() => _ReportScreenState();
}
class _ReportScreenState extends State<ReportScreen> {
  String? pdf;
  bool busy = false;
  Future<void> useReport(bool share) async {
    setState(() => busy = true);
    try {
      pdf ??= await widget.api.createReport(widget.result.reportId);
      if (share) {
        final bytes = await widget.api.download(pdf!);
        if (!mounted) { return; }
        final box = context.findRenderObject() as RenderBox?;
        await Share.shareXFiles([XFile.fromData(bytes, mimeType: 'application/pdf')],
          fileNameOverrides: ['onion-${widget.result.reportId}.pdf'],
          sharePositionOrigin: box == null ? null : box.localToGlobal(Offset.zero) & box.size);
      } else {
        if (!await launchUrl(widget.api.url(pdf!), mode: LaunchMode.externalApplication)) {
          throw Exception('Could not open PDF download.');
        }
      }
    } catch (error) {
      if (mounted) { ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString()))); }
    } finally { if (mounted) { setState(() => busy = false); } }
  }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Digital Quality Report')),
    body: ListView(padding: const EdgeInsets.all(24), children: [
      Text('Onion quality assessment', style: Theme.of(context).textTheme.headlineSmall),
      const SizedBox(height: 20), SelectableText('Report ID: ${widget.result.reportId}'),
      Text('Date & time: ${widget.result.date}'),
      Text('Total onions: ${widget.result.total}'),
      Text('Grade A: ${widget.result.percentage('grade_a')}%'), Text('URS: ${widget.result.urs}%'),
      const Divider(height: 32),
      for (final entry in labels.entries) ListTile(contentPadding: EdgeInsets.zero,
        title: Text(entry.value), trailing: Text('${widget.result.count(entry.key)} / ${widget.result.percentage(entry.key)}%')),
      const Text('This assessment is generated using an AI-based prototype and should be validated against official onion grading standards before commercial deployment.'),
      const SizedBox(height: 20),
      if (busy) const LinearProgressIndicator(),
      FilledButton(onPressed: busy ? null : () => useReport(false), child: const Text('Download PDF')),
      OutlinedButton(onPressed: busy ? null : () => useReport(true), child: const Text('Share Report')),
      TextButton(onPressed: () => Navigator.popUntil(context, (route) => route.isFirst), child: const Text('Analyze New Lot')),
    ]),
  );
}
