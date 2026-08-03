# Paper workspace

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
- `tables/t1..t5_*.tex` — T1 claim contracts, T2 same-workload ladder,
  T3 production summary, T4 quality contracts, T5 guarantee taxonomy.
  All numbers come from audited results (see captions for sources).
- `figures/` — figure PDFs (F1-F6; captions already written in the
  sections; placeholders render until the PDFs land).
- `refs.bib` — 22 entries, checked against the available primary indexes on
  2026-08-03; Voxtral Realtime is bound directly to its arXiv record because
  OpenAlex did not expose a usable arXiv identifier. Raw records are kept in
  `references/`.
- `elsarticle-num.bst` — vendored numbered bibliography style used by the
  reproducible local build. The local CTAN template bundle is intentionally
  excluded from version control because it is upstream material, not a
  RevTrace artifact.

## Compile

Locally (TeX Live/MiKTeX): `pdflatex main && bibtex main && pdflatex main`
twice. Or upload this folder to Overleaf (elsarticle is built in; set
compiler to pdfLaTeX). `review` option gives double-spaced submission
format; switch to `\documentclass[3p]{elsarticle}` for camera-style preview.
This machine compiles the paper with MiKTeX via the explicit
`pdflatex -> bibtex -> pdflatex -> pdflatex` recipe; `latexmk` is not used
because the local MiKTeX wrapper requires a separate Perl installation.

## Claim discipline reminders

- Denominator is 8/21 legal pairs (never 8/8); RAF 153 is measured on the
  6 persistent pairs.
- SG-path UCB (0.480%) never transfers to DGFT paths; quality estimands are
  per-family and never pooled; latency columns carry their scope labels.
- Zero-violation statements are exhaustive-trace validations, not
  probability-zero claims.
- Preflight (10.7-11.1 s) is excluded from all service timing.

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
