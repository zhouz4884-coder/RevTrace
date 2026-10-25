# Closed-loop stage controller and read-only audit

Status: code preparation and CPU tests only; this document does not indicate
that a remote/GPU process has started. Source, profile and parameter identity
must be frozen after all implementation gates pass.

## Frozen input schema

`PLAN.example.json` is deliberately **not runnable**: its CPU gate is false and
hash placeholders are not real evidence. A genuine `PLAN.json` must contain:

- the exact new Runtime commit and `SOURCE_MANIFEST.json` SHA256;
- calibration, closed-loop config, protocol, CPU gate and optional separate
  profile artifact hashes;
- model files and actual model hashes, source manifest and donor hashes;
- a new output path under the designated 8 TB disk;
- every cell's method/label, source pool, seed, concurrency, arrival, traffic,
  repeat and shared Proposer policy;
- separate small paid Oracle cells; Oracle work is not serving performance.

The controller verifies frozen source/configs before every fresh-process cell.
Model shards are hashed outside the serving clock, before the stage. All actual
audio files are independently checksum-validated by the runtime when loaded.
Every cell records its command/config/provenance, actual input/output history,
CPU/IO timing, physical receipts, full WAL and power samples.

The initial smoke is exactly four n8 serving cells (Fine/Causal × sync/staggered)
using the common `shared_progress` Proposer policy, plus two n4 Strict paid
Oracles (Clean/Mixed) using the original `ready` policy. Thus safety smoke covers
the actual new homogeneous-subset path without withholding it from Fine. It is an implementation/safety gate,
not a superiority result. A formal matrix is never automatically generated or
started. After a successful same-source smoke, the explicit formal PLAN may
freeze eight main labels × two arrivals × three repeats (48 diagnostic cells)
all using `ready`, preserving the original strongest Fine/Standard/cost points.
Four matched single-factor side-arms (Fine+shared_progress,
Standard+shared_progress, Cost+causal_joint, Causal+causal_joint) × two arrivals ×
three repeats add 24 cells, for an explicitly enumerated 72-cell proposal.
The template lists all units but remains unapproved with placeholder hashes.
Changes to source/calibration after smoke
require a new safety smoke study, not silent continuation.

Main methods must share GPU0 policy within matched source/arrival/traffic/repeat
groups. An optional joint-policy label (including a strong-reference arm such
as `cost_joint`) must be explicitly marked `side_arm` and differ only by the
declared Proposer policy from the same method's matched main arm. The candidate
value capability is not restricted to CES; Fine/Standard naturally lack a
verification-candidate reward. This prevents unreported DGFT-only executor
help. Clean/Mixed/High remain separately labelled
conditions and cannot be added by filtering favorable audio after seeing data.

## Invocation

On the authorized Linux host, after copying the frozen package to the new
project directory and checking resource ownership:

```text
python run_closed_stage.py --base <8TB-disk> --stage smoke --plan PLAN.json --validate-only
python run_closed_stage.py --base <8TB-disk> --stage smoke --plan PLAN.json
```

The first command verifies identities but runs no model. The second is an
explicit GPU action. Formal requires a separate `--stage formal` invocation,
its explicit approval field, a complete prior smoke audit and matching
implementation/calibration/config hashes. Existing stage markers, outputs or
STOP records are not overwritten or silently retried. Foreign GPU owners are
never killed. This controller is not an SSH launcher.

## Audit layers

`audit_closed.py` derives from the previous complete V5 audit; the old file is
untouched. It retains certificate replay, duplicate admission refusal, WAL
chain replay, complete Strict token/stop checks, paid fallback, Trusted Render,
immutable row receipts, physical lease separation, actual Consumer replay,
ACK-backed residual credit, quality and clipped two-card energy accounting.

`audit_closed_helpers.py` additionally:

1. Reconstructs the actual current Canonical Parent from initial states and
   actual install events; binds epoch/version/digest/frontiers/contract.
2. Checks released successor audio/deadlines/weights and finite Private CDFs;
   a model child contains no future Job, token or certificate.
3. Confirms a pending Private forecast references an actually enqueued,
   not-yet-received frozen job, rather than a completed/withdrawn cache entry.
4. Rechecks conditional completed-chain edges and target rendering from
   immutable observed results. A conditional preview is never authorization.
5. Replays the owner-local service book: observation/eligibility does not count
   as dispatch, each physical first batch ages obligations exactly once, and
   actual WAL installation retires them. Restart is a fresh scheduling scope.
6. Replays the deterministic CPU-only frozen decision on the observed inputs
   and cost calibration. This is algorithm replay, not GPU counterfactual
   re-execution or a proof of future performance.

The source feature schema recognizes the new `V5Target`-based modes. F2 labels,
future outputs and future Parent identities cannot enter the scheduling
observations. Source/model/profile hashes and physical input processing audits
remain separate evidence from arithmetic/model-output correctness.

`actual_model_calls` is summed from actual physical phase records, not a copied
zero. A complete `TOKEN_LIMIT_BOUNDARY` run remains in the metrics and quality
denominators: capped recognition is a content limitation, not automatically an
invalid provenance certificate. Missing/failed requested runs remain explicit
failures and make comparative performance ineligible; they are never silently
removed from the requested scope or used to claim superiority.

## Summary and CPU verification

`summarize_closed.py` writes all per-method group medians plus paired run and
source-cluster summaries. The unit is a fresh-process run, not an IID frontier.
Source-cluster intervals are conditional on the observed schedules. A one-repeat
smoke receives a no-superiority label even if its point estimate is favorable.

`test_controller_audit.py` includes no GPU calls. It exercises frozen scope,
source fairness, output confinement/non-overwrite, all four actual CPU-owner
event streams, deterministic service-book/planner replay, Parent/contract/CDF/
future-context tampering, duplicate dispatch, and preservation of capped output
history. These tests establish audit implementation behavior only; the next
real GPU histories must independently pass the complete audit.
