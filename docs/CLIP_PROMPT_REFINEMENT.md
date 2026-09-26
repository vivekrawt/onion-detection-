# Five-category appearance grading

The user-supplied examples on 2026-09-26 refine the visible definitions in
`backend/app/config.py`. No new model was trained and reference images are not
used as hidden image prototypes or hard-coded predictions.

- Grade A: healthy whole bulb, including normal red/purple/white color, dry
  roots/necks, pale patches and loose papery flakes over intact flesh.
- Damaged: physical cuts, deep cracks, dents, bruises or substantial wounds.
- Rotten: visible decomposition, mold, dark decaying flesh and wet/collapsed tissue.
- Sprouted: growing green or pale shoots emerging from the bulb, not dry roots.
- Undersized: calibrated geometric measurement below the configured minimum.

Smell and internal firmness cannot be established from these photos. Grade A
means healthy appearance, not certification that the bulb passes a size standard.
Without a usable marker, size and the undersized flag stay null. The highest CLIP
class is always retained; low scores set `needs_review`, never a sixth category.
Counts, web/mobile views and new PDF reports use the same five classes. Older
saved reports keep their original assessments and should be reanalyzed for new rules.

## Reference checks (not held-out evaluation)

The existing detector provided 10 crops from `a5e829d18a60248d9d09.jpg` and 9
from `fcfc85c90b5b1a709e28.jpg`. The selected short balanced prompts classified
9/10 and 4/9 crops respectively as Grade A; remaining crops were Damaged.
These are detections, not independently verified true onion counts.

The detector found zero candidates in the supplied generated rot scene and only
one in the generated damage scene. To separate detection from classification,
three visible bulbs in each image were manually cropped for diagnostic checks.
The selected prompts classified the three rot crops Rotten, but incorrectly called
the three damaged crops Grade A. No sprouted reference was supplied. These are
known remaining errors; prompt changes do not make general-purpose CLIP a validated
onion inspector. More realistic labeled defect crops are needed for evaluation.

Longer healthy-skin prompt ensembles improved the two healthy references slightly
but misclassified all three rot crops, so those variants were rejected. Use fresh
unseen images for any later accuracy measurements. The user-provided dataset paths
contain `train`, and the generated references were used for prompt development.
