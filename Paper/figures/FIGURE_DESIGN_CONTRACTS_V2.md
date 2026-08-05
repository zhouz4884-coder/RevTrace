# RevTrace submission-figure contracts (F3--F5)

## F3 -- authority granularity and latency scope

- **Conclusion:** authority granularity creates a measurable
  speed--quality--energy frontier; Coarse-DGFT is the throughput point while
  SG remains a distinct same-granularity certification point.
- **Hero evidence:** same-workload Pareto map, with protocol color, model
  marker, and measured service energy encoded independently.
- **Scope safeguard:** SG state-entry latency and DGFT display/segment-commit
  latency use separate axes. The 2 s SG deadline is not transferred to the
  DGFT segment-commit scope.
- **Headline evidence:** Coarse-DGFT reaches 6.88x/6.06x wall-clock speedup on
  0.6B/1.7B under the frozen R10 contract.

## F4 -- cross-family production evidence

- **Conclusion:** one runtime invariant transfers across two structurally
  different feedback adapters, while performance magnitudes remain
  family- and contract-specific.
- **Archetype:** a 3-metric by 2-family evidence matrix. Qwen uses exact-value
  lollipops; Whisper shows every production cell, arrival type, IQR, and
  median.
- **Headline evidence:** Qwen peaks at 6.88x wall-clock, 3.44x GPU-normalized,
  and 59.81% service-energy reduction. Whisper passes 16/16 production cells
  with 2.84x median wall-clock speedup and 31.13% median energy reduction.
- **Boundary:** the Qwen R10 and Whisper R9.E baselines remain visibly
  separated; no pooled cross-contract estimator is drawn.

## F5 -- per-family quality contracts

- **Conclusion:** Qwen stays bounded relative to its independent canonical
  path, while Whisper improves over unprotected feedback in both cohorts.
- **Qwen evidence:** all 16 session-level edit rates per cell, exact-session
  counts, and empirical P95 diamonds.
- **Whisper evidence:** six cohort-specific means and one-sided 95% upper
  bounds; all upper bounds remain below zero.
- **Boundary:** the two panels answer different quality questions and are
  never pooled.

## Export and QA contract

- Python/matplotlib is the exclusive rendering backend.
- PDF and SVG are vector outputs; SVG text remains editable and contains no
  embedded raster image.
- PNG is exported at 300 dpi; TIFF is exported at 600 dpi.
- Panel-title bounding boxes are checked automatically before export.
- Machine-readable export QA is written to `FIGURE_QA_V2.json`.
