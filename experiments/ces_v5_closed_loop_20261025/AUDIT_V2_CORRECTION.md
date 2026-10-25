# Audit-only correction after the closed-loop smoke

Date: 2026-10-25. Runtime remains frozen at
`e45c66475ba1173a98b49b8c9e62f3e8cb45b333`.
No new GPU execution or runtime modification is performed by this correction.

## 1. The false rejection

The original `audit_closed_helpers.py` required
`inherit_current_transition_model is False` for **every** released successor.
That disagreed with the frozen owner:

- The immediately next successor intentionally uses the actual current
  transition's model. Its flag is `True`, and its explicit Direct/Fallback
  probabilities must equal those of the actual current target context.
- A later successor's parent is genuinely unknown. Its flag is `False`, both
  transition probabilities are `None`, and it cannot inherit a root Verify
  witness.
- The deprecated single-rate field remains `None` for both layers.

The owner's setting is scheduling-prediction metadata, not an execution
permission. Allowing the correct first-layer flag does not admit a new Parent,
change a certificate, relax Trusted Render, or alter a WAL transition.

The earlier fast CPU owner tests did not create an actual released-child
observation. Therefore their passing outcome did not exercise this assertion.
The new test advances the **existing fake monotonic clock** before dispatch to
produce a real owner backlog with two released layers. This is explicitly a
CPU interleaving fixture, not model execution or a serving-performance result.

## 2. Minimal versioned correction

New `audit_closed_helpers_v2.py` checks first-layer `True` plus both explicit
rates against the actual context; later layers remain strictly `False/None`.
All other observation, current Parent, released audio, complete-plan, service
book, real dispatch, actual commit-retirement and conditional-chain checks
are retained.

`audit_closed_v2.py` imports that version. Its certificate/WAL/D1/row-receipt,
full token/stop verification, paid fallback, Consumer, energy, quality and
unfinished-scope checks are unchanged. No performance numerator or denominator
is repaired by changing data. `actual_model_calls` remains the sum of actual
recorded physical phases; re-auditing itself makes zero new GPU model calls.

Original frozen files remain byte-identical:

| Original file | SHA256 |
|---|---|
| `audit_closed.py` | `1e764d5bbc3e802018f7f584ac0972697221793231bec00b3dcf9326e8ea0a23` |
| `audit_closed_helpers.py` | `faeab42a3e81deaf1a67b4acce30aa1fe87fa466e58b78cfd509c8d6a3a94021` |

Versioned replacements:

| New file | SHA256 |
|---|---|
| `audit_closed_v2.py` | `9a1aee9814c57448d0de50258a0e18cc8bb3e7afc36d34317497d57b23e81c4c` |
| `audit_closed_helpers_v2.py` | `28a77bac902a5c9cd903d4e5ae6301a039ad6e2b947f59cdc79a52aed18a5b8e` |

## 3. Executed CPU correction controls

`AUDIT_CORRECTION_V2_CPU/SUMMARY.json` and four compressed CPU raw traces
preserve the exact false-rejection witness. For each of service-cost,
reserved-progress, inherit and causal, the actual owner produced four
observations with released successors, including two observations with two
layers. Original v1 rejected each trace at the wrong assertion; v2 accepted
the same trace, with six real CPU-owner installs and three physical-fake-worker
dispatches each. No neural model was called.

The correction tests also reject wrong first-layer inheritance, inconsistent
Direct/Fallback rates, inherited later unknown parents, and the old collapsed
single-rate field. Final test suite `test_audit_closed_v2.py` has 19 passing
tests, including full six-cell/72-file metadata-gate fixtures and rejection of
changed source, calibration, raw records, original STOP, matrix order, missing
cells, or changed auditor. These file-tree fixtures are clearly labelled CPU
metadata controls, not fabricated GPU measurements.

CPU correction summary SHA256:
`4b15e3393b63b8695005738e48f98a85cf7cd7d970829062bc7c2a2c26810b5c`.
The probe records its test-source hashes at generation time; later appended
gate-only test cases do not retroactively change that recorded identity.

## 4. Same-raw GPU re-audit and strict formal gate

The root controller reported completion of all original four performance and
two paid-Oracle smoke cells. Original v1 STOP/failures are retained. Its two
causal audit failures were the incorrect first-successor assertion, not a new
state-safety violation. The same four performance histories passed v2 with
165 recorded actual model calls; this is historical work, not new work by
the re-audit. The two Oracle histories were likewise re-audited without
rerunning GPU inference.

`finalize_smoke_reaudit_v2.py` records both v2 audit-summary hashes, hashes
all 72 original audit-input/WAL files, binds the original smoke freeze and
original STOP, and writes `smoke_REAUDITED_SUMMARY.json` once. The root reported
its SHA256 as
`bc18eef442d51568ad0fbe00ad0b813408a91a5c9fb9524384a8cb8573dc987d`.

`run_closed_stage_v2.py` accepts that summary only after checking same Runtime,
calibration, closed config, data/model identity, 4+2 complete v2 PASS audits,
raw hashes, preserved v1 terminal record, and the original **72 cells and
counterbalanced order unchanged**. A separate formal PLAN can enable approval
and add the re-audit basis, but cannot delete or reorder unfavorable units.
Formal remains an explicit new invocation; this document does not claim it
has completed or produced a benefit.

Final controller/gate set:

| File | SHA256 |
|---|---|
| `run_closed_stage_v2.py` | `f17378edf57831949b0a46d99bc7fc391631d724546028c3cc9f758b3f356538` |
| `smoke_reaudit_gate_v2.py` | `d55f84a1a54e6f1b4864571acf104e78848851b034b2ec6a37e78f05b370e1bb` |
| `finalize_smoke_reaudit_v2.py` | `2a3c3727e9546c0330fe16a702a8bb67fee9db9dc85f39a9edc6d01926915cc7` |

A temporary local v3 naming candidate was discarded before upload or any GPU
execution when direct byte hashes confirmed the executed remote v2 already
matched the intended gate. The executed controller is the `f17378...` version;
intermediate local freeze observations must be retained as superseded rather
than relabelled executed. No frozen Runtime file was edited in this process.
