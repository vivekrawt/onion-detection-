# AI-Based Onion Quality Detection and Grading Using Pretrained CLIP

## Phase 1: one onion, one appearance label

Use **Python 3.11 or 3.12**. Run commands from the repository root. A separate
environment avoids changing the older trained-model web application's dependencies.

```powershell
py -3.12 -m venv .venv-clip
.\.venv-clip\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv-clip\Scripts\python.exe -m backend.classify_onion path\to\onion.jpg
```

Example input: a tightly cropped photo of one onion. Example output (illustrative,
not a measured result): `Grade A`. Other labels: `Damaged`, `Rotten`, `Sprouted`.

The first run downloads `openai/clip-vit-base-patch32` from Hugging Face. Later
runs reuse the cache. CUDA is used when available; otherwise inference uses CPU.
Install the appropriate CUDA-enabled PyTorch build if GPU support is needed.

### Files and how it works

- `app/config.py`: prompts and experimental thresholds.
- `app/models/clip_classifier.py`: loads CLIP and its processor once per process;
  encodes several descriptions per condition, normalizes each, averages them,
  and normalizes each class mean. It compares normalized image embeddings to
  those means using cosine similarity. No training takes place.
- `classify_onion.py`: reads an image, corrects EXIF orientation, runs inference,
  and prints the strongest matching appearance label.
- `requirements.txt`: backend dependencies. Do not install multiple OpenCV wheels
  in the same environment because they all provide the `cv2` namespace.

CLIP compares image and text representations learned from general image/text
pairs. It has not been validated as an onion grader. Hidden/internal defects,
similar-looking damage and dry skin, and domain shift can cause errors.

## Phase 2: inspect confidence

Add `--scores` to print cosine similarities, relative softmax scores, raw predicted
class, condition and `needs_review` flag. Relative scores sum to one, but **are not
calibrated statistical probabilities**. The `0.55` default is an experimental
relative-score review threshold, not validated accuracy. A lower score keeps the
best-matching class and sets `needs_review=true`; it does not create a sixth grade.
Grade A means healthy appearance. Physical size is checked independently when a
reference marker is available. Missing scale leaves diameter unknown, not the grade.

### Common errors

- `No module named ...`: use the same Python executable for installation and running.
- Download/network failure: download once online; set `ONION_OFFLINE=1` only after
  caching the model. A proxy may require local network configuration.
- CUDA memory error: lower `BATCH_SIZE` or set `CUDA_VISIBLE_DEVICES=-1` before launch.
- Wrong labels: crop one onion, use uniform light, inspect scores, and evaluate
  real labeled images before adjusting prompts. Never equate score with accuracy.
- Unsupported phone photo: export JPEG/PNG; HEIC is not supported by this prototype.

