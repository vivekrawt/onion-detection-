const labels = <String, String>{
  'grade_a': 'Grade A', 'damaged': 'Damaged', 'rotten': 'Rotten',
  'sprouted': 'Sprouted', 'undersized': 'Undersized',
};

class Onion {
  final Map<String, dynamic> data;
  Onion(this.data);
  int get id => data['id'] as int;
  String get finalClass => data['final_class'] as String;
  String get condition => data['condition'] as String;
  double get confidence => (data['confidence'] as num).toDouble();
  double? get diameter => (data['estimated_diameter_cm'] as num?)?.toDouble();
  String? get cropUrl => data['crop_url'] as String?;
  Map<String, dynamic> get scores => Map<String, dynamic>.from(data['scores'] as Map);
  Map<String, dynamic> get similarities => Map<String, dynamic>.from(data['similarities'] as Map);
}

class AnalysisResult {
  final Map<String, dynamic> data;
  AnalysisResult(this.data);
  String get reportId => data['report_id'] as String;
  DateTime get date => DateTime.parse(data['created_at'] as String).toLocal();
  int get total => data['total_onions'] as int;
  int count(String category) => (data[category] as Map)['count'] as int;
  double percentage(String category) => ((data[category] as Map)['percentage'] as num).toDouble();
  double get urs => (data['urs_percentage'] as num).toDouble();
  int get ursCount => data['urs_count'] as int;
  String get imageUrl => data['processed_image_url'] as String;
  List<String> get warnings => List<String>.from(data['warnings'] as List);
  List<Onion> get onions => (data['individual_onions'] as List)
      .map((item) => Onion(Map<String, dynamic>.from(item as Map))).toList();
}
