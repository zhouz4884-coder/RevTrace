# Fixed two-client interference opportunity gate

This independent source observes the original final NN59. It does not implement
Canonical-priority admission, quotas, budgets, phase search, new cancellation,
neural reset, or a new C/U. The external 59-file checkout stays clean and byte
matched at `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`.

It derives from the complete 18-file a13 harness, commit
`a13fa0a335529dc188f7e738877a3acd027ce4a7`, manifest SHA256
`8cadffbfe9ffcc1eb3efdf5e2702e7afbc2ec932158c12dd197d6f0bdc334934`.
`UPSTREAM_DERIVATION.json` records copied byte hashes; the upstream README is
preserved as `UPSTREAM_README.md`. Launch this experiment only through
`run_interference_campaign.py`. Development preparation is not a formal freeze.

## Contract and pre-result root revision

A sends original S0908/W0369 then S0913/W0313; B sends S0905/W0246 then
S0916/W0463. Each sid/audio is used once with original reference/file EOS.
Original FP32, C/U, guard, 500 ms cadence, EOS tail, all-offered D2/C8 and
max-ahead are unchanged. Owner sid order is A0,A1,B0,B1. Each client advances
only after its own actual canonical Consumer EOS; two model PIDs stay resident.

B's first origin is exactly A's first origin + **2.0 s**. Root chose this before
any double-client output so A can establish a speculative pipeline before a new
client's necessary work arrives. Late polling retains the planned origin and
charges delay. Each client's next origin is its actual admission after own EOS.
No aliases, artificial gaps, transcript-dependent endpoints or global-clock
shortcut are permitted.

The earlier decision note suggested 250 ms, metadata sid order and shared credit
gain. **Root changed all three before double-client execution**: fixed2s,
A-first sid order, no shared-credit-gain requirement. This avoids missing the
case where measured standalone speculation helps but shared speculation harms.
The frozen root gate requires each repetition to have:

- Full exact state/C/IDs, clocks, actual EOS, physical job/PID and source gates.
- Conservative: zero C8 frontier misses on all four requests.
- AlwaysFull: an actual A speculative dispatch while B's missing Canonical was
  already ready. A proposal alone does not count.
- B worst-request C99 regression at least `max(1 s, 20% of Conservative C99)`,
  **or** at least four additional B C8 frontier misses. No pooling of repeats.

Report all A/B D2/C8, EOS/non-EOS misses, credit, both-board energy, actual held
views and protected authority. Standalone benefit belongs to separate paired32
real data. GO identifies a bounded opportunity, not a scheduler improvement,
capacity/fairness guarantee or causality of all latency. Nonpreemptive residual
work can still delay later arrivals.

## Observation and audit

`interference_supervisor.py` derives from a13's outer Supervisor; `TwoClients`
implements independent releases. Core eligibility, C/U, persistence, authority,
views and physical lifecycle stay original. Recovery is disabled; a failed
worker/Owner remains a failed trial, followed by bounded cleanup.

`interference_observer.py` wraps original methods without changing source. It
returns the exact original proposal object and register result. It never calls
the scheduler for another sid. Both policies get the same registration snapshot
logging; its overhead is part of this new condition, not assumed zero.
Accepted frontiers are sampled before the decision timestamp. Complete current
cuts and live/completed owned inputs are recorded. The audit binds each snapshot
to actual raw dispatch UID/slot/incarnation/source/whole input/end, actual worker
terminal/begin/end, installed Canonical/durable facts and prior ingress.
Missing execution, future accepted input and stolen leases fail. This trusted
read-only snapshot is not hardware attestation/full runtime refinement.

`interference_analysis.py` checks every 500 ms/EOS offer, independent client
ledger, exact legal reference, actual canonical EOS, continuous PIDs and durable
Consumer authority. Per-request clocks drive endpoint metrics. All actual
last-held views are retained. `audit_interference.py` recounts completed raw
data into a distinct output after verifying NN59 and harness manifests.

## CPU controls and root-owned launch

```text
python -B -m unittest -v test_interference test_interference_identity test_interference_prerequisites test_buffer_reaudit_prerequisite test_interference_supervisor test_controls test_supervisor_cleanup
```

`REVTRACE_NN_SOURCE` must point at exact original4f on Linux for the required
real-coordinator CPU differential. Windows defaults to current local source_v2.
Set `REVTRACE_RESIDENT_PLAN` on Linux to the existing `RESIDENT4_v2_FROZEN.json`
with its sibling `resident4_v2_configs` directory for the prospective plan control.
`REVTRACE_CPU_SCRATCH` controls tiny synthetic temporaries; use B on the host.
Actual-wrapper controls use `REVTRACE_STRENGTHENING_EVIDENCE` for the current
bounded local packet, or the existing original/posthoc result paths on B on
Linux. Stage the unchanged `INPUT_INDEX_v2.json` beside the existing frozen
posthoc config on the host; this is an input-freeze index, not an execution PASS.
These controls never import Torch or launch GPU work and prove no performance.
Additionally run the copied Linux process-group cleanup control on Linux; its
CUDA response is synthetic, not actual CUDA release.

