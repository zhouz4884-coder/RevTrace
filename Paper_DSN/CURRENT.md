# Current RevTrace DSN manuscript — 2026-10-30

- [Complete manuscript PDF](revisions/20261030_dsn2027_release_v1/main.pdf)
- [Main LaTeX source](revisions/20261030_dsn2027_release_v1/main.tex)
- [Audited anonymous source package](revisions/20261030_dsn2027_release_v1/RevTrace_DSN2027_anonymous_source_v1.zip)
- [Research decisions and final results](../experiments/dsn_manuscript_update_20261028/FINAL_RESEARCH_REPORT_20261030.zh.md)
- [Source, PDF, package and all-page QA record](../experiments/dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261030_v1.json)

Title: **RevTrace: Preserving Valid Progress across Trusted Feedback Revisions**

11 technical pages plus one references-only page; 142-word abstract; 19 cited references; three figures and three tables.
All twelve pages visually reviewed. All23 fonts embedded, no Type3, no undefined references or overfull boxes.
The package contains exactly the reachable manuscript sources, figures, selected bibliography, provenance and PDF; build logs, local QA files, audio and models are excluded.

The prior independent native confirmation retains its actual bdfa source: four speakers,16 runs,272 transitions, whole-run passes0/8→8/8.
The new4f source adds28 short fault/regression trials and8 sustained-state trials:3976 selected transitions pass complete original-reference and independent actual-call/Consumer checks.
Ninety compatible-ahead applications preserve their views;1118 necessary incompatible withdrawals remain allowed. Four consumed ASR views survive producer exit/fencing until legitimate reconciliation.
The new normal Full-call result passes1/2 fresh trials; the other misses D2 only at EOS. Owner cold recovery misses original deadlines.
All8 constructed no-VAD long trials fail D2/C8 and have severe original-task CER degradation. They establish state/history stress coverage, not useful continuous ASR or an energy advantage. Full completed-buffer installation across producer death was not observed.

The20261008 and20261029 revisions are preserved. Actual NN source4f, analysis sources and evidence-archive commits are recorded separately.
This is a complete research manuscript release; conference submission has not been performed.
