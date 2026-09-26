"""Connect the existing Allium detector to CLIP grading and automatic PDF reports."""
from dataclasses import replace
from pathlib import Path
from threading import Lock
from time import perf_counter
from uuid import uuid4
import cv2
import numpy as np
from PIL import Image
from backend.app.config import settings, LABELS
from backend.app.services.grading_service import GradingService
from backend.app.services.result_store import ResultStore
from backend.app.services.report_service import generate_report
from .inference import DEFAULT_MODEL, ModelError, prepare_image

QUALITY_ID = 'clip-quality'


class QualityEngine:
    def __init__(self, detector):
        self.detector = detector
        self.config = replace(settings, DEBUG=True, OUTPUT_DIR=Path(__file__).resolve().parents[2] / 'backend/output')
        self.store = ResultStore(self.config.OUTPUT_DIR)
        self.classifier = None
        self.error = None
        self.lock = Lock()

    def warm_up(self):
        try:
            from backend.app.models.clip_classifier import ClipClassifier
            self.classifier = ClipClassifier(self.config)
        except Exception as error:
            self.error = str(error)
            raise ModelError(f'CLIP could not start: {error}') from error

    def catalog(self):
        return {'id': QUALITY_ID, 'name': 'Full quality report', 'mode': 'quality',
                'description': 'Grade A, defects, size and a PDF report in one analysis.',
                'available': self.classifier is not None, 'loaded': self.classifier is not None,
                'file': 'CLIP model cache', 'default_confidence': self.config.CLIP_CONFIDENCE_THRESHOLD,
                'labels': list(LABELS)}

    def candidates(self, rgb, mask, markers):
        """Use existing AI to locate bulbs; OpenCV refines their size silhouettes."""
        if hasattr(self.detector, 'detect_quality'):
            result = self.detector.detect_quality(Image.fromarray(rgb), self.config.DETECTION_SIZES,
                                                  self.config.DETECTION_CONFIDENCE)
        else:
            result = self.detector.analyze(Image.fromarray(rgb), DEFAULT_MODEL)
        self.detection_diagnostics = result.get('diagnostics', {})
        height, width = rgb.shape[:2]
        candidates = []
        for detection in result['detections']:
            if detection['confidence'] < result['model']['default_confidence']:
                continue
            a, b, c, d = detection['box']
            x, y = max(0, int(a * width)), max(0, int(b * height))
            x2, y2 = min(width, int(c * width)), min(height, int(d * height))
            w, h = x2 - x, y2 - y
            if min(w, h) < 3:
                continue
            if any(cv2.pointPolygonTest(p, (float(x + w/2), float(y + h/2)), False) >= 0 for p in markers):
                continue
            contours, _ = cv2.findContours(mask[y:y2, x:x2], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contour = max(contours, key=cv2.contourArea) if contours else None
            valid = contour is not None and cv2.contourArea(contour) >= .2 * w * h
            # If foreground cannot be separated, show the detection but withhold size.
            if valid:
                contour = contour + np.array([[[x, y]]], dtype=np.int32)
            else:
                contour = np.array([[[x, y]], [[x2, y]], [[x2, y2]], [[x, y2]]], dtype=np.int32)
            candidates.append({'bbox': [x, y, w, h], 'contour': contour,
                               'detection_confidence': detection['confidence'],
                               'detection_support': detection.get('support', []),
                               'size_valid': valid and x > 0 and y > 0 and x2 < width and y2 < height,
                               'measurement_method': 'detector_guided_contour' if valid else 'unavailable'})
        return candidates

    def analyze(self, image):
        if self.classifier is None:
            raise ModelError('Full grading is unavailable. Restart with the CLIP environment and cached weights.')
        if not self.lock.acquire(blocking=False):
            raise ModelError('Another lot is being analyzed. Please retry in a moment.')
        try:
            started = perf_counter()
            report_id = str(uuid4())
            directory = self.store.directory(report_id)
            directory.mkdir()
            work, original = prepare_image(image)
            detector_ready = any(m['id'] == DEFAULT_MODEL and m['available'] for m in self.detector.catalog())
            provider = self.candidates if detector_ready else None
            result = GradingService(self.classifier, self.config, provider).analyze(work, report_id, directory)
            result['rules']['detection_source'] = DEFAULT_MODEL if detector_ready else 'opencv_foreground'
            result['detection_diagnostics'] = getattr(self, 'detection_diagnostics', {})
            result['detection_diagnostics']['visible_count'] = result['total_onions']
            result['detection_diagnostics']['non_onion_candidates_removed'] = result['non_onion_candidates_removed']
            result['rules']['detection_sizes'] = list(self.config.DETECTION_SIZES)
            result['rules']['detection_confidence'] = self.config.DETECTION_CONFIDENCE
            if detector_ready:
                result['warnings'].append('Count includes visible bulbs or cut pieces, not reconstructed whole onions. Hidden bulbs cannot be counted reliably.')
                result['warnings'].append('Size uses detector-guided foreground contours; touching bulbs and camera tilt can affect measurements.')
            else:
                result['warnings'].append('Existing detector unavailable; using foreground segmentation on a clean background.')
            for onion in result['individual_onions']:
                onion['crop_url'] = f"/api/quality-assets/{report_id}/onion-{onion['id']}.jpg"
            result['processed_image_url'] = f'/api/quality-assets/{report_id}/analyzed.jpg'
            result['pdf_url'] = f'/api/reports/{report_id}'
            generate_report(result, directory / 'analyzed.jpg', directory / 'report.pdf')
            self.store.save(result)
            width, height = result['image_width'], result['image_height']
            detections = []
            for onion in result['individual_onions']:
                x, y, w, h = onion['bbox']
                detections.append({'id': onion['id'], 'label': onion['final_class'], 'confidence': onion['confidence'],
                                   'box': [x/width, y/height, (x+w)/width, (y+h)/height]})
            elapsed = round((perf_counter() - started) * 1000, 1)
            return {'model': {'id': QUALITY_ID, 'name': 'Full quality report', 'mode': 'quality',
                              'default_confidence': self.config.CLIP_CONFIDENCE_THRESHOLD},
                    'image': {'width': width, 'height': height, 'original_width': original[0], 'original_height': original[1],
                              'data_url': f'/api/quality-assets/{report_id}/source.jpg'},
                    'detections': detections, 'quality': result,
                    'timing_ms': {'inference': elapsed, 'total': elapsed}}
        finally:
            self.lock.release()
