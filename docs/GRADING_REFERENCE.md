# Grading baseline — researched 8 September 2026

Use NCCF's EOI dated 23 June 2026, Annexure I (printed page 23), for the prototype. It concerns Rabi onion procurement in Maharashtra and Madhya Pradesh under the Price Stabilization Fund. This is a dated project profile, not a claim that every procurement scheme uses identical rules or that URS procurement is currently open.

Primary source: [NCCF EOI and quality norms](https://www.nccfindia.com/documents/20121/42406/1782229402713_-_PAACS.pdf).

The annexure specifies a 35–70 mm procurement diameter range. Grade A permits surface staining up to 30%; URS permits up to 40%. Cuts/cracks and ruptured skin fail both. Single skin and misshapen/double bulbs are permitted under URS; Grade A is stricter. Rot is excluded. URS lists a 10% sunburn allowance, but its measurement basis needs clarification before automation. The complete annexure includes other requirements; these examples are not an exhaustive grading predicate.

URS expands to Under Relaxed Specifications: [PTI report, 24 June 2026](https://money.rediff.com/news/market/onion-buffer-stock-procurement-slow-despite-price-hikes/49402320260624).

## Project interpretation

- Use diameter <35 mm for the undersized flag. Measurements near the boundary require uncertainty handling.
- Record >70 mm separately as outside the profile; it is not undersized or necessarily damaged.
- Keep four appearance categories: good, damaged, rotten, undersized, with rotten > damaged > undersized > good precedence. Independent size/defect flags preserve overlapping observations.
- Sprouting is outside the dataset and model scope per the user. Do not claim that the application checks its absence.
- Produce a second, separate grading result: estimated Grade A, estimated URS-only, rejected, or needs review. Evaluate Grade A first to avoid double counting bulbs that also satisfy relaxed criteria.
- Grade A and URS-only percentages use all grading-assessed onions, including rejected onions, as their common denominator. Display count-based estimates and assessment coverage. Do not infer weight percentages.
- Four coarse labels cannot implement the grading rules alone. Training annotations must include skin condition, staining extent, shape, and other relevant visual attributes. Undefined rule interpretations remain review cases.
- Single-view images show only part of the surface; observed staining fractions are not automatically whole-bulb fractions. Full grading also includes properties such as firmness and smell that ordinary video cannot verify. Report visual eligibility estimates and require manual checks for full specification compliance.
- Preserve source date and profile version. Verify applicable amendments before using reports for real procurement.
