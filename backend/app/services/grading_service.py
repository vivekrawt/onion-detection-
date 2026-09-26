"""Geometry, model inference, and grading rules remain separate concerns."""
from datetime import datetime, timezone
import cv2
from PIL import Image
from ..config import LABELS, CLASS_DESCRIPTIONS
from ..vision.preprocessing import preprocess
from ..vision.onion_segmentation import segment
from ..vision.size_estimation import find_reference, diameter_pixels
from ..vision.crops import onion_crop

COLORS = {"grade_a": (20, 130, 70), "damaged": (220, 120, 20), "rotten": (190, 40, 45), "sprouted": (90, 70, 185), "undersized": (0, 110, 180)}


def final_class(condition, diameter, config):
    small = diameter is not None and diameter < config.MINIMUM_ONION_DIAMETER_CM
    if small and (config.SIZE_OVERRIDES_CONDITION or condition == "grade_a"):
        return "undersized"
    # Grade A means healthy appearance. Missing scale never changes condition;
    # it only prevents the independent undersized check.
    return condition


def statistics(onions, config):
    total = len(onions)
    result = {"total_onions": total}
    # Every detection remains in the denominator, including low-score predictions.
    for category in LABELS:
        count = sum(o["final_class"] == category for o in onions)
        result[category] = {"count": count, "percentage": round(100 * count / total, 2) if total else 0.0}
    urs_count = sum(result[key]["count"] for key in config.URS_CLASSES)
    result.update(urs_count=urs_count, urs_percentage=round(100 * urs_count / total, 2) if total else 0.0)
    result["needs_review_count"] = sum(bool(o.get("needs_review")) for o in onions)
    return result


class GradingService:
    def __init__(self, classifier, config, candidate_provider=None):
        self.classifier, self.config = classifier, config
        self.candidate_provider = candidate_provider

    def analyze(self, image, report_id, directory):
        rgb, lab, hsv = preprocess(image, self.config)
        scale, markers, warning = find_reference(rgb, self.config)
        candidates, mask = segment(lab, hsv, markers, self.config)
        if self.candidate_provider is not None:
            candidates = self.candidate_provider(rgb, mask, markers)
        if len(candidates) > self.config.MAX_ONIONS:
            raise ValueError(f"Too many objects; use a smaller lot (maximum {self.config.MAX_ONIONS}).")
        crops = []
        for index in range(len(candidates)):
            crops.append(onion_crop(rgb, candidates, index, self.config.CROP_CONTEXT_FRACTION))
        predictions = self.classifier.classify(crops) if crops else []
        if len(predictions) != len(candidates):
            raise RuntimeError("Classifier did not return one result per candidate")
        rejected = sum(bool(p.get('exclude_from_count')) for p in predictions)
        accepted = [(c,p,im) for c,p,im in zip(candidates,predictions,crops) if not p.get('exclude_from_count')]
        overlay = rgb.copy()
        onions = []
        for index, (candidate, prediction, crop) in enumerate(accepted, 1):
            diameter_px = diameter_pixels(candidate["contour"])
            diameter = diameter_px / scale if scale and candidate.get("size_valid", True) else None
            category = final_class(prediction["condition"], diameter, self.config)
            reason = "Appearance and configured size rules applied."
            if diameter is None:
                reason = "Best-matching appearance class; physical size has not been verified."
            if prediction.get("needs_review"):
                reason += " Low or conflicting visual evidence; review this prediction."
            reason = prediction.get('decision_reason', '') + ' ' + reason
            onion = {"id": index, "bbox": candidate["bbox"], **prediction,
                     "diameter_pixels": round(diameter_px, 2), "estimated_diameter_cm": round(diameter, 2) if diameter is not None else None,
                     "is_undersized": diameter < self.config.MINIMUM_ONION_DIAMETER_CM if diameter is not None else None,
                     "final_class": category, "classification_reason": reason,
                     "class_description": CLASS_DESCRIPTIONS[category],
                     "detection_confidence": candidate.get("detection_confidence"),
                     "measurement_method": candidate.get("measurement_method", "foreground_contour")}
            if self.config.DEBUG:
                name = f"onion-{index}.jpg"
                crop.save(directory / name)
                onion["crop_url"] = f"/outputs/{report_id}/{name}"
            onions.append(onion)
            x, y, w, h = candidate["bbox"]
            color = COLORS[category]
            cv2.drawContours(overlay, [candidate["contour"]], -1, color, 2)
            cv2.rectangle(overlay, (x, y), (x+w, y+h), color, 2)
            text = f"#{index} {LABELS[category]}"
            tx, ty = min(x, max(0, overlay.shape[1]-200)), max(20, y-6)
            cv2.putText(overlay, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 4, cv2.LINE_AA)
            cv2.putText(overlay, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, .55, color, 1, cv2.LINE_AA)
        Image.fromarray(overlay).save(directory / "analyzed.jpg", quality=92)
        Image.fromarray(rgb).save(directory / "source.jpg", quality=92)
        if self.config.DEBUG:
            Image.fromarray(mask).save(directory / "mask.png")
        warnings = ["Prototype: inspect all detections; overlapping onions and non-onion objects can invalidate counts."]
        if warning:
            warnings.append(warning)
        if not onions:
            warnings.append("No valid foreground objects detected. Use separated onions on a contrasting background.")
        return {"report_id": report_id, "created_at": datetime.now(timezone.utc).isoformat(),
                **statistics(onions, self.config), "individual_onions": onions,
                "processed_image_url": f"/outputs/{report_id}/analyzed.jpg",
                "image_width": rgb.shape[1], "image_height": rgb.shape[0],
                "pixels_per_cm": scale, "warnings": warnings,
                "non_onion_candidates_removed": rejected,
                "rules": {"model": self.config.CLIP_MODEL_NAME,
                          "confidence_threshold": self.config.CLIP_CONFIDENCE_THRESHOLD,
                          "crop_context_fraction": self.config.CROP_CONTEXT_FRACTION,
                          "minimum_diameter_cm": self.config.MINIMUM_ONION_DIAMETER_CM,
                          "marker_size_cm": self.config.REFERENCE_MARKER_SIZE_CM,
                          "marker_id": self.config.REFERENCE_MARKER_ID,
                          "urs_classes": list(self.config.URS_CLASSES),
                          "size_overrides_condition": self.config.SIZE_OVERRIDES_CONDITION,
                          "classification_policy": "multi_view_visible_evidence_v2",
                          "evidence_min_similarity": self.config.EVIDENCE_MIN_SIMILARITY,
                          "evidence_margin": self.config.EVIDENCE_MARGIN,
                          "grade_a_definition": "healthy appearance; size verified only when measured"}}
