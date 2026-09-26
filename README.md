# Onion Quality Assessment

## New: zero-shot CLIP + Flutter prototype

The requested **AI-Based Onion Quality Detection and Grading System Using
Pretrained CLIP** is in [backend/](backend/README.md) and [mobile/](mobile/README.md).
It uses pretrained CLIP without training, OpenCV segmentation and marker sizing,
configurable grading, FastAPI, PDF reports, and a six-screen Flutter client.
Start with the Phase 1 CLI in the backend guide, then follow phases 2-9.
The existing trained-model application described below remains a separate project path.

AI-assisted inspection of onion batches from photos: a trained vision model detects each bulb and labels it healthy or unhealthy, with a web app for running it.

## Quick start

```powershell
.\.venv-clip\Scripts\python.exe webapp\run.py
```

Then open http://localhost:8000, choose a photo and click **Analyze quality**.
The existing Allium UI now includes CLIP grading and automatically generated PDF
reports. See [webapp/README.md](webapp/README.md).

## Structure

```text
OnionDetection/
├─ webapp/                       the web application (FastAPI + browser UI)
├─ models/
│  ├─ trained/                   models we trained on our data (best.pt: healthy/unhealthy)
│  └─ pretrained/                third-party models used to label and detect the data
├─ data/
│  ├─ annotations-piyu12-gpu-full/   labeling run output, input to the dataset build
│  └─ dataset-pilot-candidates/      early pilot export
├─ scripts/                      the labeling and dataset pipeline
├─ docs/                         plan, annotation guide, dataset build, grading reference
├─ tests/                        pipeline tests
├─ onion-dataset/                built train/validate/test dataset (absolute path in data.yaml)
└─ Red and White Onion Dataset/  original source photos
```

The two dataset folders stay at the top level because tools record absolute paths to them; see [data/README.md](data/README.md). Model weights and datasets are git-ignored.

## Pipeline

```powershell
.\.venv\Scripts\python.exe scripts/prepare_model.py        # fetch and prompt the open-vocabulary detector
.\.venv\Scripts\python.exe scripts/annotate.py             # label the raw photos
.\.venv\Scripts\python.exe scripts/build_dataset.py        # pack into train/validate/test splits
.\.venv\Scripts\python.exe scripts/validate_dataset.py onion-dataset
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Recorded commands and results are in [docs/DATASET_BUILD.md](docs/DATASET_BUILD.md) and [docs/ANNOTATION_GUIDE.md](docs/ANNOTATION_GUIDE.md). Dataset completion is recorded in `onion-dataset/validation.json`.

## Status and documents

The healthy/unhealthy detector and the web app are built. The wider roadmap, including video, tracking, sizing and grading, is in [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md).

- [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) — goals, architecture, milestones, validation gates
- [docs/ANNOTATION_GUIDE.md](docs/ANNOTATION_GUIDE.md) — healthy/unhealthy labeling workflow
- [docs/ANNOTATION_PILOT_RESULTS.md](docs/ANNOTATION_PILOT_RESULTS.md) — measured pilot results and detector limits
- [docs/DATASET_BUILD.md](docs/DATASET_BUILD.md) — how the mixed dataset was built
- [docs/GRADING_REFERENCE.md](docs/GRADING_REFERENCE.md) — dated NCCF grading baseline
- [models/README.md](models/README.md) — trained vs pretrained weights

Results are visual estimates from photographs. Hidden surfaces and internal rot cannot be judged, so these are not a substitute for physical grading.
