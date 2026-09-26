# Allium: automatic onion quality reports

Choose a photo, then click **Analyze quality**. The default **Full quality report**
mode uses the existing detector to locate bulbs, pretrained CLIP for condition
classification, and OpenCV/ArUco for approximate size. It automatically displays
the labeled photo, five-category breakdown, Grade A/URS percentages, individual
crops and scores, and a ready PDF. No API forms, report IDs or URL copying are needed.

Images and reports from full grading are saved locally under `backend/output/`.
Older health/detection modes are still available and process their images in memory.

## Run

From this folder, using the project's existing virtual environment:

```powershell
..\.venv-clip\Scripts\python.exe run.py
```

Open http://localhost:8000. The first start takes a few seconds while the default model warms up. Options: `--port 8080`, or `--host 0.0.0.0` to open it from a phone on the same Wi-Fi (browse to `http://<this-PC's-IP>:8000`).

To set up a fresh environment, install `requirements.txt` plus `ultralytics` in
a Python 3.12 environment and keep the existing weights in `../models/`. Use one
OpenCV package (`opencv-contrib-python-headless`); avoid installing conflicting
OpenCV wheels. If weights are already cached, set `$env:ONION_OFFLINE='1'` to skip
network checks. No separate server on port 8001 is required for this interface.

## Features

- Drag and drop, file picker, clipboard paste (Ctrl+V), or one of three sample photos from the held-out test split.
- Annotated image with numbered boxes. Hovering a box or a list row spotlights that onion.
- Healthy share gauge plus healthy, unhealthy, and total counts.
- Live confidence slider. The server returns every box scored 10% or higher, and the browser filters them instantly, with no re-upload.
- Model switcher. Switching keeps the photo; click Analyze to use the selected mode.
- Downloads: annotated PNG; automatically generated PDF in full grading; JSON in older modes.
- Click a box or onion row for the crop, condition scores, estimated diameter and grading explanation.
- Failed requests keep the photo and show a retryable error. Duplicate clicks are disabled during analysis.
- Light and dark themes. Works on phones.
- HEIC (iPhone) photos are decoded on the server through `pi-heif`.

## Models

The app reads weights from the project's shared [models/](../models) folder, so each file exists only once on disk. Set the `ALLIUM_MODELS_DIR` environment variable to read them from somewhere else.

| In the app | Weights | What it does | Default confidence |
|---|---|---|---|
| Full quality report (default) | Existing detector + `openai/clip-vit-base-patch32` | Five final grades, physical sizing and automatic PDF | 55% review threshold |
| Onion Health | `../models/trained/best.pt` | Your trained YOLO detector: class 0 `healthy`, class 1 `unhealthy`, trained at 512 px | 30% |
| Fruit & Veg YOLO11m | `../models/pretrained/piyu12-fruit-veg-yolo11m.pt` | 35-class produce detector, filtered to class 22 `Onion`. AGPL-3.0, see `piyu12-source.json` | 25% |
| YOLO-World · onion | `../models/pretrained/onion-world.pt` | Open-vocabulary detector prompted with "onion" | 20% |

The original modes remain for comparison. Full quality uses the Onion Health model
only to locate bulbs; CLIP decides their appearance condition. Without existing
detector weights it falls back to controlled-background OpenCV segmentation.
No new model is trained. Size uses the foreground contour inside each detection;
if no suitable contour or scale is available it remains unknown. Grade A means a
healthy appearance, even without a marker; size remains unverified. Low scores keep
the best-matching class and carry a review note instead of an Uncertain category.
Relative CLIP scores are not calibrated probabilities.
Full-report counts include low-confidence predictions and never change when boxes are hidden;
the confidence slider applies only to the original detector modes.

To add or retrain a model, put the `.pt` in `../models/trained/` and add a `ModelSpec` to `MODELS` in [app/inference.py](app/inference.py), with the path written relative to the models folder. Health models must have `healthy` and `unhealthy` classes, and detect-only models must have an `onion` class. Keep `-world` in a YOLO-World filename, because Ultralytics picks its loader from the name.

## API

- `GET /api/models`: model catalog, default model, and availability.
- `POST /api/analyze`: multipart `file` (max 20 MB, 80 MP), optional `model_id`. Returns the oriented image as a JPEG data URL (at most 2048 px on its longest side), detections sorted by confidence with normalized `[x1, y1, x2, y2]` boxes, and timings. Errors: `400` unreadable image, `404` unknown model, `413` too large.

Interactive docs at http://localhost:8000/docs.

Full grading is the default for `POST /api/analyze`. Its response includes the
existing canvas-compatible fields plus `quality` (complete saved grading result,
individual crops, rule snapshot, warnings, and `pdf_url`). The report is created
before returning success. `GET /api/reports/{UUID}` previews the PDF;
`?download=true` downloads it. `GET /api/quality-assets/{UUID}/{filename}` serves
the source photo, annotated photo and crops. Generated outputs contain lot photos;
this local prototype has no access control and should not be exposed publicly.

## Tests

```powershell
$env:ONION_OFFLINE='1'
..\.venv-clip\Scripts\python.exe -m unittest discover -s tests
```

## Layout

```text
webapp/
  run.py            start the server
  app/inference.py  model registry, EXIF handling, inference
  app/main.py       FastAPI routes and upload validation
  static/           index.html, styles.css, app.js, favicon, sample photos
  tests/            API and inference tests
```

Weights are not stored here. `app/inference.py` reads them from `../models/`.

## Limitations

- Results are visual estimates from one photo. Hidden sides and internal rot can't be seen.
- `best.pt` was trained for only 4 epochs on automatically generated boxes. On unhealthy and blurry photos it sometimes boxes a group of onions, adds a low-score box over the background, or misses bulbs. Raising the confidence slider removes most stray boxes. More training epochs and manually checked labels are the main levers for improvement.
# September 26 refinement

The default quality mode now uses two detector resolutions, group/duplicate-box
filtering and six CLIP crop views with separate cut, injury, decay, shoot and dry-neck
descriptions. See `../docs/DETECTION_REFINEMENT.md` for measured changes and remaining
errors. Counts include visible cut pieces. Re-analyze old photos to use these rules.
