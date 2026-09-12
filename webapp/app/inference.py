"""Model registry and inference. Images stay in memory; nothing is written to disk."""
import base64
import io
import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
(APP_ROOT / '.cache' / 'ultralytics').mkdir(parents=True, exist_ok=True)
os.environ.setdefault('YOLO_CONFIG_DIR', str(APP_ROOT / '.cache' / 'ultralytics'))
os.environ.setdefault('YOLO_AUTOINSTALL', 'false')
os.environ.setdefault('YOLO_OFFLINE', 'true')

from PIL import Image, ImageOps  # noqa: E402

# Weights come from the project's shared models folder; ALLIUM_MODELS_DIR overrides it.
MODELS_DIR = Path(os.environ.get('ALLIUM_MODELS_DIR') or APP_ROOT.parent / 'models')
# Inference keeps every box above this floor; the browser filters by the user's threshold.
CONFIDENCE_FLOOR = 0.10
IOU = 0.5
# Work image size: model inputs are 512-640 px, so larger photos only cost time and memory.
WORK_MAX_SIDE = 2048
HEALTH_LABELS = ('healthy', 'unhealthy')


@dataclass(frozen=True)
class ModelSpec:
    id: str
    name: str
    file: str
    description: str
    mode: str  # 'health' labels each onion; 'onion' only locates onions
    imgsz: int
    default_confidence: float


MODELS = (
    ModelSpec('onion-health', 'Onion Health', 'trained/best.pt',
              'Your trained detector. Labels every onion healthy or unhealthy.', 'health', 512, 0.30),
    ModelSpec('fruit-veg-yolo11m', 'Fruit & Veg YOLO11m', 'pretrained/piyu12-fruit-veg-yolo11m.pt',
              'Public 35-class produce detector, filtered to onions. Locates onions only.', 'onion', 640, 0.25),
    ModelSpec('onion-world', 'YOLO-World · onion', 'pretrained/onion-world.pt',
              'Open-vocabulary detector prompted with "onion". Locates onions only.', 'onion', 640, 0.20),
)
DEFAULT_MODEL = MODELS[0].id


class ModelError(Exception):
    """Requested model is unknown, missing, or has incompatible classes."""


def class_map(spec, names):
    """Map model class ids to app labels for the spec's mode."""
    names = {int(i): str(n).strip().lower() for i, n in names.items()}
    if spec.mode == 'health':
        keep = {i: n for i, n in names.items() if n in HEALTH_LABELS}
        if sorted(keep.values()) != list(HEALTH_LABELS):
            raise ModelError(f'{spec.file} needs healthy and unhealthy classes, found {sorted(names.values())}')
    else:
        keep = {i: 'onion' for i, n in names.items() if n in {'onion', 'onions'}}
        if not keep:
            raise ModelError(f'{spec.file} has no onion class')
    return keep


def prepare_image(image):
    """Apply EXIF orientation, convert to RGB, and cap the working size."""
    image = ImageOps.exif_transpose(image).convert('RGB')
    original_size = image.size
    if max(image.size) > WORK_MAX_SIDE:
        image.thumbnail((WORK_MAX_SIDE, WORK_MAX_SIDE), Image.LANCZOS)
    return image, original_size


def jpeg_data_url(image, quality=88):
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=quality)
    return 'data:image/jpeg;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


class Engine:
    def __init__(self, specs=MODELS, models_dir=MODELS_DIR):
        self.specs = {s.id: s for s in specs}
        self.models_dir = Path(models_dir)
        self._loaded = {}
        # Ultralytics predictors are not safe to share across threads.
        self._lock = threading.Lock()

    def catalog(self):
        return [{**asdict(s), 'available': (self.models_dir / s.file).is_file(), 'loaded': s.id in self._loaded,
                 'labels': list(HEALTH_LABELS) if s.mode == 'health' else ['onion']} for s in self.specs.values()]

    def _model(self, model_id):
        """Load on first use. Caller holds the lock."""
        spec = self.specs.get(model_id)
        if spec is None:
            raise ModelError(f'Unknown model: {model_id}')
        if model_id not in self._loaded:
            path = self.models_dir / spec.file
            if not path.is_file():
                raise ModelError(f'Model file not found: models/{spec.file}')
            from ultralytics import YOLO
            model = YOLO(str(path))
            self._loaded[model_id] = (model, class_map(spec, model.names))
        return spec, *self._loaded[model_id]

    def warm_up(self, model_id=DEFAULT_MODEL):
        """Load a model and run one blank prediction so the first real request is fast."""
        with self._lock:
            spec, model, keep = self._model(model_id)
            model.predict(Image.new('RGB', (spec.imgsz, spec.imgsz)), imgsz=spec.imgsz, classes=list(keep),
                          device='cpu', verbose=False)

    def analyze(self, image, model_id=DEFAULT_MODEL):
        started = time.perf_counter()
        work, original_size = prepare_image(image)
        with self._lock:
            spec, model, keep = self._model(model_id)
            infer_started = time.perf_counter()
            result = model.predict(work, conf=CONFIDENCE_FLOOR, iou=IOU, imgsz=spec.imgsz, classes=list(keep),
                                   agnostic_nms=True, device='cpu', verbose=False)[0]
            inference_ms = (time.perf_counter() - infer_started) * 1000
        detections = []
        for box, score, cls in zip(result.boxes.xyxyn.tolist(), result.boxes.conf.tolist(), result.boxes.cls.tolist()):
            x1, y1, x2, y2 = (min(1.0, max(0.0, v)) for v in box)
            if x2 > x1 and y2 > y1:
                detections.append({'label': keep[int(cls)], 'confidence': round(score, 4),
                                   'box': [round(v, 5) for v in (x1, y1, x2, y2)]})
        # Highest confidence first, so raising the threshold only trims the tail of the numbering.
        detections.sort(key=lambda d: -d['confidence'])
        for number, detection in enumerate(detections, 1):
            detection['id'] = number
        return {
            'model': {'id': spec.id, 'name': spec.name, 'mode': spec.mode, 'default_confidence': spec.default_confidence},
            'image': {'width': work.width, 'height': work.height, 'original_width': original_size[0],
                      'original_height': original_size[1], 'data_url': jpeg_data_url(work)},
            'confidence_floor': CONFIDENCE_FLOOR,
            'detections': detections,
            'timing_ms': {'inference': round(inference_ms, 1), 'total': round((time.perf_counter() - started) * 1000, 1)},
        }
