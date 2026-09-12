# Healthy/unhealthy bounding-box annotation

The input contains 17,828 images: 12,367 Healthy and 5,461 Unhealthy, across 17 leaf folders. Both onion colors share the same health classes. Class IDs are zero-based: 0 healthy, 1 unhealthy.

Every onion detection inherits the exact Healthy/Unhealthy ancestor folder. This assumes each image contains only the stated health category. The detector does not diagnose health. These two labels cannot teach a model to distinguish rotten from damaged or measure undersize without additional annotation/calibration.

## Detector selection

The initial local candidate is official YOLOv8s-Worldv2 with the text vocabulary `onion`, not an onion-specific fine-tuned model. Its suitability must be checked on this dataset. Source: https://docs.ultralytics.com/models/yolo-world/

An onion-specific hosted candidate was found at https://universe.roboflow.com/onionws/onion-detection-v8. Its accuracy on these images and access to downloadable weights have not been verified. No images have been uploaded there. Another model found online targets onion leaf diseases and is unsuitable for whole-bulb localization.

## Run locally in PowerShell

```powershell
.\.venv\Scripts\python.exe scripts/prepare_model.py
.\.venv\Scripts\python.exe scripts/annotate.py --inventory-only
.\.venv\Scripts\python.exe scripts/annotate.py --per-folder 2 --output data/annotations-pilot
.\.venv\Scripts\python.exe scripts/annotate.py --output data/annotations
```

Model preparation downloads pretrained weights and the text encoder. Image inference is local. To substitute an onion detector, use `--model path/to/model.pt`; its class metadata must contain `onion`, `onions`, or `onion bulb`. All other model classes are filtered out.

Create a visual review page with `.\.venv\Scripts\python.exe scripts/review_gallery.py annotations-pilot`. Dependency versions are recorded in `requirements-lock.txt`. Ultralytics code/weights have licensing conditions (including AGPL/enterprise options); check the selected licenses before distributing a proprietary product.

Outputs:

- `labels/`: YOLO text files mirroring input folders, one line per box: class_id center_x center_y width height, coordinates normalized to [0,1].
- `records/`: source paths, pixel coordinates, confidence, dimensions, and review status.
- `previews/`: annotated JPEGs.
- `inventory.json`, `run.json`, `summary.json`: source counts, reproducibility metadata and results.

Resume with the same command: existing completed records are skipped. Changed model/settings require a new output directory. Do not change source images during an annotation run; use a fresh output directory after editing inputs. No-detection or corrupt images have no training label and need review. All generated boxes are pseudo-labels, marked needs_review; confidence is localization confidence, not health confidence.

Inspect misses, merged boxes spanning touching onions, false positives, loose boundaries and partial bulbs. Correct labels before final training; independently hand-label validation/test images so detector errors do not become the evaluation target. Keep adjacent frames and views of the same physical onions in one split. No random frame-level training split is created automatically because capture-session identities are not yet known.

The original dataset is never modified. Folder paths disambiguate repeated filenames. Sprouting remains outside the requested classes.

See ANNOTATION_PILOT_RESULTS.md for measured pilot results and the current detector limitation. Package candidate image/label pairs with `.\.venv\Scripts\python.exe scripts/export_candidates.py annotations-pilot-sensitive data/dataset-pilot-candidates`. The destination must be new. This does not mark labels reviewed or invent a train/validation split.
