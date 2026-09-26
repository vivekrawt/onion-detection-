"""Generate ArUco artwork. Print black square at the configured physical width."""
import argparse
from pathlib import Path
import cv2
from .app.config import settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("backend/output/marker.png"))
    args = parser.parse_args()
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(dictionary, settings.REFERENCE_MARKER_ID, 600)
    marker = cv2.copyMakeBorder(marker, 100, 100, 100, 100, cv2.BORDER_CONSTANT, value=255)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.output), marker):
        raise OSError("Could not save marker")
    print(f"Saved {args.output}. Print BLACK SQUARE at {settings.REFERENCE_MARKER_SIZE_CM} cm; verify using a ruler.")
    print(f"The complete 800px image including white border should be {settings.REFERENCE_MARKER_SIZE_CM * 800 / 600:.3f} cm wide.")


if __name__ == "__main__":
    main()
