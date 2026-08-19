# Paper workspace

Current locally compiled draft: `main.pdf` (mixed-width layout candidate,
elsarticle `[5p]` camera-style preview, 17 pages including references). The
full-length article stays below FGCS's strict 18-page limit; closure-repair history stays
in the public audit rather than expanding the scientific narrative. This
revision adds a normal-load c16 comparison
against MarginGate- and LLM-42-style revision adaptations, makes the authority
interface explicitly precision-independent, and maps the single-node ledger
to a bounded multi-node realization without claiming measured multi-node
scaling. It retains the independent 84-cell 8xV100 scale-out contract and adds
a 30-cell, three-repeat headline matrix that separates c64 display-SLO capacity
from certified-segment commit latency, keeps c128 as the measured display
overload boundary, and includes an authority-heavy allocation sensitivity.
It also retains proposer/authority bottleneck attribution and the
250,000-attempt CPU transaction-state fuzz. Post-commit repairs (2026-08-06):
the `[times]`
class option reintroduced Type 3 fonts and was replaced by
`newtxtext`/`newtxmath` (zero Type 3 verified), the 1.7B Coarse/Hybrid
P95-edit boundary (3.18%, 8/16 exact sessions) is now visible in the H7
prose and the F7 figure caption wherever their speedups are reported, and the abstract/highlights restore the
480 SG / 320 DGFT scope split on the 800 Qwen revision events. The
point-by-point author audit is in
`submission/REVIEW_TRIAGE_2026-08-05.md`.

Manuscript: **RevTrace: Dual-Granularity Feedback Transactions for
State-Certified Streaming ASR Serving** (FGCS first; elsarticle, numbered
references).

Writing plan: `docs/reports/revtrace_paper_outline_v2.md`
(`OUTLINE_V2_THEORY_GUIDED`). Evidence map:
`docs/reports/revtrace_dgft_paper_blueprint.md`. No manuscript claim may
exceed `docs/CLAIM_BOUNDARIES.md`.

## Layout

- `main.tex` — preamble, abstract (DRAFT v0), section inputs, bibliography.
- `sections/01..09_*.tex` — one file per section (outline v2 structure).
- `tables/t1..t8_*.tex` — T1 claim contracts, T2 same-workload ladder,
  T3 production summary, T5 guarantee taxonomy, and T8 normal-load c16
  comparison of
  revision-level MarginGate/LLM-42 adaptations and RevTrace configurations.
  T4 (quality contracts) and T6 (flip-rich revision adaptations) are retained
  as auditable source tables but are not `\input` in the paper because their
  values are already carried by Figure F6/H5 and the H6 stress-test prose;
  omitting the duplicate floats prevents adjacent table strips.
  T7 (`t7_v100_scaling.tex`) is retained as source provenance for the
  independent 8xV100 contract but is not `\input` in the paper: its numbers
  are carried by Figure F7 and the H7 prose. Float convention: the retained
  wide tables T2/T3 use `table*[b]` (via `stfloats`) so the float strip alternates
  top/bottom instead of stacking two floats at one page top.
  All numbers come from audited results (see captions for sources).
- `figures/` — figure PDFs. The paper uses a mixed-width evidence hierarchy:
  the authority-frontier and quality-contract composites are single-column,
  while the motivation, architecture, cross-family production, and V100
  scale-out summaries remain double-column hero figures. Figures 1--3 are
  editable Visio redraws under `figures/visio/`: each directory contains the
  staged senior-author source, semantic `scene.json`, editable `.vsdx`, SVG,
  and PNG review export. Their submission PDFs are
  `f1_motivation_visio.pdf`, `f2_architecture_visio.pdf`, and
  `f3_certification_visio.pdf`. The quantitative reproducible sources are
  `f3_authority_frontier_column.pdf`, F5 `f4_production.pdf`,
  F6 `f5_quality_column.pdf`, and F7 `f7_v100_dual_plane.pdf` (PNG previews
  alongside). Regenerate the wide production source with
  `python Paper/scripts/plot_paper_figures_v2.py` and the two single-column
  composites with `python Paper/scripts/plot_single_column_figures.py`. The refined submission
  renderer reads the frozen audited JSONs
  (`results/r10_qwen_cross_adapter/*`,
  `results/r9_dgft/FINAL_REPORT_ONLINE.json`) at runtime, so no plotted
  number is hardcoded. It exports editable SVG, PDF, 300 dpi PNG, 600 dpi
  TIFF, `figures/FIGURE_QA_V2.json`, and `figures/FIGURE_COLUMN_QA.json`;
  the original renderer is retained as
  provenance. Regenerate F7 with
  `python Paper/scripts/plot_v100_dual_plane.py`; it consumes the frozen
  V1--V4 summary and independently repeated V5 summary and writes its own
  source CSV and QA manifest. The Visio redraws intentionally correct three
  submission-facing risks in the original drafts: the authority interface is
  contract-specific rather than intrinsically FP32, only risk evidence (not a
  certificate) is non-authorizing, and Qwen/Whisper quality estimands remain
  separate.
