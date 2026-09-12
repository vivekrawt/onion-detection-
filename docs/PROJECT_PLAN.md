# Onion Quality Assessment — Project Plan

## 1. Product goal

Build a mobile application that accepts a batch video or image, identifies individually visible onions, assesses visible defects, estimates size when calibrated, counts onions without counting every video frame as a new onion, and generates a reviewable quality report.

Start with a fixed camera, even lighting, a contrasting background, and onions in a single layer. Support a stationary tray image or a one-way conveyor video first. Handheld scans and dense piles are later research work: hidden onions cannot be counted reliably, and onions leaving and re-entering the image can be counted twice.

Video appearance cannot establish internal rot or the condition of unseen surfaces. Multiple views or controlled rotation improve visible surface coverage. Describe results as visual quality estimates.

## 2. Classification and grading contract

Store independent observations for each onion: visible rot, physical damage, measured size, observation confidence, and evidence frames. An onion can have more than one defect.

For the requested four mutually exclusive output categories, propose this configurable precedence:

1. Rotten: visible rot exceeds the agreed defect threshold.
2. Damaged: physical damage under the labeling guide.
3. Undersized: no higher-priority defect and calibrated diameter below the agreed cutoff.
4. Good: sufficiently observed, no disqualifying visible defect, and size passes the configured requirement.

Sprouted onions are absent per the user. Sprouting detection is excluded; retain four primary categories.

Insufficient evidence is a review status, not a forced quality label. Missing size calibration prevents a final good/undersized decision for otherwise acceptable onions; a clearly rotten onion can still be classified rotten. Ambiguous rot versus damage needs review.

Use the dated NCCF June 2026 baseline in [GRADING_REFERENCE.md](GRADING_REFERENCE.md). URS means Under Relaxed Specifications. Default undersized cutoff: diameter below 35 mm. Above 70 mm is a separate outside-profile flag. Appearance categories and procurement grades remain separate; video estimates are count-based and do not establish weight percentages or full compliance.

Initial report calculations:

- Primary count percentages = category count / assessed unique onions × 100.
- Coverage = assessed unique onions / all counted unique onions × 100.
- Review count = all counted unique onions − assessed unique onions.
- Grade A percentage = onions meeting every configured Grade A rule / grading-eligible onions × 100, explicitly labeled as a count-based estimate.
- URS-only percentage counts onions passing relaxed rules but not Grade A. Both grade percentages use all grading-assessed onions, including rejected onions, as denominator. Report review cases separately.
- Zero denominators produce unavailable, never a fabricated zero percentage.

Show denominators and exclusions. When review cases remain, flag grading as provisional. Do not extrapolate a visible sample to an entire lot without a sampling protocol. Version all rules in reports.

## 3. Proposed architecture

Mobile app (Flutter) → Python API (FastAPI) → video processing worker → OpenCV preprocessing → trained onion detector/instance segmenter → tracker → per-onion defect classifier and calibrated size estimator → temporal aggregation → grading rules → report storage and mobile results.

These are proposed implementation choices, not installed dependencies. Begin with server inference so models can change without rebuilding the app. Evaluate on-device inference after measuring accuracy, latency, privacy needs, and device capability. Pin dependency versions during implementation and review model/data licenses before distribution.

OpenCV handles decoding, orientation, geometric calibration, frame quality checks, crops, overlays, and output video. A trained model supplies learned visual recognition; color thresholds alone are not a reliable production classifier across onion varieties and lighting.

Use an onion instance segmenter where touching onions and size measurement require boundaries. Begin with a detector plus crop classifier if the controlled setup allows it. Prototype YOLO-based detection with ByteTrack or BoT-SORT, then evaluate identity switches on actual onion footage. Tracking IDs are estimates, not guaranteed physical identities.

## 4. Video analysis workflow

1. Validate video format, duration, orientation, and decoding; record batch metadata.
2. Check lighting, blur, camera stability, and calibration reference. Request recapture when necessary.
3. Detect individual onions and optionally segment each outline.
4. Associate detections across frames, keeping stable track histories.
5. Analyze clear crops for rot and damage; reject heavily occluded observations.
6. Estimate physical diameter only with valid geometric calibration. A scale reference must match the measurement plane; perspective and onion height create error. Validate against caliper measurements and use multiple views when necessary.
7. Aggregate evidence across clear frames; validate how persistence and confidence thresholds trade missed defects against false alarms. Do not trust a single blurry frame.
8. Count a confirmed track once when it crosses a configured line in the allowed direction. Define start/end partial-track handling and flag identity ambiguity. For tray images, count segmented instances in one selected clear view rather than summing video detections.
9. Apply quality and grading rules; send uncertain items to review.
10. Produce counts, evidence images, an annotated video, and JSON/PDF report. Show progress while processing; measure turnaround rather than promise instant processing for arbitrary videos.

