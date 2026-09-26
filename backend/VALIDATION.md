# Validation record

Checked on 2026-09-26 with Python 3.12, Transformers 4.57.6, OpenCV contrib
4.14.0, CPU PyTorch, and pretrained `openai/clip-vit-base-patch32`.

- Seven offline tests passed: geometry, marker exclusion, classification hierarchy,
  missing scale, statistics, evaluation abstention, image validation, upload limits,
  persisted analysis retrieval and PDF download (several checks share one test).
- Real pretrained weights downloaded into the project cache. Single-image CLI
  inference completed on an actual onion crop. The maximum relative score was
  about 0.480, resulting in `uncertain` at the 0.55 threshold.
- Full API startup loaded real CLIP once. `/analyze` ran real inference on a photo
  and a synthetic two-object geometry fixture; class scores summed to one.
  Saved results generated a downloadable PDF through `/generate-report`.
- The one-page PDF layout was rendered with Poppler and visually inspected.
  Synthetic figures and stub labels were explicitly identified as layout-test data.
- Marker generation, Python compilation and Git whitespace checks passed.
- Empty evaluation folders produced a clear error instead of fabricated metrics.

Local verification reused available Python runtime packages to avoid duplicate
large downloads. Fresh installation instructions are in README.md.

**Not verified:** Flutter analyzer/tests/native build, camera and sharing on a
device (Flutter SDK unavailable); clinical/commercial/official grading suitability;
condition-classification accuracy on an independently labeled dataset.
Synthetic tests validate plumbing and arithmetic, not onion recognition accuracy.
