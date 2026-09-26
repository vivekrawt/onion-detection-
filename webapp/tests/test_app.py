import io
import sys
import unittest
import tempfile
from dataclasses import replace
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402
from app.inference import MODELS, ModelError, ModelSpec, class_map, prepare_image  # noqa: E402
from app.quality import QualityEngine  # noqa: E402
from backend.app.services.result_store import ResultStore  # noqa: E402
from backend.tests.test_pipeline import fixture, StubClassifier  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / 'static' / 'samples'


def encode(image, fmt='PNG', **params):
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **params)
    return buffer.getvalue()


class ClassMapTests(unittest.TestCase):
    def test_health_mode_requires_both_classes(self):
        spec = ModelSpec('h', 'H', 'h.pt', '', 'health', 512, 0.3)
        self.assertEqual(class_map(spec, {0: 'Healthy', 1: 'unhealthy'}), {0: 'healthy', 1: 'unhealthy'})
        with self.assertRaises(ModelError):
            class_map(spec, {0: 'healthy', 1: 'onion'})

    def test_onion_mode_keeps_only_onion(self):
        spec = ModelSpec('o', 'O', 'o.pt', '', 'onion', 640, 0.25)
        self.assertEqual(class_map(spec, {21: 'Okra', 22: 'Onion', 23: 'Orange'}), {22: 'onion'})
        with self.assertRaises(ModelError):
            class_map(spec, {0: 'apple'})

    def test_exif_rotation_and_size_cap(self):
        exif = Image.Exif()
        exif[0x0112] = 6  # rotate 90 degrees clockwise on display
        rotated = Image.open(io.BytesIO(encode(Image.new('RGB', (300, 100)), 'JPEG', exif=exif)))
        work, original = prepare_image(rotated)
        self.assertEqual((work.size, original), ((100, 300), (100, 300)))
        work, original = prepare_image(Image.new('L', (4096, 1024)))
        self.assertEqual((work.mode, work.size, original), ('RGB', (2048, 512), (4096, 1024)))