## 5. Data and labeling

Collect representative footage from intended phones and capture setups, covering varieties, skin colors, sizes, backgrounds, lighting, touching onions, and all defects. Include hard negatives such as loose skins, soil, shadows, and non-onion objects.

An initial collection target is 2,000–5,000 independently observed onions, including several hundred examples of each important defect where feasible. This is a starting budget, not an accuracy guarantee; expand from learning curves and error analysis. Adjacent frames are not independent samples.

Annotate bounding boxes or masks, independent defect labels, uncertainty, physical size measured with calipers, batch identity, and onion identity where possible. Have agricultural inspectors agree on examples and severity thresholds; obtain double labels for a subset and adjudicate disagreement. Label tracks and crossing events in evaluation videos.

Split train/validation/test by batch or collection session before extracting frames. Keep all views of the same onion in one split. Hold out devices and sites to test generalization. Never tune thresholds on the final test set.

## 6. Mobile experience and reports

Screens: create batch → capture guidance and calibration → record/upload → processing progress → category counts and grading coverage → review uncertain onions → export/share report.

Report fields: report/batch ID, capture and analysis timestamps, unique onion total, four primary counts, review count, percentage denominators, size units and calibration status, Grade A/URS results or unavailable reason, model/rule versions, representative evidence, and reviewer corrections with original predictions retained.

For a provisional count example: 100 unique onions, 60 good, 15 damaged, 10 rotten, 5 undersized, and 10 needing review gives 90 assessed onions and 90% coverage. Good is 66.7% of assessed onions. That value is not automatically Grade A.

Restrict report/video access by user, validate uploads, set retention limits, and make deletion available. Save manual overrides with an audit history to support transparency.

## 7. Implementation milestones

| Phase | Deliverable | Indicative effort |
|---|---|---|
| Requirements and capture experiment | Agreed label guide, grading definitions, sample footage, capture setup | 3–5 days |
| Dataset pilot | Labeled data, split manifest, annotation quality review | 1–2 weeks |
| Offline model baseline | Image detection, defect assessment, size experiment, evaluation report | 1–2 weeks |
| Video pipeline | Tracking, counting, evidence aggregation, annotated video and JSON | 1 week |
| Mobile/API MVP | Upload, background jobs, results, review and downloadable report | 1–2 weeks |
| Field validation | Held-out tests, difficult-case review, performance measurements | 1–2 weeks |

Overall estimate: roughly 6–10 weeks for an MVP with accessible data and timely labels. Data collection may extend this. Build a small offline video proof of concept before committing to full mobile development.

## 8. Validation and release gates

Agree numeric acceptance thresholds after the pilot establishes feasibility; do not claim target performance as measured performance.

- Detection: precision/recall and missed instances, including touching onions.
- Quality: per-defect precision, recall, confusion matrix, and especially missed rot; report reviewed/abstained cases separately.
- Counting: absolute error per video, duplicate and missed crossings, and identity switches against manually counted videos.
- Size: millimeter error against calipers and error near the chosen undersized boundary.
- Grading: percentage-point error against independently inspected batches using identical denominators and rules.
- Robustness: results by device, variety, lighting, occlusion, and capture site.
- Product: processing time per video minute, upload failures, memory use, report reproducibility, and correction audit trail.

Test empty videos, corrupt uploads, no-onion scenes, partial entry/exit, repeated crossings, missing calibration, and batches where all observations require review. Launch only for capture conditions supported by test evidence.

## 9. Planned repository structure

```text
backend/             API, jobs, access control and storage
vision/              detection, tracking, classification and calibration
grading/             configurable predicates and percentage calculations
mobile/              Flutter capture, upload, review and report screens
configs/             capture profiles and versioned grading rules
data/                dataset instructions and split manifests; no raw data in Git
models/              model metadata and retrieval instructions
reports/             report templates
tests/               counting, grading and pipeline validation
docs/                annotation guide, capture protocol and evaluation results
```

## 10. Inputs needed before training

Obtain representative video, intended capture mode (conveyor, tray, or handheld pile), onion varieties, and labeled examples. The dated grading baseline is in GRADING_REFERENCE.md; sprouting is excluded. The project can be planned now, but reliable trained classification cannot be delivered without labeled data and validation.

## Technical references

- OpenCV camera calibration: https://docs.opencv.org/4.13.0/d4/d94/tutorial_camera_calibration.html
- Ultralytics multi-object tracking: https://docs.ultralytics.com/modes/track/

These references support implementation mechanisms, not onion-specific accuracy or grading certification.