Formal freeze **waits for root review**. After review commit final source, use
`freeze_interference_source.py --out <outside-source packages>`, import full
commit at root, select CURRENT and execute no-argument preflight. Do not relabel
4f/a13. `build_interference_plan.py` then writes four prospective configs/plan:

```text
python -B build_interference_plan.py --resident-plan RESIDENT4_v2_FROZEN.json --manifest INTERFERENCE_SOURCE_v1.json --out <new bounded inputs> --remote-source <B source> --remote-manifest <B manifest> --remote-inputs <B inputs> --raw-root <B raw>
```

It launches no model. All models/audio/cache/power/raw remain on B. The fixed
queue is Conservative r0, AlwaysFull r0, AlwaysFull r1, Conservative r1 with GPU
assignment rotated. A failed first pair stops at two, retaining two unrun cells.
Maximum actual trials is four; existing outputs cannot be overwritten/resumed.

Root PRELAUNCH retains a13's root/asset/exclusive-GPU receipts and adds:

```json
{
  "prior_scope_completion": {
    "paired32_summary": {"path": "<B actual SUMMARY>", "sha256": "<hash>"},
    "resident4_summary": {"path": "<B actual SUMMARY>", "sha256": "<hash>"},
    "buffer4_reaudit": {
      "input_index": {"path": "<B INPUT_INDEX_v2.json>", "sha256": "<hash>"},
      "frozen_config": {"path": "<B original frozen posthoc config>", "sha256": "<hash>"},
      "formal_cpu_gate": {"path": "<B formal reader31 GATE>", "sha256": "<hash>"},
      "aggregate_gate": {"path": "<B b867 posthoc GATE>", "sha256": "<hash>"},
      "aggregate_summary": {"path": "<B b867 posthoc SUMMARY>", "sha256": "<hash>"},
      "run_record": {"path": "<B b867 posthoc RUN_RECORD>", "sha256": "<hash>"},
      "original_compound_gate": {"path": "<B original4eb failed GATE>", "sha256": "<hash>"},
      "original_compound_summary": {"path": "<B original4eb failed SUMMARY>", "sha256": "<hash>"},
      "cases": [
        {
          "reaudit": {"path": "<B CID_REAUDIT.json>", "sha256": "<hash>"},
          "raw_before": {"path": "<B CID_RAW_BEFORE.json>", "sha256": "<hash>"},
          "raw_after": {"path": "<B CID_RAW_AFTER.json>", "sha256": "<hash>"}
        }
      ]
    }
  }
}
```

The `cases` array must contain all four distinct cases. Root can generate these
read-only bindings with `buffer_reaudit_prerequisite.collect_receipts()` using
the frozen config, input-index and formal31 gate paths.

Requires actual paired32 completion and both resident repeats' four complete
task/reference/clock/PID requests with the measured strong E2E opportunity. The
real resident 7/8 original D2/C8 passes and all misses remain unchanged; see
`PREREQ_ROOT_CLARIFICATION_20261031.md` for Root's clarification before any new
probe output. This is not resident SLO invariance or expected probe success.

Buffer completion consumes b867's separate zero-NN wrappers and nested original
NN mechanisms. The original4eb buffer FAIL, CLI exit1, watchdog FAIL and compound
NO_GO must remain failed with the known receipt-reader reason. Formal31/source/
config/index/aggregate/per-case hashes, original task/reference PASS and complete
raw/watchdog before-after/current bytes are checked. A wrapper PASS cannot hide
an actual task/protocol/physical failure. Neither synthetic fixture controls nor
the old four top-level mechanism PASS labels qualify alone.
Complete controller/a13/NN59 manifests,
configs, environment, assets, actual READY FP32/allocator and GPU availability
are rechecked before NN.

```text
python -B run_interference_campaign.py --plan INTERFERENCE_OPPORTUNITY4_v1_FROZEN.json --manifest INTERFERENCE_SOURCE_v1.json --prelaunch PRELAUNCH.json --out <exact frozen B raw root>
```

Each cell has a 720 s outer watchdog and separately recorded 40 s failure-cleanup
deadline/per-query timeouts. Failed/uncertain group or CUDA release remains FAIL
and stops the queue. a13 PID-generation/session/descendant cleanup is reused.
Useful-certified-EOS and externally confirmed physical-drain board-energy
windows are retained separately. GO alone does not authorize a Canon-first fork.