- `refs.bib` — 49 entries, checked against primary indexes (arXiv API,
  OpenAlex, CrossRef) across 2026-08-03..06 (original 22 verified
  2026-08-03, 15 Related-Work additions 2026-08-04, the 2026 LLM-42 and
  MarginGate preprints re-verified against the arXiv API 2026-08-06).
  Voxtral Realtime is bound directly to its arXiv record because OpenAlex
  did not expose a usable arXiv identifier. Raw records are kept in
  `references/`.
- `elsarticle-num.bst` — vendored numbered bibliography style used by the
  reproducible local build. The local CTAN template bundle is intentionally
  excluded from version control because it is upstream material, not a
  RevTrace artifact.
- `lineno.sty` — vendored (a stale MiKTeX filename database made the tree
  copy invisible to pdflatex; run `initexmf --update-fndb` if packages seem
  missing). Line numbers are enabled via `\linenumbers` in `main.tex` for
  review copies; comment out for camera-ready.
- `submission/` — journal-submission companions: `highlights.txt` (5 items,
  each <=85 characters) and `title_page_revtrace.docx` (author block,
  corresponding author, acknowledgments, AI-use and COI statements, adapted
  from the provided title page).
- Author block in `main.tex` is filled and confirmed (Bin Zhou first,
  experiment design and overall execution; Jiyuan Miao second; Xi Cao
  corresponding, supervisor; Beijing University of Chemical Technology).
  CRediT statement and Data availability (public repository
  `https://github.com/zhouz4884-coder/RevTrace`) are filled in the end
  matter; the repository must be made publicly reachable before submission
  (it returned 404 when last checked while still private).

## Compile

Locally (TeX Live/MiKTeX): `pdflatex main && bibtex main && pdflatex main`
twice. Or upload this folder to Overleaf (elsarticle is built in; set
compiler to pdfLaTeX). `review` option gives double-spaced submission
format; switch to `\documentclass[3p]{elsarticle}` for camera-style preview.
This machine compiles the paper with MiKTeX via the explicit
`pdflatex -> bibtex -> pdflatex -> pdflatex` recipe; `latexmk` is not used
because the local MiKTeX wrapper requires a separate Perl installation.
Fonts: the preamble loads `\usepackage[T1]{fontenc}` plus
`newtxtext`/`newtxmath` (Times-style, full T1/AMS glyph coverage) so the
built PDF contains no Type 3 fonts (verified with `pdffonts`; TeX Gyre
Termes/NewTX embedded Type 1 only, plus CID TrueType fonts embedded by the
matplotlib figure PDFs). The invariant arrow is `\nRightarrow`; never use
`\not\Rightarrow`, and do not re-enable the legacy `[times]` class option —
its mathptm-era setup reintroduces Type 3 bitmap fallbacks for symbols and
accented bibliography names.

## Claim discipline reminders

- Denominator is 8/21 legal pairs (never 8/8); RAF 153 is measured on the
  6 persistent pairs.
- SG-path UCB (0.480%) never transfers to DGFT paths; quality estimands are
  per-family and never pooled; latency columns carry their scope labels.
- Zero-violation statements are exhaustive-trace validations, not
  probability-zero claims.
- The 8xV100/Transformers-eager contract is independent of the
  RTX3090/vLLM contract; report c64 as the 2 s display-SLO capacity and c128
  as the measured display overload boundary. Certified-segment commit latency
  is a separate estimand; never pool either contract's absolute timings.
