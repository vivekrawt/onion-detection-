# Allium: onion health web app

Upload a photo of onions. The app boxes every bulb, labels it **healthy** or **unhealthy** with the trained model, and shows the counts. Everything runs locally on CPU, and images are processed in memory and never saved to disk.

## Run

From this folder, using the project's existing virtual environment:

```powershell
..\.venv\Scripts\python.exe run.py
```

Open http://localhost:8000. The first start takes a few seconds while the default model warms up. Options: `--port 8080`, or `--host 0.0.0.0` to open it from a phone on the same Wi-Fi (browse to `http://<this-PC's-IP>:8000`).

To set up a fresh environment instead: `pip install -r ..\requirements-lock.txt -r requirements.txt`.

## Features

- Drag and drop, file picker, clipboard paste (Ctrl+V), or one of three sample photos from the held-out test split.
- Annotated image with numbered boxes. Hovering a box or a list row spotlights that onion.
- Healthy share gauge plus healthy, unhealthy, and total counts.
- Live confidence slider. The server returns every box scored 10% or higher, and the browser filters them instantly, with no re-upload.
- Model switcher. Switching re-analyzes the current image.
- Downloads: annotated PNG with a caption band, and a JSON report (counts, threshold, per-onion boxes in pixels).
- Light and dark themes. Works on phones.
- HEIC (iPhone) photos are decoded on the server through `pi-heif`.

## Models

The app reads weights from the project's shared [models/](../models) folder, so each file exists only once on disk. Set the `ALLIUM_MODELS_DIR` environment variable to read them from somewhere else.

| In the app | Weights | What it does | Default confidence |
|---|---|---|---|
| Onion Health (default) | `../models/trained/best.pt` | Your trained YOLO detector: class 0 `healthy`, class 1 `unhealthy`, trained at 512 px | 30% |
| Fruit & Veg YOLO11m | `../models/pretrained/piyu12-fruit-veg-yolo11m.pt` | 35-class produce detector, filtered to class 22 `Onion`. AGPL-3.0, see `piyu12-source.json` | 25% |
| YOLO-World · onion | `../models/pretrained/onion-world.pt` | Open-vocabulary detector prompted with "onion" | 20% |

Only Onion Health judges health. The other two locate onions without grading them, so they are there for comparison.

To add or retrain a model, put the `.pt` in `../models/trained/` and add a `ModelSpec` to `MODELS` in [app/inference.py](app/inference.py), with the path written relative to the models folder. Health models must have `healthy` and `unhealthy` classes, and detect-only models must have an `onion` class. Keep `-world` in a YOLO-World filename, because Ultralytics picks its loader from the name.

## API

- `GET /api/models`: model catalog, default model, and availability.
- `POST /api/analyze`: multipart `file` (max 20 MB, 80 MP), optional `model_id`. Returns the oriented image as a JPEG data URL (at most 2048 px on its longest side), detections sorted by confidence with normalized `[x1, y1, x2, y2]` boxes, and timings. Errors: `400` unreadable image, `404` unknown model, `413` too large.

Interactive docs at http://localhost:8000/docs.

## Tests

```powershell
..\.venv\Scripts\python.exe -m unittest discover -s tests
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
