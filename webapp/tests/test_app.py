import io
import sys
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402
from app.inference import MODELS, ModelError, ModelSpec, class_map, prepare_image  # noqa: E402

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


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(main.app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def analyze(self, data, model_id=None, name='onions.jpg'):
        form = {'model_id': model_id} if model_id else {}
        return self.client.post('/api/analyze', files={'file': (name, data, 'image/jpeg')}, data=form)

    def test_index_and_models(self):
        self.assertIn('Allium', self.client.get('/').text)
        body = self.client.get('/api/models').json()
        self.assertEqual(body['default_model'], MODELS[0].id)
        self.assertEqual([m['id'] for m in body['models']], [m.id for m in MODELS])
        self.assertTrue(all(m['available'] for m in body['models']))

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