- The V100 1.7B Coarse/Hybrid P95 final-edit boundary (3.18%, 8/16 exact
  sessions) must stay visible wherever their speedups are reported (H7
  prose, F7 caption).
- Preflight (10.7-11.1 s) is excluded from all service timing.
- Untouched-cohort sample unit: 40 long sessions per model, deterministically
  assembled from 214 previously unused source utterances. The statistical
  unit for bootstrap/averaging is the long session, not the utterance; never
  report n=214 as the cohort size.

## Theory/evidence calibration round (2026-08-04, frozen)

Concepts below are frozen; the three architecture figures F1/F2/F6 must be
drawn against these definitions, not earlier drafts.

- Feedback sub-state: `S_t = (S_t^x, H_t)` with `H_{t+1} = Φ(Y_t; H_t)`
  (Eq. 2) and `S_{t+1} = T(S_t, A_t, H_{t+1})` (Eq. 3). Ordinary serving's
  implicit assumption is Eq. 4 `H_{t+1} = Φ(Y_t^batch; H_t)`. Qwen `H_t` =
  rollback prefix; Whisper `H_t` = previous-text prompt. The boxed invariant
  (Eq. 5) is `Display(Y_t) ⇏ Authorize(Φ(Y_t; H_t))`.
- Certificate: `cert_j = Bind(sid_j, e_j, p_j, v_j, [f_j, f_{j+1}),
  h(Φ_j^a))` with `Φ_j^a = Φ(Y_j^a; H_{v_j})`; binds canonical projection
  digest + parent version + frontier + contract epoch/runtime; single-use.
  Theorem 3.1 states no uncertified fine projection can enter committed
  ancestry; Theorem 3.2 requires atomic commit (indivisible compare-and-swap
  of Definition 3.3 checks + installation).
- Assumption 2.1 (Local sensitivity) precedes the RAF recurrence: finite
  per-round constants in a neighbourhood of the canonical trajectory; no
  global Lipschitz claim.
- Proposition 3.7: end-to-end condition
  `T_service ≈ max(T_p, T^a) + T_repair` (Eq. 9), with the original
  authority-lane inequality retained as a simplified sufficient condition.
- H2 zero-violation claims are split by scope (Qwen FP32 preflight / DGFT
  online transaction trace / SG independent replay) and never pooled.
- §5 debugging history moved to Appendix A "Rejected realizations and
  measurement repairs".
- Table 5 (t5) is a 9-column taxonomy: display stability, feedback ancestry,
  canonical authority, stale rejection, statistical risk bound, preflight
  invariance, exhaustive transaction validation, semantic reference.
- Related Work rewritten into 8 paragraphs (37 refs): adds stateful/multi-
  turn serving, revision-generative/self-correcting models, speculative
  verification (Medusa/EAGLE/SpecInfer), transduction-streaming ASR, STM/
  transactional runtimes, reproducibility surveys.
- Break-even (Section 7) is now a definition, `N = ⌈T_preflight/ΔT⌉`, not a
  promised measured value.

## Pre-submission offline audits

The three paper audits are executable rather than prose-only:

```text
python scripts/audit_r9_coverage_replay.py \
  --manifest results/r9_dgft/online_closure/coverage-replay.json \
  --output results/r9_dgft/online_closure/coverage-replay.json
python scripts/audit_paper_submission.py
python scripts/audit_h6_normal_load.py
```

Audited outputs are frozen under `Paper/audits/`:

- `cjk_coverage_replay.json`: 2,050-segment legacy/current decision replay;
- `denominator_audit.json`: raw-pair recomputation and manuscript scan;
- `contract_inventory.json`: path/hash/digest binding for R9.E, R10, SG risk,
  Qwen quality, and Whisper quality;
- `REPORT.md`: human-readable audit summary.
- `h6_normal_load_v100.json`: direct recomputation of the ten normal-load
  c16 comparison cells, SLO/install checks, and RevTrace-to-adaptation ratios.

The Voxtral Realtime boundary now cites its own report,
arXiv:2602.11298 (first submitted 2026-02-11), rather than the 2025 Voxtral
main report.
