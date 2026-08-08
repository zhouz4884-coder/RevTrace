# FGCS submission-format audit

Source: Elsevier, *Future Generation Computer Systems -- Guide for Authors*,
checked 2026-08-08:
https://www.sciencedirect.com/journal/future-generation-computer-systems/publish/guide-for-authors

## Automatic checks

| Requirement | Current state | Decision |
|---|---:|---|
| Full-length article, strict double-column single-spaced limit | 18 pages including figures, tables, and references | PASS |
| Abstract | 241 words (limit 250) | PASS |
| Keywords | 6 (required 6--10) | PASS |
| Highlights | 5 bullets; longest 78 characters (limit 85) | PASS |
| Editable manuscript source | LaTeX sources, editable tables, SVG figures | PASS |
| Figure/table captions | Included in manuscript source | PASS |
| Numbered sections and cross-references | Enabled | PASS |
| Generative-AI preparation declaration | Included before references | PASS |
| Competing-interest, CRediT, acknowledgments, data availability | Included | PASS |
| Embedded Type 3 fonts | None found | PASS |
| Undefined references/citations and overfull boxes | None found | PASS |

## Author/submission-system actions

- **AUTHOR_INPUT_NEEDED:** final Figures 1, 2, and 6 must replace the current
  placeholders before submission. Their source sections were deliberately not
  changed during the performance-evidence revision.
- **AUTHOR_INPUT_NEEDED:** verify that the corresponding author's ORCID record
  is public/visible as required by FGCS and enter it in the submission system.
- **AUTHOR_INPUT_NEEDED:** provide the corresponding author's telephone number
  in the submission metadata/title-page package if requested by the portal.
- **AUTHOR_ACTION:** the manuscript states that the RevTrace repository is
  public, but an unauthenticated check currently returns HTTP 404. Make the
  repository or the frozen archival release publicly resolvable before
  submission, or revise the data-availability statement to match the actual
  access policy.
- **AUTHOR_ACTION:** upload the editable `highlights.txt` separately and retain
  the 18-page `[5p]` manuscript format.

## Integration decision

The page-limit repair did not shrink fonts or remove scientific evidence. It
moved the closure-repair chronology out of the manuscript narrative and
removed duplicate URL rendering where an arXiv identifier or complete venue
citation already resolves the source. The causal result, DGFT theory,
transaction validation, cross-family evidence, normal-load comparison,
flip-rich stress test, repeated V100 capacity result, and negative boundaries
remain in the main paper.
