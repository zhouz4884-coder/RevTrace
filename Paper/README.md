# Paper workspace

Current locally compiled review draft: `rev_v6.pdf`. This revision adds the
independent 84-cell 8xV100 scale-out contract, c64 SLO-valid capacity, c128
overload boundary, proposer/authority bottleneck attribution, and the
250,000-attempt CPU transaction-state fuzz. The point-by-point author audit is in
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
- `tables/t1..t7_*.tex` — T1 claim contracts, T2 same-workload ladder,
  T3 production summary, T4 quality contracts, T5 guarantee taxonomy, and
  T6 same-trace revision adaptations; T7 is the independent 8xV100
  single-node scale-out contract.
  All numbers come from audited results (see captions for sources).
- `figures/` — figure PDFs. The three data/performance figures are rendered
  and reproducible: F3 `f3_pareto_latency.pdf`, F4 `f4_production.pdf`,
  F5 `f5_quality.pdf` (PNG previews alongside). Regenerate with
  `python Paper/scripts/plot_paper_figures_v2.py` — the refined submission
  renderer reads the frozen audited JSONs
  (`results/r10_qwen_cross_adapter/*`,
  `results/r9_dgft/FINAL_REPORT_ONLINE.json`) at runtime, so no plotted
  number is hardcoded. It exports editable SVG, PDF, 300 dpi PNG, 600 dpi
  TIFF, and `figures/FIGURE_QA_V2.json`; the original renderer is retained as
  provenance. F1/F2/F6 (architecture/timeline/ladder diagrams)
  remain placeholders pending drawing requirements.
- `refs.bib` — 37 entries, checked against primary indexes (arXiv API,
  OpenAlex, CrossRef) on 2026-08-04 (original 22 verified 2026-08-03,
  15 Related-Work additions verified 2026-08-04). Voxtral Realtime is bound
  directly to its arXiv record because OpenAlex did not expose a usable
  arXiv identifier. Raw records are kept in `references/`.
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
Fonts: the preamble loads `\usepackage[T1]{fontenc}` + `\usepackage{lmodern}`
so the built PDF contains no Type 3 fonts (verified with `pdffonts`; Latin
Modern embedded Type 1 only, plus CID TrueType fonts embedded by the
matplotlib figure PDFs).

## Claim discipline reminders

- Denominator is 8/21 legal pairs (never 8/8); RAF 153 is measured on the
  6 persistent pairs.
- SG-path UCB (0.480%) never transfers to DGFT paths; quality estimands are
  per-family and never pooled; latency columns carry their scope labels.
- Zero-violation statements are exhaustive-trace validations, not
  probability-zero claims.
- The 8xV100/Transformers-eager contract is independent of the
  RTX3090/vLLM contract; report c64 as the 2 s-SLO capacity and c128 as the
  measured overload boundary, never pool their absolute timings.
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
```

Audited outputs are frozen under `Paper/audits/`:

- `cjk_coverage_replay.json`: 2,050-segment legacy/current decision replay;
- `denominator_audit.json`: raw-pair recomputation and manuscript scan;
- `contract_inventory.json`: path/hash/digest binding for R9.E, R10, SG risk,
  Qwen quality, and Whisper quality;
- `REPORT.md`: human-readable audit summary.

The Voxtral Realtime boundary now cites its own report,
arXiv:2602.11298 (first submitted 2026-02-11), rather than the 2025 Voxtral
main report.
