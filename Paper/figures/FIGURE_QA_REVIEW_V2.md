# Manual figure QA review (F3--F5 v2)

Date: 2026-08-04

## Review scope

- Inspected all three 300 dpi PNG exports at original resolution.
- Recompiled the 26-page manuscript with
  `pdflatex -> bibtex -> pdflatex -> pdflatex`.
- Rendered and inspected the compiled manuscript pages containing F3--F5.
- Verified that the revised visual encodings preserve each contract boundary.

## Result

**PASS.** No figure title, subtitle, annotation, tick label, or legend collision
remains at the manuscript's actual `\linewidth` placement. Strong metrics are
visible without relying on the caption, and the figure text remains legible in
the compiled PDF.

## Figure-specific checks

- **F3:** SG state-entry latency and DGFT display/segment-commit latency are on
  separate axes. The 2 s deadline appears only in the SG scope. The Pareto
  panel preserves protocol color, model shape, and measured-energy area.
- **F4:** Qwen and Whisper retain separate contract columns. Every one of the
  16 Whisper production cells remains visible; arrival mode, median, and IQR
  are independently encoded. Qwen exact values are directly labeled.
- **F5:** Qwen and Whisper quality estimands remain unpooled. All Qwen session
  observations and exact-session counts are visible; all six Whisper cohort
  means and one-sided upper bounds remain readable.

## Non-figure build note

The manuscript compiles successfully. The existing BibTeX warning for the
empty `pages` field in `yu2022orca` is unrelated to F3--F5.
