import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'services/api_service.dart';

void main() => runApp(OnionApp());

class OnionApp extends StatelessWidget {
  OnionApp({super.key});
  final ApiService api = ApiService();
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Onion Quality Analyzer', debugShowCheckedModeBanner: false,
    theme: ThemeData(useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff526c35)),
      scaffoldBackgroundColor: const Color(0xfffaf9f3),
      appBarTheme: const AppBarTheme(centerTitle: false)),
    home: HomeScreen(api: api),
  );
}
