# RevTrace FGCS pre-submission QA

## Passed gates

- Manuscript compiles with `pdflatex -> bibtex -> pdflatex -> pdflatex`.
- Manuscript length is 18 pages, including figures, tables, and references.
- Repository test suite: 258 passed.
- CJK-aware coverage replay: PASS with no recorded-decision change.
- Motivation denominator audit: PASS (8/21 with feedback, 0/21 without,
  six persistent pairs, maximum measured tail RAF 153).
- Contract inventory: PASS; SG, DGFT, V100, Qwen quality, and Whisper quality
  evidence remain separately scoped.
- Five highlights are present; every item is at most 85 characters.
- Abstract length is 241 words, below the 250-word ceiling.
- No blocking overfull float, undefined reference/citation, or Type 3 font was
  found in the compiled manuscript.
- Cover letter and title page were rendered through Microsoft Word and visually
  inspected; no clipping or overlap was observed.

## Tool warnings reviewed

- The bibliography checker reports missing `title` for `li2024eagle` and
  `zhang2026llm42`; both titles are present in `refs.bib` and use nested braces
  to preserve EAGLE/LLM capitalization. BibTeX compiles them successfully.
- Most bibliography warnings concern arXiv or conference records without
  journal volume/page/DOI fields; they are not missing-citation errors.
- The format checker reports macro/spacing heuristics around custom LaTeX
  commands. The final LaTeX build has no blocking formatting diagnostic.
- Corrected Figures 1--3 are each 2400x1792 pixels, exceed 350 effective ppi at
  their frozen widths, and pass the technical text and page-layout review.

## Remaining author actions

1. Fill suggested reviewers if Editorial Manager requests them.
2. Obtain final approval from all authors and inspect the generated submission
   PDF in Editorial Manager before clicking Submit.
