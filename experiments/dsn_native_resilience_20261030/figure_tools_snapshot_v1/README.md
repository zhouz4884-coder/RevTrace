# Independent bounded evidence and figure tools (development)

This directory is separate from neural execution source. It performs no model
calls, owns no experiment queue, and does not update source-identity pointers.
Read `EVIDENCE_CONTRACT.zh.md` before freezing or running the final analysis.

`export_bounded.py --runtime-source CLEAN_SOURCE --trial RAW_CELL --out NEW_DIR`
streams an already completed trial into bounded, text-free diagnostic series.
The existing checksum/sequence-validating WAL scanner is imported from the
explicit runtime source; it is called with `repair_tail=False`. The raw trial is
read only. No reference/oracle trace is substituted for a serving trace.

`render_evidence.py --index INDEX.json --out NEW_DIR` reads an explicit frozen
index of all 36 exported trial directories. Each entry has `bounded_dir`,
`cohort` (`short_main`, `short_regression`, or `sustained`), and `condition`.
An optional `semantic_audit` object may contain `illegal_installs` and
`legal_progress_wrong_rejections`, but those numbers require explicit independent
checker metadata (`checker_source_commit`, `checker_summary_sha256`, `scope`).
Absent independent audit remains unknown. The script exports machine tables,
LaTeX, and all-eight-run sustained diagnostics; it never infers semantic zeros
from runtime PASS strings. The exact index file is an analysis input, not a new
experiment plan.

The index must also contain exactly two `plans` entries with `path` and `sha256`
for the actual frozen short28 and sustained8 plans. Every raw per-cell config
digest and complete cell-ID set are checked against those exact plans; counts
alone do not establish scope. `python -B -m unittest -v test_evidence_controls.py`
runs four explicitly synthetic, no-model development controls (ActualG binding,
unknown endpoints, pinned-vs-unpinned bounds, and no invented semantic zeros).

Before final use, commit/freeze this tool source independently, write its config,
environment and input manifest, run the targeted CPU controls, and pass the final
visual QA. No mock paper result is shipped by these tools.
