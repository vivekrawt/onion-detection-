# Mixed onion dataset build

The user selected Piyu12 YOLO11m and authorized bulk annotation and dataset creation. Healthy and unhealthy labels come from source folders, not the detector. Red, white and mixed varieties share the same class IDs: 0 healthy, 1 unhealthy.

## Output

```text
onion-dataset/
  data.yaml
  train/
    images/
    labels/
  validate/
    images/
    labels/
  test/
    images/
    labels/
  review/images/
  manifest.json
  summary.json
  validation.json
  README.md
```

Each split combines both health classes without class subdirectories. Unique filenames map each image to a same-stem YOLO text label. The YAML uses `val: validate/images`, which is the training tool's expected key. Confidence threshold is 0.20, IoU suppression threshold 0.45, and image size 640. No new health categories or augmentations are added.

## Execution

The original PyTorch model was exported to OpenVINO (float32 weights) for the computer's Intel GPU. Exported models use fixed square input padding. A fair comparison against the original model with identical padding gave identical box counts in all 34 pilot images (257 boxes), mean matched-box IoU 0.994389, minimum 0.897498. GPU execution may use reduced precision internally. See models/pretrained/acceleration-comparison.json and models/pretrained/piyu12-source.json for evidence and model provenance.

```powershell
.\.venv\Scripts\python.exe scripts/annotate.py --model models/pretrained/piyu12-fruit-veg-yolo11m_openvino_model --device intel:gpu --confidence 0.20 --output data/annotations-piyu12-gpu-full --square --no-previews
.\.venv\Scripts\python.exe scripts/build_dataset.py --annotations data/annotations-piyu12-gpu-full --output onion-dataset
.\.venv\Scripts\python.exe scripts/validate_dataset.py onion-dataset
```

The annotator resumes completed records. Dataset packaging requires a new output directory and refuses incomplete annotation runs. The source images remain unchanged; output images are copies. The earlier partial CPU run and all pilot outputs are preserved for comparison and are not combined into this build.

## Splits and quality

Target split is 80% train, 10% validate, 10% test using seed 42 and health-class stratification. Blocks of 100 consecutive numbered images within each source folder stay together, and exact duplicate images are linked into the same split. This produces approximate ratios. These blocks are a heuristic: actual physical onion and capture-session identity is unknown, and similar images across block boundaries can still leak. Do not claim independent field accuracy based on these splits.

Every original image is represented in manifest.json. Images with no onion detections, decoding failures, or contradictory health labels on duplicate content go into review/images and are excluded from the YAML. Empty labels are not generated for missed onions. All remaining boxes are automatically generated annotations accepted by the user for this dataset, not manually verified ground truth. Validation/test labels should be checked manually before reporting reliable detection accuracy. Known limitations include missed degraded bulbs and boxes spanning groups.

Validation checks source coverage and hashes, paired names, normalized boxes, health class IDs, both classes in each split, YAML paths, and absence of exact-duplicate and block-level leakage. Actual split and exclusion counts are saved in summary.json when the build completes.
