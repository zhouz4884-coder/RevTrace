# Native actual-model pilot, before any large validation matrix

This file defines execution and decisions, not results. The parent must freeze
the entire source including these files, execute the fixed-version Linux CPU
tests without skips, prepare a full verified model asset manifest, and choose an
idle dual RTX3090 interval before invoking the controller.

## Model and objective

The first candidate is the installed original Qwen2.5-1.5B-Instruct (not the
vocab152064 modification). Its config is Qwen2ForCausalLM and the BF16 asset files
total3,087,467,144bytes. FP32 authority weights are approximately6.17GB before
runtime tensors; this is a file-size feasibility estimate, not a GPU success.
Qwen3-4B exists but changing model/template would require a new frozen provider
study and self-check. Seven-billion-parameter FP32 weights exceed one24GB3090's
budget and are not a silent substitute.

Two development task structures are runbook dependencies and constrained resource
planning. There are3 real read/write cycles; cycles1/2 consume previously admitted
memory through actual model input. They are planning-memory tasks, not commands
executed against real infrastructure. Four different validation instances are
already fixed by tasks.validation_tasks and remain unrun by this pilot.

## Provider controls and strong methods

1. Actual FP32 autoregressive generation twice under the same initial input,
   plus complete teacher-forced verification of the first full token/Stop result.
   Capture all actual input tensors and output tokens. If teacher-forcing or
   repeat equivalence fails, Strict receives NO-GO with the observed counterexample.
   That does not prevent Direct Standard/RevTrace from completing the native
   application work package under actual selected-result semantics.
2. Candidate-only: real FP16 Proposer onGPU0, no Authority loaded or claimed.
   This is a negative arm, with selection_authorized=false. Canonical installation
   in this arm must remain an observable unauthorized-admission counterexample.
3. Direct Standard: real FP32 Authority onGPU1 plus complete SQL/OCC/receipt checks.
4. Direct RevTrace: exactly the same selection/renderer plus actual composed kernel.
5. When the provider gate supports it: Strict Standard and Strict RevTrace each
   use actual FP16 Proposer GPU0 and full correct-context FP32 verification onGPU1,
   with real FP32 fallback after rejection. Neither receives a free heterogeneous
   batch or an assumed-equivalent autoregressive result.

Each mode loads only models that it needs. Equal resource entitlement is not a
requirement to load or execute an unused Proposer for Direct. The same physical
GPU0/1 power sampler covers the full cell window, including idle-device power,
mode-required cold loads, asset validation, native/SQL waits and retries.

The coherent condition replaces only cycle0's low-trust return with frozen JSON;
later cycles call the actual model without reinjection. The checker records both
the original GPU-generated tokens and the externally replaced tokens. Direct
does not consume the candidate at all: its coherent-labelled twin is a repeated
no-exposure control, not evidence that Direct rejected an observed corruption.

## Explicit stages and denominators

`--stage smoke` runs at most10 clean cells: two families times five methods.
If Strict is NO-GO, four planned Strict entries are explicitly skipped with that
gate and the six core cells still run. The controller returns after smoke; it
never automatically queues the full development matrix.

Only a later explicit `--stage development` call with the passed SMOKE_GATE may
reuse the same frozen run and extend it to clean/coherent 脳 two families 脳 five
methods 脳 two repeats, plus four clean Direct protected crash/resume cells.
That is44 entries with Strict, or28 actual runs plus16 NO-GO entries without it.
Existing complete smoke cells are reused by exact identity. Partial or failed
cells require diagnosis; the controller never silently reruns them.

The crash occurs after application SQLite commits and before the native task
returns. The recovery process rotates owner epoch, obtains the exact old receipt
and restores the actual persisted history. A model failure before commit is
reported as a fault point not reached, not as a crash test success.

All offered cycles, unfulfilled outputs, rejected writes, fallback calls and fresh
retries remain counted. Execution-finished does not assert all cycles succeeded.
Protocol safety, current-output validity, current-step quality, invalid-history
repair and the separate offline global objective bound are reported independently.
Clean model errors remain in the paired-trajectory comparison.

## Gates

- Before GPU: complete source hash match; full source commit; zero-failure,
  zero-skip fixed native CPU test report tied to this same source commit; exact
  package versions; full model manifest; two3090hardware and no competing process.
- Strict GO: actual same-input records, full Stop, exact repeat tokens and full
  self-verification in every development control. This is a bounded provider
  validation, not a universal numerical equivalence theorem.
- Protected native evidence: independent actual-ID/token/render/SQL/receipt audit,
  no protocol violation/unknown, observed multi-cycle consumption/writeback for
  both Direct protected methods in both families. Wrong task content selected by
  a trusted model remains a quality error, not an unauthorized write.
- Negative evidence: expected unauthorized admissions are explicitly labelled;
  any additional malformed-input, receipt, provenance or unknown evidence stops
  the pilot for diagnosis. A no-admission negative arm is not counted as an
  observed counterexample.
- Cost: actual power coverage and all failed/fallback work. Missing power or an
  unknown failing-call cost blocks the comparison; raw records stay available.
- Large independent validation: outside this pilot; requires parent review and
  a new frozen plan. No performance, novelty or publication conclusion is automatic.

## Required invocation

Use the actual pinned environment's python and provide concrete values for:

`native/pilot_controller.py --source-root S --source-manifest SOURCE.json
 --cpu-gate CPU_GATE.json --model-manifest MODEL_ASSETS.json
 --config S/native/PILOT_CONFIG.json --output R --stage smoke`

CPU_GATE.json must identify this source commit, statusPASS, the real JUnit XML
path and SHA256. The controller checks that native lifecycle cases actually ran
without skip. It records experiment ID, code/config/environment hashes, raw path,
summary path and decision path before first model execution. R must be on the
designated8TB freeze_boundary_20261027 result subtree.

Power, operator controls and application cells are separate evidence tiers.
Neither the self-check operator calls nor this protocol text count as application
model evidence before execution.
