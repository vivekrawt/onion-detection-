import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:onion_quality_analyzer/main.dart';
import 'package:onion_quality_analyzer/models/analysis_result.dart';

void main() {
  testWidgets('home offers capture and upload', (tester) async {
    await tester.pumpWidget(OnionApp());
    expect(find.text('Capture Image'), findsOneWidget);
    expect(find.text('Upload Image'), findsOneWidget);
    expect(find.byType(FilledButton), findsOneWidget);
  });
  test('size can remain unknown', () {
    final onion = Onion({'estimated_diameter_cm': null, 'confidence': 0.5});
    expect(onion.diameter, isNull);
    expect(onion.confidence, 0.5);
  });
}
