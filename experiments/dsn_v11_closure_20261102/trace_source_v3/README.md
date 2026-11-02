# Original normal32 event-path accounting (CPU only)

This V2 source is **authored, not executed** at handoff. Root must commit,
freeze a complete manifest, validate the actual CPU environment and Root CURRENT,
then run the nine controls and the complete analysis. No model, GPU, runtime,
manuscript, source pointer or original raw file is changed by this source.

## Identity and dependencies

- This analysis has its own clean checkout/full commit/complete manifest. It is
  not labelled with the service, checker or evidence-archive commit.
- Its only imported external helpers are original4f `feedback_contract` and
  `resilience_storage.scan(path, repair_tail=False)`. Before importing either,
  the complete clean **59-file** source is byte-verified against commit
  `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`, manifest SHA256
  `60ae549fcc98165a74e5a3dc420bf93418296099fa12b410572b15d281b2c457`.
- No runtime/model module is imported. The runner checks the module set before
  and after analysis and requires `CUDA_VISIBLE_DEVICES=''` and Python `-B`.
- All paths, input inventories, before/after SHA records, logs and results reside
  under `/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9`. No WAV is opened.

## Frozen inputs

Use Root's `RAW_INDEX_v1.json` directly: its `inputs` is a path-to-identity map;
its 32 `cells` have `cell_id/source_id/speaker_id/policy/repeat/raw_root`, absolute
or relative `owner_directories`, and `frames`. Its original service summary and
32 prior-C4 bindings are retained. The runner hashes every indexed input before
and after, including indexed files not otherwise needed for event interpretation.
The raw index itself is separately hash-bound before/after with the frozen
config, environment, manifests and prelaunch/Root receipt.

Each actual cell consumes only CONFIG/ORIGIN/SUMMARY/consumer/publications/
ingress/facts and the declared owner_e0 dispatch/worker_results/owner_events/
policy_audit logs. Normal32 is the only admitted campaign scope; no other fault,
load or no-reset banks are silently pooled. The actual NN SUMMARY, original a13
per-frontier archive and final report/C4 receipt are independently bound.

## External config (not inside the clean source tree)

```text
experiment_id: unique string
mode: controls | analysis
analysis_source:
  source_root, source_manifest, source_commit, source_manifest_sha256
actual_NN:
  source_root, source_manifest, source_commit, source_manifest_sha256
environment_record: absolute 8TB JSON path
environment_record_sha256: full SHA256
raw_index: {path: absolute frozen RAW_INDEX_v1.json, sha256: full SHA256}
verified_report: {path: original FINAL_REPORT/PAPER_DATA.json, bytes: N, sha256: SHA}
raw_base: absolute common parent containing all original32 cell raw_roots
lease_path: distinct exclusive file; parent already exists
raw_result_location: fresh output directory; parent already exists
aggregate_summary_location: output/SUMMARY.json
gate_decision_location: output/GATE.json
stdout_location, stderr_location: explicit 8TB outer-redirection files
minimum_free_bytes: e.g. 536870912
max_input_bytes: e.g. 268435456 (hard cap 512 MiB)
max_output_bytes: e.g. 16777216 (hard cap 32 MiB)
max_elapsed_seconds: e.g. 1800 (hard cap 3600)
```

The frozen environment JSON must equal the result of `current_environment()`
from `trace_common` under the actual intended `-B`, CPU-only environment. This
helper imports only the standard library. Its execution/freeze is Root's job.

Prelaunch is **separate from config**, avoiding a gate/config hash cycle:

```text
config_sha256: SHA of the final config bytes
root_noarg_preflight: absolute Root no-argument CURRENT receipt
root_noarg_preflight_sha256: SHA of that receipt
```

The Root receipt must identify this analysis source/manifest, with
`gate=SOURCE_IDENTITY_PASS`, `code_commit` and `manifest_sha256`. Config never
contains the Root receipt's hash. Controls and complete analysis have distinct
IDs, output/log/lease paths and prelaunch receipts. Both bind the same completed
32-cell raw index; controls do not open its actual raw inputs.

After freeze and Root authorization, the exact CLI is:

```text
CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 PYTHON -B SOURCE/run_trace.py \
  --config CONFIG.json --manifest SOURCE_MANIFEST.json \
  --prelaunch PRELAUNCH.json --out FRESH_OUTPUT
```

The runner first executes exactly nine synthetic controls. In analysis mode it
then accounts for all32 or preserves a FAIL; it never drops a bad run to create
a successful subset. Source identity and controls alone are not trace evidence.

## Outputs and semantics

- `JOB_TIMELINES.csv`: every dispatched original UID, with execution evidence
  separately marked (dispatch alone is not proof of execution). It retains
  original dispatch/worker begin/model start/ASR produced/model end/worker end/
  completion sent/durable-sync/install-log/actual-Consumer clocks, promotion and
  abandon/discard records, selection_changed, original parent/projection/full
  state comparisons and canonical-start parent-install-to-dispatch intervals.
- `ENDPOINTS.csv`: every original500ms/partial-EOS F; original offer and first
  actual D/C observations. D uses the first actual row with G>=F, at that row's
  own actual G. It is checked against the original a13 per-frontier record and
  original NN aggregates.
