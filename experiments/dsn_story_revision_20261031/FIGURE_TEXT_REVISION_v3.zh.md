# Final text-only artwork revision v3

Current directory: `FIGURES_v3`. This supersedes v2 for manuscript placement;
v2 and its numeric/visual gate remain byte-for-byte intact. Full measured-value
and claim mapping remains in `FIGURE_CAPTIONS_AND_EVIDENCE_MAP.zh.md`.

Actual plot source: `aaa13a008772700a2befb0b0d8022e1098f7d7e5`,35files;
manifest `FIGURE_SOURCE_v3.json` SHA
`e0572331403335e901d6cb2a52fe42d9db18175d99c4db3bcc494269765c8e1e`.
Bundle and complete snapshot are supplied. Actual interval analysis remains
`73026a11f6db202d723e6028ad85e6833888ec78`; no real-input reader was rerun.

## Changes responding to both cold reads

1. `coordination_protocol`: UNKNOWN now says “may run/buffer; no commit.”
   The AU box explicitly names the original Correct/Update result P3, complete
   result plus checked parent, and synchronization before installation. Its
   box is slightly wider/taller so four readable lines do not overlap.
2. `composition_and_content`: panel(b) now says “More matching content meets
   deadlines”; the upper bank is “Matched trials.” “Resident requests” and
   Pass are retained; main caption supplies the distinct trial/request P99
   D2/C8 criteria. Tiny gray tails remain unlabelled remainders, with rounding
   explained in the manuscript caption rather than using tiny fonts.
3. `timely_interval_comparison` is unchanged: actual Joint first coverage is
   2.027s, D2+27.4ms; later F14 coverage has no gap. Its later own F16 view is
   visible when selected F14 applies. It remains separate actual executions,
   not an event-matched counterfactual or a claim that Joint is faster here.

## Main files and printing sizes

| Main role | PDF/SVG basename | Final width×height |
|---|---|---|
| Actual same-input two-arm case | `timely_interval_comparison` |7.125×2.75in|
| Eligibility/authority/support mechanism | `coordination_protocol` |7.125×3.00in|
| Factorial and native content effects | `composition_and_content` |7.125×3.40in|

The three companions (`service_region`, `factorial_cohorts_detail`,
`timely_full_interval_case`) are also regenerated without value changes.
All visible source labels remain≥8.5pt, all PDF fonts embedded, no Type3,
SVG text editable. The two changed color/gray PDF previews were actually
viewed; the four unchanged color/gray previews are byte-identical to v2
images already actually viewed. Final paper scaling/page review remains
Root's integration task.

## Verification

- Formal Root current-source gate passed35 files before rendering.
- Formal v3 replot exit0 and numeric/vector gate PASS; controls/source and all26
  pinned inputs remained matched before/after. Zero new NN/model calls.
- Comparison JSON is exactly the v1 actual-analysis output (SHA
  `7df3c385a14c8842f745a66c8fb4f3635fee7cd916aad6d1e23af7cfdc80fd94`).
- Main matrix/native numeric JSON and all48 plotted-value JSON are
  byte-identical to v2. No counts, offered denominators or categories changed.
- Both color and grayscale Fig1 images are byte-identical to v2. The full
  original53 v2 output files, including its gate, match their protected hashes.
- V4 manuscript/source/PDF/ZIP25 protected files remain unchanged.

Final figure QA: `FIGURE_QA_v3.json`. Detailed data/caption scope remains in
the prior map, except that its v2 “Unknown: wait” explanation is superseded by
the explicit new in-figure wording above. The original plot tick failure in
v1 stays failed, separately from the successful actual interval extraction
and current text-only replot.
