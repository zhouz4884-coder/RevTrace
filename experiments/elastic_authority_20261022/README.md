# RevTrace — Elastic Authority Granularity audit

Experiment `REVTRACE-ELASTIC-20261022`. **Final: NO-GO for a C2 Elastic algorithm upgrade.** The bounded prototype is safe in the audited histories but does not beat strong fixed/simple baselines under the frozen success rules. Original C1/C2/C3 are retained; the paper, title and abstract are unchanged.

Start with `FINAL_RESEARCH_REPORT.zh.md`, `C2_UPGRADE_DECISION.md`, `CLAIM_EVIDENCE_MATRIX.md`, then `GO_NO_GO.json`. All negative scouts and formal outcomes are retained.

## Scope and measured results

- 18 real dual-RTX3090 scouts +24 fresh formal runs (six policies×four repeats).
- Formal: same32 independent full English utterances/speakers,604.85 audio-s, controlled low→high→low replay. Repeats are not additional independent speakers; no production-arrival prevalence claim.
- Joint vs best fixed3: Goodput −4.17%,95% conditional CI [−20.92%,14.51%]; Commit P99 +45.31%; energy +9.58%.
- Joint vs Deadline-only: Goodput −10.13%,CI [−22.38%,−1.82%]; Commit P99 +27.06%; energy +8.02%.
- Quality noninferiority passes; all formal caps=0. Deadline's +6.62% point vs fixed is not significant (CI [−7.44%,27.90%]). All formal whole-run P99s miss2s/8s: partial Audio Goodput is not full SLO pass.
- 148 scoped CPU regressions;81 primitive/WAL sequences and324 synthetic transitions. CPU evidence is not GPU model/recovery evidence. Full historical pytest collection failed on19 unavailable legacy dependencies; log preserved.

Clock definitions: Display is actual FIFO consumer view-application completion minus the common frontier's audio-release time. Commit is the WAL-complete owner-state installation time minus that same frontier-release time; it is not the later consumer receipt of the canonical publication. Global wall includes arrivals and drain. No clock has been changed to improve the result.

## Evidence map and identities

`PROTOCOL.md` → mechanism/obligations → fixed16 space freeze → negative gate → one32 qualification freeze → minimal design freeze → statistical freeze → all formal outcomes. No tuning after formal results.

Runtime base `2a4b56bc5d8dcbf3884f03f8213f9c39101f59f8`; latest prior GitHub `af0920092abd25213378861a9a73bda17d7c2bc7`. Formal loaded root commit `998550ce8ce07dc9139a3453b0972e920d68606f`. `runtime/` is an exact loaded-root export, not a new measured revision. Its file hashes map to the original source manifests. Unchanged `dgft`,WAL,Worker,Render/continuity hashes are in `SOURCE_CHANGE_AUDIT.json`.

`sources/` keeps the three original measured source tarballs and Git history bundles unchanged. The Elastic tarball contains an unused nested static copy (117 files); this was not on the runtime import path and is not in the loaded-root export. The fixed tarball's generated manifest includes a stale self-entry; postflight records the exact old/current metadata hashes and verifies every other source and all model weights. These packaging defects are not silently erased. See failure history and `POSTFLIGHT.json`.

`BOUNDED_EVIDENCE.tar.gz` is a lossless bounded metadata/results archive, **not the complete raw GPU trace bank**. It includes all42 run configurations/provenance/results, freeze/gate/statistical records, CPU read-only audit reports, per-source quality, common-frontier/SLO-grid tables and the complete663-file raw index. Large event/Worker/consumer/power/WAL files are retained on the designated8TB disk.453 bounded original files or losslessly expanded CSVs were hash-checked on collection. `EVIDENCE_INDEX.json` maps all artifacts. No audio, weights, local credentials, manuscript PDF or manuscript source is uploaded in this release. No new software license is asserted.

Raw root (authorized server):
`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/elastic_20261022/`.
Each of `fixed_scout`, `stress_scout`, `formal` has per-cell config/provenance/raw results plus its journals. Environment/model/data hashes and exact commands are retained. All six formal strategies share the same protected execution configuration/resources; their declared selection policies differ in chi. No benchmark output splicing, relaxed authorization, new model algorithm, KV reuse, C1/C3 failure campaign or manuscript rewrite occurred.

## CPU-only replay / inspection

First verify the published `MANIFEST.json` SHA256 entries. Extract the bounded tarball into a `collected/` directory. `analysis/final_diagnostics.py` is a read-only table summary; placing it at the root or adjusting W reproduces the descriptive cost/prediction tables. Remote audit scripts under `analysis/` use the frozen8TB layout and raw index, not invented stand-in outputs.

For the exact148-test CPU scope, use `CPU_PROTOCOL_SCOPE.json` and the released `runtime` directory. The tests use a CPU fake executor and temporary WALs; they do not launch CUDA. From `runtime`, run the16 test files named in that JSON with `python -B -m pytest -q -p no:cacheprovider`. `src` import setup is provided by the frozen test configuration. `CPU_RELEASE_REPLAY.json` records the final exported-source replay. Do not run the entire legacy tree and then call missing fixtures an Elastic model result.

GPU controller scripts are archived for provenance, **not automatically scheduled or executed**. Reproduction needs the separately provisioned exact model, tokenizer, LibriSpeech audio, environment and approved disk layout; these assets are not included. No more GPU jobs are queued. A new experiment is required before changing selection thresholds or claiming a repaired scheduler.

## Limits

One model/family, one controlled English source pool for formal comparison,4paired runs, fixed2s/8s primary deadlines and12-point supplementary grid. Conditional bootstrap resamples measured sources without rerunning contention. CPU WAL resumption does not extend the prior C3 GPU evidence. Admission/causal safety does not guarantee recognition completeness or deadline satisfaction. A NO-GO for these frozen rules does not prove no possible elastic policy can ever help.
