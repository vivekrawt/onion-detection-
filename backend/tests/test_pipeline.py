"""Offline functional tests use an explicit stub, never fake production predictions."""
from dataclasses import replace
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
import cv2
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient
from backend.app.config import settings
from backend.app.main import create_app
from backend.app.services.grading_service import final_class, statistics
from backend.app.utils.image_utils import decode_image
from backend.app.vision.size_estimation import find_reference
from backend.evaluate import metrics


class StubClassifier:
    def classify(self, images):
        return [{"predicted_class": "grade_a", "condition": "grade_a", "confidence": .8, "needs_review": False,
                 "scores": {"grade_a": .8, "damaged": .1, "rotten": .05, "sprouted": .05},
                 "similarities": {"grade_a": .3, "damaged": .2, "rotten": .1, "sprouted": .1}} for _ in images]


def fixture(with_marker=True):
    image = np.full((600, 800, 3), 255, dtype=np.uint8)
    cv2.circle(image, (180, 230), 60, (165, 85, 45), -1)
    cv2.circle(image, (420, 230), 30, (165, 85, 45), -1)
    if with_marker:
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        marker = cv2.aruco.generateImageMarker(dictionary, 0, 100)
        image[400:500, 600:700] = cv2.cvtColor(marker, cv2.COLOR_GRAY2RGB)
    return image


def png(image):
    buffer = BytesIO()
    Image.fromarray(image).save(buffer, format="PNG")
    return buffer.getvalue()


class PipelineTests(unittest.TestCase):
    def test_hierarchy_and_no_scale(self):
        self.assertEqual(final_class("rotten", 3, settings), "undersized")
        self.assertEqual(final_class("rotten", 3, replace(settings, SIZE_OVERRIDES_CONDITION=False)), "rotten")
        self.assertEqual(final_class("grade_a", None, settings), "grade_a")
        self.assertEqual(final_class("grade_a", 4, settings), "grade_a")

    def test_percentages_and_configurable_urs(self):
        onions = [{"final_class": key} for key in ("grade_a", "rotten", "grade_a", "undersized")]
        result = statistics(onions, settings)
        self.assertEqual(result["urs_percentage"], 50)
        self.assertEqual(result["grade_a"]["percentage"], 50)
        self.assertNotIn("uncertain", result)
        self.assertEqual(statistics([], settings)["urs_percentage"], 0)
        self.assertEqual(statistics(onions, replace(settings, URS_CLASSES=("rotten",)))["urs_count"], 1)

    def test_marker_scale(self):
        scale, polygons, warning = find_reference(fixture(), settings)
        self.assertAlmostEqual(scale, 20, delta=.3)
        self.assertEqual(len(polygons), 1)
        self.assertIsNone(warning)

    def test_low_confidence_keeps_grade_and_counts_review(self):
        class LowScoreClassifier(StubClassifier):
            def classify(self, images):
                predictions = super().classify(images)
                for prediction in predictions:
                    prediction.update(confidence=.4, needs_review=True,
                                      scores={'grade_a': .4, 'damaged': .3, 'rotten': .2, 'sprouted': .1})
                return predictions
        with tempfile.TemporaryDirectory() as directory:
            with TestClient(create_app(replace(settings, OUTPUT_DIR=Path(directory)), LowScoreClassifier())) as client:
                result = client.post('/analyze', files={'image': ('lot.png', png(fixture(False)))}).json()
                self.assertEqual(result['grade_a']['count'], 2)
                self.assertEqual(result['needs_review_count'], 2)
                self.assertNotIn('uncertain', result)
                self.assertTrue(all(o['needs_review'] and o['final_class'] == 'grade_a' for o in result['individual_onions']))

    def test_decode_rejects_bad_and_large_images(self):
        with self.assertRaises(ValueError):
            decode_image(b"not an image", 1000)
        with self.assertRaises(ValueError):
            decode_image(png(fixture()), 1000)

    def test_evaluation_abstention(self):
        result = metrics(["grade_a", "rotten"], ["grade_a", "uncertain"])
        self.assertEqual(result["accuracy"], .5)
        self.assertEqual(result["per_class"]["rotten"]["recall"], 0)
        self.assertEqual(result["confusion_matrix"][2][4], 1)

    def test_api_pipeline_and_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            config = replace(settings, OUTPUT_DIR=Path(directory), DEBUG=True)
            with TestClient(create_app(config, StubClassifier())) as client:
                self.assertEqual(client.get("/health").status_code, 200)
                response = client.post("/analyze", files={"image": ("lot.png", png(fixture()), "image/png")})
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertEqual(result["total_onions"], 2)  # Marker must not become an onion.
                self.assertEqual(result["grade_a"]["count"], 1)
                self.assertEqual(result["undersized"]["count"], 1)
                self.assertAlmostEqual(result["individual_onions"][0]["estimated_diameter_cm"], 6, delta=.3)
                self.assertEqual(client.get(result["processed_image_url"]).status_code, 200)
                self.assertEqual(client.get(result["individual_onions"][0]["crop_url"]).status_code, 200)
                self.assertEqual(client.get(f"/analyses/{result['report_id']}").json(), result)
                report = client.post("/generate-report", json={"report_id": result["report_id"]})
                self.assertEqual(report.status_code, 200, report.text)
                pdf = client.get(report.json()["pdf_url"])
                self.assertTrue(pdf.content.startswith(b"%PDF"))
                self.assertEqual(client.post("/analyze", files={"image": ("bad.png", b"bad")}).status_code, 422)
                self.assertEqual(client.post("/generate-report", json={"report_id": "../bad"}).status_code, 422)
                unknown = "00000000-0000-0000-0000-000000000000"
                self.assertEqual(client.post("/generate-report", json={"report_id": unknown}).status_code, 404)
                empty = client.post("/analyze", files={"image": ("empty.png", png(np.full((100, 100, 3), 255, dtype=np.uint8)))}).json()
                self.assertEqual(empty["total_onions"], 0)
                self.assertEqual(empty["urs_percentage"], 0)
                no_scale = client.post("/analyze", files={"image": ("lot.png", png(fixture(False)))}).json()
                self.assertEqual(no_scale["grade_a"]["count"], 2)
                self.assertNotIn("uncertain", no_scale)
                self.assertIsNone(no_scale["individual_onions"][0]["estimated_diameter_cm"])

    def test_upload_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            with TestClient(create_app(replace(settings, OUTPUT_DIR=Path(directory), MAX_UPLOAD_BYTES=4), StubClassifier())) as client:
                self.assertEqual(client.post("/analyze", files={"image": ("bad.png", b"12345")}).status_code, 413)


if __name__ == "__main__":
    unittest.main()
