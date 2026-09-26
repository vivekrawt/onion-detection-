"""Phase 1: python -m backend.classify_onion photo.jpg [--scores]."""
import argparse
import json
from PIL import Image, ImageOps
from .app.config import LABELS, settings


def main():
    parser = argparse.ArgumentParser(description="Classify one tightly cropped onion using pretrained CLIP")
    parser.add_argument("image")
    parser.add_argument("--scores", action="store_true", help="Phase 2: print scores, best condition and review flag")
    args = parser.parse_args()
    try:
        from .app.models.clip_classifier import ClipClassifier
        with Image.open(args.image) as image:
            result = ClipClassifier(settings).classify([ImageOps.exif_transpose(image).convert("RGB")])[0]
        print(json.dumps(result, indent=2) if args.scores else LABELS[result["predicted_class"]])
    except (OSError, ValueError) as error:
        parser.exit(1, f"Unable to classify image: {error}\nCheck the image path and model download/cache.\n")


if __name__ == "__main__":
    main()
