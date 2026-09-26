# Models

Two kinds of weights, deliberately kept apart.

## `trained/` — trained by us on this project's data

| File | What it is |
|---|---|
| `best.pt` | YOLO detector trained on `onion-dataset`. Classes: `0 healthy`, `1 unhealthy`, trained at 512 px for 4 epochs. This is the model the web app uses to judge onion health. Originally named `best (2).pt`. |

## `pretrained/` — third-party models used to label and detect the data

None of these were trained by us, and none of them judge health.

| File | What it is |
|---|---|
| `clip-vit-base-patch32/` | Hugging Face `openai/clip-vit-base-patch32` snapshot used by the backend. The 605 MB `model.safetensors` file is stored with Git LFS. |
| `piyu12-fruit-veg-yolo11m.pt` | 35-class produce detector (class 22 `Onion`) that auto-labeled the raw photos into `onion-dataset`. Provenance and license in `piyu12-source.json` (AGPL-3.0). |
| `yolov8s-worldv2.pt` | Official YOLO-World open-vocabulary base weights. |
| `onion-world.pt` | The same network with the text prompt "onion" baked in, produced by `scripts/prepare_model.py`. Keep `-world` in the filename: Ultralytics picks its loader from the name. |
| `piyu12-source.json` | Download source, revision and license of the Piyu12 detector. |
| `acceleration-comparison.json` | Evidence that the OpenVINO export matched the PyTorch model (identical box counts on 34 pilot images, mean IoU 0.994). |

Large detector weight files remain git-ignored because of their size. The CLIP
snapshot is the exception: its safetensors file is tracked with Git LFS so the
backend works from a fresh LFS clone. OpenVINO exports are not stored: regenerate
them into this folder with `scripts/prepare_acceleration.py`, or
`scripts/prepare_batch_acceleration.py` for the batch-of-4 variant.

The web app reads from this folder. Point it elsewhere with the `ALLIUM_MODELS_DIR` environment variable.
