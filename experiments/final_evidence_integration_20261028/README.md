# RevTrace — final bounded research integration (2026-10-28)

This package closes the evidence integration requested after the context,
finite-wait, native-loop and trusted-render dependency studies. It does not
rename their negative decisions, edit the paper or start another GPU matrix.

Read [FINAL_REPORT.zh.md](FINAL_REPORT.zh.md), then:

1. [Seven deliverables / contribution map](SEVEN_DELIVERABLES.md).
2. [Paid work and batching](PAID_WORK_RESULTS.md).
3. [Native actual-input / generation / task / writeback](NATIVE_CAUSAL_CHAIN.md).
4. [Related-work and publication-status audit](RELATED_WORK_AUDIT.md).
5. [Scope and stopping decisions](DECISIONS.json).

## Actual source identities (archive HEAD is not execution source)

| Work | Actual full commit | Manifest / records |
|---|---|---|
|Primary native and paid-work read-only reconstruction|ca5e04bbb513b703f9aa46d03c6f6fcd08315909|SOURCE_v2.json; records_v2|
|Second implementation over archived raw, no production admission imports|53246842be8f51dcf4dc1aba488dda40a004bbc0|SOURCE_v5.json; independent_check_v2 and archive_layout_check_v1; resolves local and public archive update-directory layouts|
|Public DOI metadata lookup|d60f076b4c9b73fda23f5393a293cacd9be24d23|SOURCE_v3.json; related_metadata_v1|
|Current live runtime / last four cold trials|040fcc95f4cd3bbc4d918bc1dd4502b0b768990c|../trusted_render_dependency_20261028/runtime/SOURCE_v17.json in GitHub archive|
|Existing formal execution|996430d24d110facb242b352ba69c2f42f26e69c|../input_freeze_20261027/formal/FORMAL_SOURCE_v5.json|

Each analysis version has a standalone source tar, Git bundle, complete byte
manifest and CPU gate. v1 is a retained preliminary successful recount, not a
failed GPU run. v2 adds explicit prior validity and next-write consumption
edges; v3 adds public metadata; v4 adds a separately implemented raw recount;
v5 adds portable resolution of the public archive's historical update paths.
Each local version passed six CPU fixtures; these are repeated tests, not
independent scientific samples. Zero GPU inference was launched by this package.

## Verification and raw locations

The original GPU raw remains under the designated 8 TB disk's
`results/revtrace/freeze_boundary_20261027/` and
`results/revtrace/trusted_render_dependency_20261028/`.
The CPU analysis raw is under `results/revtrace/final_evidence_integration_20261028/`.
`records_v2/RAW_INDEX.json` authenticates copied analysis results. Original input
member hashes are repeated in the analysis outputs and second-check result;
their public compressed raw cuts remain in the context package.

Portable read-only recount from a complete repository archive:

```text
python -B source/independent_check.py --repo <repository-root> --source-manifest SOURCE_v5.json --out <new-result-directory>
```

For source-strict reproduction, materialize the matching bundle/tar into a
separate clean Git checkout before running. Do not pretend an evidence-archive
HEAD is the independently frozen analysis commit. Existing result directories
are immutable. The package manifest excludes itself and local Git/test caches.
