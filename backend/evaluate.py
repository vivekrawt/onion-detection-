"""Phase 9: evaluate independent single-onion crops; never trains a model."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageOps
from .app.config import settings

FOLDERS = {"healthy": "grade_a", "damaged": "damaged", "rotten": "rotten", "sprouted": "sprouted"}


def metrics(truth, predictions):
    labels = [*FOLDERS.values(), "uncertain"]
    matrix = [[0 for _ in labels] for _ in labels]
    for actual, predicted in zip(truth, predictions):
        matrix[labels.index(actual)][labels.index(predicted)] += 1
    per_class = {}
    for i, label in enumerate(labels[:-1]):
        tp, support = matrix[i][i], sum(matrix[i])
        predicted_count = sum(row[i] for row in matrix)
        precision = tp / predicted_count if predicted_count else 0.0
        recall = tp / support if support else 0.0
        per_class[label] = {"precision": precision, "recall": recall,
                            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
                            "support": support}
    return {"samples": len(truth), "accuracy": sum(a == b for a, b in zip(truth, predictions)) / len(truth) if truth else 0.0,
            "labels": labels, "confusion_matrix": matrix, "matrix_orientation": "rows=true, columns=predicted",
            "per_class": per_class, "macro_f1": sum(p["f1"] for p in per_class.values()) / 4,
            "uncertain_count": predictions.count("uncertain")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, nargs="?", default=Path("test_images"))
    parser.add_argument("--output", type=Path, default=Path("backend/output/evaluation.json"))
    args = parser.parse_args()
    files = [(path, label) for folder, label in FOLDERS.items()
             for path in sorted((args.directory / folder).rglob("*"))
             if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
    if not files:
        parser.exit(1, "No images found. Add single-onion crops under healthy/damaged/rotten/sprouted.\n")
    from .app.models.clip_classifier import ClipClassifier
    classifier = ClipClassifier(settings)
    truth, raw, thresholded, details, skipped = [], [], [], [], []
    for path, label in files:
        try:
            with Image.open(path) as image:
                prediction = classifier.classify([ImageOps.exif_transpose(image).convert("RGB")])[0]
        except (OSError, ValueError) as error:
            skipped.append({"file": str(path), "error": str(error)})
            continue
        truth.append(label)
        raw.append(prediction["predicted_class"])
        # Research metric: optional abstention is evaluated separately from the
        # five-category product, which always uses the best-matching condition.
        thresholded.append("uncertain" if prediction["needs_review"] else prediction["condition"])
        details.append({"file": str(path), "true_label": label, **prediction})
    if not truth:
        parser.exit(1, "No readable images; evaluation cannot be computed.\n")
    result = {"model": settings.CLIP_MODEL_NAME, "threshold": settings.CLIP_CONFIDENCE_THRESHOLD,
              "prompts": settings.CLASS_PROMPTS, "raw": metrics(truth, raw), "thresholded": metrics(truth, thresholded),
              "images": details, "skipped": skipped,
              "note": "Accuracy measures condition classification on supplied crops, not segmentation, physical sizing, or official grading."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"raw": result["raw"], "thresholded": result["thresholded"], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
