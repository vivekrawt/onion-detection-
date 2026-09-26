# Manual evaluation

Place tightly cropped, independently labeled onion photos into `healthy/`,
`damaged/`, `rotten/`, and `sprouted/`. Collect multiple bulbs under varied light
and backgrounds. Use one predominant condition per crop and document ambiguous
or multi-defect cases separately. Keep the same bulb/lot out of both prompt-tuning
and final evaluation sets. Ask a knowledgeable human grader to label the photos.

Run `python -m backend.evaluate test_images`. The JSON records raw and thresholded
accuracy, confusion matrices, precision, recall, F1, support, macro F1 and abstentions.
Uncertain predictions count as errors for accuracy/recall. Zero denominators are
reported as zero; missing classes have zero support and affect the four-class macro F1.

Do not report metrics before collecting a labeled dataset. This evaluates CLIP
condition classification only. Independently compare segmentation counts with
manual counts, and estimated diameters against calipers/rulers. Log failed marker
detections and merged/touching bulbs. No images or trained models are bundled here.
