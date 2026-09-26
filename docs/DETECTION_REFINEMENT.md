# Counting and visible-condition refinement — 2026-09-26

The default Full quality report now combines 640/1280 detector passes, removes
group boxes enclosing distinct bulbs, merges repeated detections, and checks
obvious non-onion candidates against knife, empty cloth and loose-peel descriptions.
Counts refer to visible bulbs **or pieces**; two halves count as two visible pieces.
This cannot recover hidden bulbs or reconstruct the original number before cutting.

CLIP receives square-padded crops rather than losing crop ends to center cropping.
Expanded context masks neighboring detected bulbs outside the target rectangle.
Six views (whole, center, top, bottom, left, right) compare separate descriptions
of whole bulbs, dry necks/roots, cut faces, injuries, growing shoots and decay.
Repeated cut evidence yields Damaged even for fresh white flesh. Repeated decay
evidence takes priority if a cut onion is also spoiled. Dry necks alone do not
satisfy the repeated sprout check. These are experimental evidence rules, not
trained defect detectors or calibrated probability estimates.

Settings and margins are in `backend/app/config.py`; prompts and decisions are
in `backend/app/models/evidence.py`. Raw class scores and evidence votes remain in
saved results. Displayed confidence is the raw score for the selected condition,
not a manufactured high confidence after an override. Conflicts request review.
The five output categories and independent marker-based undersize rule remain.

## Actual checks

32 tests passed: 20 backend/refinement tests and 12 web/API tests, including actual
model integration, PDF/crop routes, duplicate/group boxes, adjacent bulbs, edge
preservation, cut override, decay priority, dry-neck contrast and background rejection.

Full real-model runs on saved examples (development checks, **not held-out accuracy**):

| Example | Previously saved result | Revised result |
| --- | --- | --- |
| User-reported `33eb4ec6…/source.jpg` | 13 boxes, 1 false sprout | 12 visible bulbs, 0 sprouts; 6 Grade A, 6 Damaged |
| Knife-cut halves `70fa9e04…` | Both halves labeled Grade A | Both halves Damaged; 10 visible bulbs/pieces after rejecting knife/peel detections |
| Sprouted lot `f9de2f6d…` | 1 box, no sprout labels | 10 boxes, 2 Sprouted; several shoots still missed |
| Generated rotten pile `0bded086…` | 0 boxes | 8 boxes; 7 Rotten, 1 Grade A |
| Generated damaged reference | 1 box, Grade A | 10 boxes; 1 Damaged, 1 Rotten, 8 Grade A |

The reported photo still has false damage labels. The generated damaged photo
still has substantial classification errors. Overlapping/partial bulbs can still
be missed or merged. Prompting and geometric filtering do **not** establish a
robust production grader. Further accuracy work needs human-verified per-bulb
boxes/masks and condition labels, including real knife cuts, sprouts, dry necks,
healthy peeling skin, rot, and mixed defects, plus a separate held-out test set.
Do not use the detector's existing pseudo-labeled group boxes as count ground truth.

Historical saved reports are unchanged; upload and analyze again for the new rules.