References: [CLIP documentation](https://huggingface.co/docs/transformers/v4.57.1/en/model_doc/clip),
[model card](https://huggingface.co/openai/clip-vit-base-patch32).

## Phases 3-6: multi-onion grading and FastAPI

```powershell
.\.venv-clip\Scripts\python.exe -m backend.make_marker
$env:ONION_DEBUG = '1'
.\.venv-clip\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001/docs to upload a photo using **POST /analyze**. The
older web application uses port 8000; the CLIP backend uses 8001. No custom dataset
or trained detector is required. Model files are cached under `.cache/huggingface/hub`.
Use one worker so the model loads only once. Startup fails visibly if weights
cannot be loaded; production inference never substitutes invented predictions.

1. Print `backend/output/marker.png`; use a ruler to ensure the **black square**
   is exactly `REFERENCE_MARKER_SIZE_CM` wide (default 5 cm). The white margin is
   excluded from this measurement. The configured marker ID is 0 in `DICT_4X4_50`.
2. Place the marker next to separated onions on a uniform, contrasting background.
   Avoid shadows, clipping, overlap, clutter, and objects along the photo edges.
3. Photograph from directly above. The marker must lie approximately in the same
   measurement plane as the bulb silhouettes. Bulb height, perspective, lens
   distortion, and camera tilt introduce error; this is not precision metrology.
4. Upload JPEG, PNG or WebP (up to 12 MB / 25 megapixels). Images are resized to
   1600 pixels on the longest edge. Bounding boxes `[x,y,width,height]` and pixel
   measurements refer to this resized, orientation-corrected image.

`preprocessing.py` resizes, optionally adjusts brightness, denoises and converts
to LAB/HSV. `onion_segmentation.py` estimates background from the border, thresholds
color differences and saturation, applies opening/closing, and extracts connected
components/contours. It excludes detected marker polygons, small noise, partial
border objects, and extreme shapes. This detects foreground candidates, not onion
semantics; touching onions can merge and other objects can be false positives.

`size_estimation.py` averages marker edge lengths to estimate pixels/cm. The bulb
diameter is the shorter side of the minimum rotated bounding rectangle. The
marker must be detected once with the expected ID. Missing, duplicate, tiny or
visibly skewed markers produce unknown diameter (`null`), never an invented scale.

`grading_service.py` retains raw CLIP prediction, condition, review flag, scores,
cosine similarities, size and final class separately. By default, undersized takes
priority; set `SIZE_OVERRIDES_CONDITION=False` to retain defective condition
labels and override only healthy appearances with undersized. The undersized flag
and CLIP condition remain in the response either way. Without scale, a healthy
appearance is Grade A with unverified size; it is not a certified physical grade.

All accepted detections, **including low-confidence predictions**, form the percentage denominator.
The five final classes are mutually exclusive. URS sums the configured final classes,
so an onion is not double-counted. Empty images return zero percentages plus a warning;
rounding can make displayed percentages differ slightly from 100%. URS rules and
the 4 cm minimum are examples, not official grading standards.

### API contract

```powershell
curl.exe -F "image=@path\to\lot.jpg" http://127.0.0.1:8001/analyze
curl.exe http://127.0.0.1:8001/health
```

The analysis JSON includes `report_id`, `created_at` (UTC), `total_onions`,
`grade_a`, `damaged`, `rotten`, `sprouted`, `undersized` (each with
count/percentage), `needs_review_count`, `urs_count`, `urs_percentage`, `individual_onions`,
`processed_image_url`, scale, warnings and a snapshot of applied grading rules.
URLs are relative to the backend origin; the mobile client resolves them.

- `GET /analyses/{report_id}` retrieves a persisted result.
- `POST /generate-report` accepts `{"report_id":"<UUID from analysis>"}` and returns
  `pdf_url`. It loads authoritative saved data, rather than trusting client counts.
- `GET /outputs/{report_id}/{filename}` downloads allowed image/report artifacts.
- Invalid images: 422; oversized files: 413; unknown reports: 404; analyzer busy: 503.

The filesystem `ResultStore` is an intentionally small persistence interface that
can be replaced by SQLite or Firebase. Results survive restarts. Output has no
automatic expiration; manually remove obsolete lot directories when no requests
use them. This local prototype has no accounts or access control. Do not expose
it publicly without adding authentication, request limits and storage retention.

## Phase 7: mobile app

See [../mobile/README.md](../mobile/README.md). The Flutter client implements
capture/upload, preview, processing/retry, results, per-onion inspection and report
download/share. The native platform runners are generated with `mobile/bootstrap.py`.

## Phase 8: PDF reports and developer mode

The mobile report screen or `/generate-report` creates a PDF with report ID,
date/time, counts, percentages, analyzed image, rules, warnings and the prototype
disclaimer. Text labels accompany colored outlines for accessibility.

Set `ONION_DEBUG=1` before starting the server to save crops and `mask.png` beside
the result. Individual details display crops, class scores, cosine similarities,
estimated diameter and final class. The same diagnostics are stored in `result.json`.
Crop endpoints are disabled when debug mode is off.

## Phase 9: manual evaluation

```powershell
.\.venv-clip\Scripts\python.exe -m backend.evaluate test_images
.\.venv-clip\Scripts\python.exe -m unittest discover -s backend/tests -v
```

See [../test_images/README.md](../test_images/README.md) for labeling methodology.
The evaluator records raw and thresholded accuracy, confusion matrix, precision,
recall and F1. Use untouched evaluation images after tuning prompts/thresholds.
No scientific accuracy claim is possible without that dataset. The automated
tests use a clearly named classifier stub for deterministic logic checks; a real
CLIP smoke test checks integration, not accuracy.

### Additional troubleshooting

- `cv2.aruco` missing: install `opencv-contrib-python-headless` in a clean environment;
  remove competing OpenCV packages from that environment first.
- Zero/merged detections: clear the image border, separate bulbs, improve contrast,
  and inspect the debug mask. Adjust `BACKGROUND_DISTANCE` / `MIN_COMPONENT_AREA`.
- Size unknown: print the exact configured ArUco marker; keep its full white border
  visible and take the photo directly from above.
- Phone cannot connect: use the host LAN IP or Android emulator `10.0.2.2`, bind
  to `0.0.0.0` for LAN use, and check the private-network firewall.
- PDF button fails: check that the same backend still has the report's saved output.

## Complete new project structure

```text
backend/
  __init__.py
  README.md
  requirements.txt
  classify_onion.py             phases 1-2 CLI
  make_marker.py                reference artwork
  evaluate.py                   manual labeled-crop evaluation
  app/
    __init__.py
    main.py                     FastAPI startup and endpoints
    config.py                   model, prompts, thresholds and rules
    models/clip_classifier.py   cached text ensemble + image inference
    vision/preprocessing.py     color conversion, resize and denoise
    vision/onion_segmentation.py
    vision/size_estimation.py   marker scale and contour geometry
    services/grading_service.py
    services/result_store.py    persisted JSON repository
    services/report_service.py PDF layout
    utils/image_utils.py        safe image decoding and orientation
  tests/test_pipeline.py        offline geometry/API/rule tests
mobile/
  pubspec.yaml
  analysis_options.yaml
  bootstrap.py                  creates Android/iOS platform runners
  README.md
  lib/main.dart
  lib/models/analysis_result.dart
  lib/services/api_service.dart
  lib/screens/home_screen.dart
  lib/screens/image_preview_screen.dart
  lib/screens/processing_screen.dart
  lib/screens/result_screen.dart
  lib/screens/onion_detail_screen.dart
  lib/screens/report_screen.dart
  test/widget_test.dart
test_images/
  README.md
  healthy/ damaged/ rotten/ sprouted/
```

Each Python subpackage also contains `__init__.py`. Generated environment, weights,
results and locally collected test images are ignored by Git.
