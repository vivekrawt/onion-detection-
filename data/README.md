# Data artifacts

| Folder | What it is |
|---|---|
| `annotations-piyu12-gpu-full/` | Full labeling run over the raw photos with the Piyu12 detector on the Intel GPU: one JSON record per image, YOLO label files, and the run settings in `run.json`. This is the input to `scripts/build_dataset.py`. |
| `dataset-pilot-candidates/` | Small pilot export of candidate image/label pairs from the early annotation experiments. |

## The two datasets stay at the project root

They are not in here because tools store absolute paths pointing at them:

- `../Red and White Onion Dataset/` — the original photos and the input to labeling. Every record in `annotations-piyu12-gpu-full/records/` stores an absolute path into it, so moving it breaks a dataset rebuild unless those records are rewritten.
- `../onion-dataset/` — the built train/validate/test dataset. Its `data.yaml` stores an absolute `path:`, which has to be updated if the folder moves.
