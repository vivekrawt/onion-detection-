"""All experimental grading rules live here; none are official standards."""
import os
from dataclasses import dataclass, field
from pathlib import Path

# Visible criteria only: photographs cannot measure odor or internal firmness.
CLASS_DESCRIPTIONS = {
    "grade_a": "Healthy whole bulb with intact flesh. Natural red/purple/white color, dry roots, a dry neck, pale patches and loose papery flakes are normal.",
    "damaged": "Physical injury: knife-cut halves, slices, exposed cut faces, deep cracks, dents, bruises or missing flesh. Fresh-looking cut flesh is still damaged. Dry loose outer flakes alone are normal.",
    "rotten": "Visible spoilage: brown/black decaying flesh, mold, wet/slimy-looking tissue or collapsed decomposing areas.",
    "sprouted": "A fresh green or pale white/green growing shoot emerging from the bulb neck; ordinary dry roots and dry stalks are not sprouts.",
    "undersized": "Measured bulb diameter below the configured minimum; determined using the scale marker, never CLIP.",
}
# Short, balanced descriptions tested against the supplied healthy and defect
# references. Long healthy-skin descriptions overwhelmed the decay prompts.
CLASS_PROMPTS = {
    "grade_a": [
        "a photo of a healthy onion",
        "a photo of a fresh onion",
        "a photo of a normal red onion with dry papery skin",
        "a photo of a healthy white onion",
        "a photo of a whole onion with intact flesh and natural flaky outer skin",
    ],
    "damaged": [
        "a photo of a damaged onion",
        "a photo of a cut onion",
        "a photo of an onion with a deep cut exposing flesh",
        "a photo of an onion with open cracks in the bulb",
        "a photo of a bruised and dented onion",
    ],
    "rotten": [
        "a photo of a rotten onion",
        "a photo of a moldy onion",
        "a photo of a decomposing onion",
        "a photo of an onion with black rot",
        "a photo of an onion with slimy brown decaying flesh",
    ],
    "sprouted": [
        "a photo of a sprouted onion",
        "a photo of an onion with a green sprout",
        "a photo of an onion with green shoots growing from the top",
        "a photo of a germinating onion",
        "a photo of an onion with white and green shoots",
    ],
}
LABELS = {"grade_a": "Grade A", "damaged": "Damaged", "rotten": "Rotten", "sprouted": "Sprouted", "undersized": "Undersized"}

@dataclass(frozen=True)
class Settings:
    CLIP_MODEL_NAME: str = "openai/clip-vit-base-patch32"
    MODEL_CACHE_DIR: Path = Path(__file__).resolve().parents[2] / ".cache/huggingface/hub"
    CLASS_PROMPTS: dict = field(default_factory=lambda: CLASS_PROMPTS)
    # Below this relative-score threshold, request review without changing the label.
    CLIP_CONFIDENCE_THRESHOLD: float = 0.55
    MINIMUM_ONION_DIAMETER_CM: float = 4.0
    REFERENCE_MARKER_SIZE_CM: float = 5.0
    REFERENCE_MARKER_ID: int = 0  # DICT_4X4_50; measure the black square, not its margin.
    # Replace with the official URS definition for the intended grading scheme.
    URS_CLASSES: tuple = ("damaged", "rotten", "sprouted", "undersized")
    SIZE_OVERRIDES_CONDITION: bool = True
    MAX_IMAGE_SIDE: int = 1600
    MAX_IMAGE_PIXELS: int = 25_000_000
    MAX_UPLOAD_BYTES: int = 12 * 1024 * 1024
    MIN_COMPONENT_AREA: int = 200
    MAX_ONIONS: int = 150
    BACKGROUND_DISTANCE: float = 28.0
    BRIGHTNESS_GAIN: float = 1.0
    BATCH_SIZE: int = 16
    DETECTION_SIZES: tuple = (640, 1280)
    DETECTION_CONFIDENCE: float = .25
    # A little surrounding context preserves growing shoots; nearby bulbs are
    # masked from that context before CLIP sees the target.
    CROP_CONTEXT_FRACTION: float = .18
    EVIDENCE_MIN_SIMILARITY: float = .29
    EVIDENCE_MARGIN: float = .004
    BACKGROUND_MARGIN: float = .01
    OUTPUT_DIR: Path = field(default_factory=lambda: Path(os.getenv("ONION_OUTPUT_DIR", "backend/output")))
    DEBUG: bool = os.getenv("ONION_DEBUG", "0") == "1"
    LOCAL_FILES_ONLY: bool = os.getenv("ONION_OFFLINE", "0") == "1"

    def __post_init__(self):
        if not 0 <= self.CLIP_CONFIDENCE_THRESHOLD <= 1:
            raise ValueError("Confidence threshold must be between 0 and 1")
        if self.MINIMUM_ONION_DIAMETER_CM <= 0 or self.REFERENCE_MARKER_SIZE_CM <= 0:
            raise ValueError("Physical dimensions must be positive")
        if set(self.URS_CLASSES) - set(LABELS) or len(set(self.URS_CLASSES)) != len(self.URS_CLASSES):
            raise ValueError("URS_CLASSES must contain distinct supported categories")

settings = Settings()