- `MISS_TIMELINES.csv`: all actual D2-missed frontiers, with the UID and exact
  publication that created the actual view. It therefore includes all missed
  frontiers in the failed fullcall cells, as well as conservative misses.
- `SOURCE_DEFICIT_LEDGER.{json,csv}`: fullcall missed-audio sum and share for each
  source, quality once per acoustic source and exact failed cell IDs. S0915's
  value/share is derived from the original rows; no target value or desired
  explanation is a pass condition.
- `PER_CELL.json`, bounded `SUMMARY.json`, `GATE.json`, prelaunch/final records,
  complete input before/after hashes, accessed-input and control hashes.

An actual private view binds its private_job to the original dispatch and an
actually applied private publication's final step. Complete start/end state,
UID and original target remain bound to that job's original ASR projection or
complete result. As in `SurvivorConsumer.snapshot`, the actual visible frontier
is zero when the whole text is empty; the internal tip frontier and owned target
remain nonzero and are separately emitted. Such a row supplies no audio coverage.
If a subsequent compatible
canonical application or shorter publication retains that same UID/G/text, the
origin publication remains the earlier applied one. Both current event and
view-origin publication IDs/received clocks are emitted. Canonical views with no
private_job bind through actual journal sequence/transition/publication receipt
to the original facts; an empty private path binds its explicit canonical root.

For a same-private-job path with recorded dispatch and ASR clocks only:

```text
D = dispatch - original_offer
  + ASR_produced - dispatch
  + actual_Consumer_observed - ASR_produced
```

The final term is also split at that view-origin publication's actual
`received_perf`. This is an observed path decomposition, not a counterfactual
cause or pure guard/IPC tax: correction, waiting, Owner work and transport may
all be inside those intervals. Canonical fallback and missing/nonmonotonic phase
clocks are explicitly inapplicable; missing intervals never become zero. Other
signed observed intervals remain signed. `canonical_install` timestamps are log
observations after Owner reconciliation, not an inferred exact atomic instant.
All model clocks are host brackets, not CUDA-kernel intervals.

The original all-offered denominator, EOS, original D2/C8 and linear P99 rule are
unchanged. Per-cell D/C, credit, original archive endpoints, policy totals and
source deficits must conserve. No new scheduler, cancellation policy, deadline
guarantee, counterfactual speed, parameter fitting or automatic repair is output.

## Nine meaningful synthetic controls

1. Actual G>F preserves the F's original offer and conserved same-job path.
2. Canonical fallback requires a durable fact and never fabricates private ASR.
3. Missing stage clocks remain NA; signed intervals are not clamped to zero.
4. Partial EOS/credit/all-offered and exact archived endpoints conserve.
5. Partial, repeated or speaker-overlapping32 scope fails closed.
6. Duplicate dispatch UIDs and foreign worker-incarnation receipts fail closed.
7. Complete state differs even with matching text or Python bool/int coercion;
   selection_changed and projection-state equality remain different quantities.
8. Retained views keep their true publication identity; synthetic source
   deficits and shares are derived with values unrelated to S0915's observed sum.
9. An empty-text private view at actual visible frontier0 still binds to its
   original nonzero tip/target and exact full-state receipt; it supplies zero
   displayed-audio credit. Wrong complete state, target or publication fails.

## V2 repair provenance

Frozen V1 `670229ff0f6fdcc3e59a44de664b337b9b27ee72` and its raw failed output
are preserved. Its eight formal controls passed, but the complete32 analysis
stopped because it equated every private tip's internal frontier with the
Consumer's visible frontier. Root-authorized read-only diagnosis checked the
original consumer/publication/dispatch bytes on the experiment disk (96 files,
before/after SHA matching). The first counterexample is cell
`SC_NEWTEST_BAC009S0914W0456_conservative_r0`, actual Consumer index2, publication3,
job `e0-j000000002`: full start frontier8000, original target/tip16000, empty
tip/observed text and actual visible frontier0. Sixteen cells' first V1 binding
failure had this same snapshot-normalization pattern. This is a diagnostic
coverage statement, not a new service result or natural-prevalence estimate.

V2 implements the existing snapshot rule, strengthens full end-state receipt
binding, emits internal tip frontier/digest separately, and adds cell/Consumer
row index/publication/job context to binding errors. All eight original controls
are unchanged; the ninth covers the observed case and rejection counterexamples.
No original clocks, endpoint rules, stored Consumer rows, runtime, source pointer
or paper are repaired. Root must freeze and execute V2 before claiming its
controls or complete accounting pass.


## V3 fixture-only correction

Frozen V2 controls correctly exposed aliasing in its new empty-view test: the
publication end and trusted ASR receipt referenced the same Python object, so
corrupting the former also corrupted the latter. Actual records are independently
decoded JSONL objects. V3 gives the ASR witness an independent deep copy before
fault injection. Analysis/runner/common and the original eight controls stay
byte-identical; V1/V2 sources and failed runs remain preserved. No runtime or
original trace is changed.
