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

The index must also contain exactly two `plans` entries with `path`, `sha256`,
and `frozen_configs_dir`
for the actual frozen short28 and sustained8 plans. Every raw per-cell config
digest and complete cell-ID set are checked against those exact plans; counts
alone do not establish scope. The actual operator serializes a runtime config
echo with different bytes. Original frozen file bytes must match the exact plan;
the complete runtime JSON object must equal that frozen object, and the runtime
echo SHA must independently match both exporter and metric receipts. Both byte
digests remain separately named; no byte-equality claim is made.
`python -B -m unittest -v test_evidence_controls.py` runs five explicitly
synthetic, no-model development controls (separate config byte bindings,
ActualG binding, unknown endpoints, pinned-vs-unpinned bounds, and no invented
semantic zeros). V1 remains preserved; this narrow V2 compatibility change does
not modify the exporter, runtime, experiment configuration or original endpoints.

V3 is restricted to labels, comments and layout: the paper label is Full-call,
the native token axis is explicitly `Derived T+C` (not full prefix-inclusive L
or an observed forward length), and the recovery comment preserves the frozen
runtime's `model_end >= fault` boundary. Strict `>` remains a separately checked
property of actual timestamps. The 7.2-by-3-inch figure uses 8.5pt text to allow
paper-width scaling, legends outside data panels, and the same all-eight-row
selected-edge rug in panel a so that it does not obscure D/C delays. No input,
count, envelope, quantile, recovery selection, or numerical algorithm changes.

Before final use, commit/freeze this tool source independently, write its config,
environment and input manifest, run the targeted CPU controls, and pass the final
visual QA. No mock paper result is shipped by these tools.
