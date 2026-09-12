# Annotation pilot results

Date: 8 September 2026. Dataset inventory: 17,828 images (12,367 Healthy, 5,461 Unhealthy).

Implemented and tested local image-to-box-to-folder-label pipeline. The label IDs are 0 healthy and 1 unhealthy, independent of red/white variety. Originals remain unchanged. A pretrained YOLOv8s-Worldv2 detector was downloaded from Ultralytics and its vocabulary set to onion. It is an open-vocabulary baseline, not a model fine-tuned on this dataset.

Selected the first and last image in sorted order from each of 17 leaf folders: 34 images, including both health categories, colors, mixed groups, singles and multiple onions. This is a diagnostic sample, not an unbiased accuracy benchmark.

| Confidence threshold | Predicted boxes | Images with boxes | Images with no boxes |
|---|---:|---:|---:|
| 0.20 | 42 | 16 | 18 |
| 0.05 | 173 | 27 | 7 |

No detection is a failure/review case here, not proof that an image contains no onions. These counts are not precision/recall measurements: no complete ground-truth bounding-box set exists yet.

Visual inspection found missing bulbs in mixed groups even at 0.05, substantial misses in a crowded unhealthy pile, and zero detections in all four sampled unhealthy single-onion images. Threshold reduction alone is insufficient. Do not use these candidates as fully annotated training ground truth or label the full dataset with this baseline without correction.

Artifacts:

- annotations-pilot/review.html: original threshold contact sheet.
- annotations-pilot-sensitive/review.html: lower-threshold contact sheet.
- Each output includes label text files, detection records, previews and summary.
- data/dataset-pilot-candidates/: 27 paired image/label examples from the lower-threshold run, explicitly unverified. The seven no-detection images remain in the review records.

Tests passed for exact health-folder matching (Unhealthy must not match Healthy), normalized coordinate clipping, and invalid box rejection. Both pilot runs finished. The full 17,828-image dataset has NOT been annotated.

Next requirement: obtain an onion-bulb detector that performs well on both fresh and degraded bulbs. A candidate exists at https://universe.roboflow.com/onionws/onion-detection-v8; its downloadable weights/access and suitability are unverified. User-provided local weights or configured access would allow a comparison. Alternatively, manually correct a representative seed set (initially 100–200 images across these folders), fine-tune a detector, then repeat the pilot before bulk labeling. This seed-set size is a starting point, not an accuracy guarantee.

## User-suggested model: jazzmacedo/fruits-and-vegetables-detector-36

Inspected the model card and config on 8 September 2026:
https://huggingface.co/jazzmacedo/fruits-and-vegetables-detector-36
https://huggingface.co/jazzmacedo/fruits-and-vegetables-detector-36/raw/main/config.json

Despite its repository name, its architecture is ResNetForImageClassification (ResNet-50), with 36 image-level classes including onion (ID 20). It returns image class scores, not per-instance boxes. It cannot directly produce the onion coordinates needed for this annotation pipeline or distinguish multiple bulbs. No weights were downloaded and no image inference was run: the architecture check establishes this incompatibility. It could classify crops produced by a separate detector, but would not replace that detector. Existing annotations were not changed.

## User-suggested detectors: Piyu12 and MohamedKhayat

Piyu12/fruit-veg-yolo11m-detector is a YOLO11m object detector with 35 classes including Onion. Downloaded best.pt at revision 82c9865261175e778ba5641cf8560b5d10439ec6. Local weight provenance is in models/pretrained/piyu12-source.json, and the run records its SHA-256. Only the Onion class is retained, then relabeled from source folders.

Source: https://huggingface.co/Piyu12/fruit-veg-yolo11m-detector

On the same 34-image diagnostic sample at confidence 0.20, Piyu12 produced 242 boxes across 25 images; nine images had no onion boxes. Healthy: 199 boxes in 23 of 26 images. Unhealthy: 43 boxes in two of eight images. All four unhealthy single-onion samples had no detections. Higher box totals are not proof of higher accuracy: visual inspection of Healthy/Mixed/2WO8RO/Onion 00593.jpg showed individual bulb boxes plus an erroneous large box spanning the group. A crowded unhealthy pile still has missed bulbs and extra oversized boxes.

Review: annotations-pilot-piyu12/review.html. These are unverified pseudo-labels, not a completed or approved training dataset.

Lowering Piyu12's confidence threshold to 0.05 produced 278 boxes but still only 25 of 34 images with onion detections (nine no-detection cases). The extra boxes did not recover image coverage. Outputs are in annotations-pilot-piyu12-sensitive, including review.html. Both Piyu12 runs completed; full-dataset labeling remains pending a reliable detector/correction workflow.

MohamedKhayat/fruit-detector-rtdetrv2-101 is an RTDetrV2ForObjectDetection model, but its config has 12 classes and no onion class. It was not downloaded or run because it cannot directly supply onion-class boxes with its current trained head. Renaming another class would not teach onion detection.

Verified config at revision 6a4d48636e3b295780973471a9c8969d0cc93b86:
https://huggingface.co/MohamedKhayat/fruit-detector-rtdetrv2-101/blob/6a4d48636e3b295780973471a9c8969d0cc93b86/config.json