class QualityGeometryTests(unittest.TestCase):
    def test_detector_guided_size_and_missing_foreground(self):
        class Detector:
            def catalog(self):
                return [{'id': 'onion-health', 'available': True}]

            def analyze(self, image, model_id):
                return {'model': {'default_confidence': .3}, 'detections': [
                    {'box': [120/800, 170/600, 241/800, 291/600], 'confidence': .9},
                    {'box': [390/800, 200/600, 451/800, 261/600], 'confidence': .9}]}

        engine = QualityEngine(Detector())
        engine.classifier = StubClassifier()
        with tempfile.TemporaryDirectory() as output:
            engine.config = replace(engine.config, OUTPUT_DIR=Path(output))
            engine.store = ResultStore(output)
            result = engine.analyze(Image.fromarray(fixture()))['quality']
            self.assertEqual(result['grade_a']['count'], 1)
            self.assertEqual(result['undersized']['count'], 1)
            self.assertAlmostEqual(result['individual_onions'][0]['estimated_diameter_cm'], 6, delta=.3)
            self.assertTrue(all(o['measurement_method'] == 'detector_guided_contour' for o in result['individual_onions']))
            empty = fixture()
            empty[100:350, :500] = 255  # Keep reference marker, remove bulb silhouettes.
            result = engine.analyze(Image.fromarray(empty))['quality']
            self.assertEqual(result['grade_a']['count'], 2)
            self.assertTrue(all(o['estimated_diameter_cm'] is None for o in result['individual_onions']))

    def test_busy_analyzer_rejects_duplicate_request(self):
        engine = QualityEngine(None)
        engine.classifier = StubClassifier()
        engine.lock.acquire()
        try:
            with self.assertRaisesRegex(ModelError, 'Another lot'):
                engine.analyze(Image.new('RGB', (20, 20)))
        finally:
            engine.lock.release()


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(main.app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def analyze(self, data, model_id='onion-health', name='onions.jpg'):
        form = {'model_id': model_id} if model_id else {}
        return self.client.post('/api/analyze', files={'file': (name, data, 'image/jpeg')}, data=form)

    def test_index_and_models(self):
        self.assertIn('Allium', self.client.get('/').text)
        body = self.client.get('/api/models').json()
        self.assertEqual(body['default_model'], 'clip-quality')
        self.assertEqual([m['id'] for m in body['models']], ['clip-quality', *[m.id for m in MODELS]])
        self.assertTrue(all(m['available'] for m in body['models']))

    def test_full_quality_default_automatically_generates_pdf_and_crops(self):
        response = self.analyze((SAMPLES / 'healthy-batch.jpg').read_bytes(), model_id=None)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['model']['mode'], 'quality')
        quality = body['quality']
        self.assertGreaterEqual(quality['total_onions'], 10)
        self.assertEqual(len(body['detections']), quality['total_onions'])
        keys = ('grade_a', 'damaged', 'rotten', 'sprouted', 'undersized')
        self.assertEqual(sum(quality[key]['count'] for key in keys), quality['total_onions'])
        self.assertIsNone(quality['pixels_per_cm'])
        self.assertNotIn('uncertain', quality)
        self.assertGreater(quality['grade_a']['count'], 0)
        self.assertTrue(all(o['final_class'] in keys for o in quality['individual_onions']))
        pdf = self.client.get(quality['pdf_url'])
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertIn('inline', pdf.headers['content-disposition'])
        self.assertIn('attachment', self.client.get(quality['pdf_url'] + '?download=true').headers['content-disposition'])
        self.assertEqual(self.client.get(body['image']['data_url']).status_code, 200)
        self.assertEqual(self.client.get(quality['processed_image_url']).status_code, 200)
        self.assertEqual(self.client.get(quality['individual_onions'][0]['crop_url']).status_code, 200)
        self.assertEqual(self.client.get('/api/reports/not-a-uuid').status_code, 422)
        self.assertEqual(self.client.get('/api/reports/00000000-0000-0000-0000-000000000000').status_code, 404)
        self.assertEqual(self.client.get(f"/api/quality-assets/{quality['report_id']}/result.json").status_code, 404)

    def test_health_model_on_healthy_sample(self):
        response = self.analyze((SAMPLES / 'healthy-batch.jpg').read_bytes())
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['model']['mode'], 'health')
        self.assertTrue(body['image']['data_url'].startswith('data:image/jpeg;base64,'))
        self.assertEqual(body['image']['name'], 'onions.jpg')
        detections = body['detections']
        self.assertEqual([d['id'] for d in detections], list(range(1, len(detections) + 1)))
        confident = [d for d in detections if d['confidence'] >= body['model']['default_confidence']]
        self.assertGreaterEqual(len(confident), 10)
        self.assertTrue(all(d['label'] == 'healthy' for d in confident))
        for d in detections:
            x1, y1, x2, y2 = d['box']
            self.assertTrue(0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1)
            self.assertGreaterEqual(d['confidence'], body['confidence_floor'])
        self.assertEqual(detections, sorted(detections, key=lambda d: -d['confidence']))

    def test_health_model_on_unhealthy_sample(self):
        body = self.analyze((SAMPLES / 'unhealthy-batch.jpg').read_bytes()).json()
        confident = [d for d in body['detections'] if d['confidence'] >= body['model']['default_confidence']]
        self.assertTrue(confident)
        self.assertTrue(all(d['label'] == 'unhealthy' for d in confident))

    def test_detect_only_model_labels_onions(self):
        body = self.analyze((SAMPLES / 'healthy-batch.jpg').read_bytes(), 'fruit-veg-yolo11m').json()
        self.assertEqual(body['model']['mode'], 'onion')
        self.assertTrue(body['detections'])
        self.assertEqual({d['label'] for d in body['detections']}, {'onion'})

    def test_blank_image_has_no_detections_and_keeps_orientation(self):
        exif = Image.Exif()
        exif[0x0112] = 6
        body = self.analyze(encode(Image.new('RGB', (320, 200), 'white'), 'JPEG', exif=exif)).json()
        self.assertEqual(body['detections'], [])
        self.assertEqual((body['image']['width'], body['image']['height']), (200, 320))

    def test_rejects_bad_input(self):
        self.assertEqual(self.analyze(b'not an image').status_code, 400)
        self.assertEqual(self.analyze(b'').status_code, 400)
        self.assertEqual(self.analyze(encode(Image.new('RGB', (8, 8))), 'no-such-model').status_code, 404)
        original = main.MAX_UPLOAD_BYTES
        main.MAX_UPLOAD_BYTES = 10
        try:
            self.assertEqual(self.analyze(encode(Image.new('RGB', (8, 8)))).status_code, 413)
        finally:
            main.MAX_UPLOAD_BYTES = original


if __name__ == '__main__':
    unittest.main()
