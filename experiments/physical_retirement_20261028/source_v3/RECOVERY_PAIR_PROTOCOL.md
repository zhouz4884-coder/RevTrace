# Trusted recovery startup: same-contract four-arm development pilot

Status: implementation and CPU controls only. No GPU experiment has been
launched by this package. Parent must integrate, independently review, commit,
freeze the complete source, run Linux CPU gates and schedule actual GPU use.
The previous source is 8923af39efbf36c9bf5ab4685f7a0d7d244482c9; adding this
controller and logical-fault hook requires a NEW source commit/manifest. Do not
label these bytes with 8923af39.

## Question and intervention

Does overlapping native trusted-renderer initialization with two real cold
workers improve measured recovery without delaying verified old-fact views,
changing the render contract, skipping checks, or weakening full Standard?

Four arms: RevTrace `dgft_original` and full Standard `standard_fair`, each
with resume `full_first/reuse` or `descriptor_workers_first/reuse`. Every
prefix uses **full_first/reuse**, so the compared initialization cannot change
pre-fault execution. First pilot: c4, one repeat per arm; `--repeats` is retained
for a separately frozen repeated study. Rotate and reverse the four-arm order
by repeat. No claim of statistical advantage from four cells.

All arms: original four independent metadata-first validation-source audio,
fine=2s, rho=3, FP16 Proposer GPU0, FP32 Authority GPU1, full physical MB16,
256-token budget, real row-complete/drained lease, trusted render, kernel
event-cow, unchanged private eligibility, group-ready WAL, input debt journal,
real local FIFO Consumer, original D2/C8 deadlines. Limit budget1000s and queue
threshold10000 are deliberately nonbinding, identically applied. Complete
audio, including final fractional chunks and missing responses, stays in the
denominator. Default stagger offsets 0/.25/.5/.75; sync is a frozen alternative,
not a post-result selection.

## Logical fault, ownership and cold/cache boundary

Freeze `--fault-target 0:192000` (session0, 12s audio frontier at16kHz).
The first source lasts12.215s; its12s transition and0.215s suffix are real, and
the other sources continue up to18.925s. An atomic marker is emitted only
after the actual `commit_transitions` fsync returns, before owner installation
and publication. This is not a simulated journal event or an8s wall-clock cut.

The controller validates the owner PID, Linux start ticks, pgid and command
hash; verifies exactly proposal-0 and authority-1 handles; rejects any group
member not descended from that owner. It rechecks owner identity immediately
before SIGKILL of its isolated group, awaits its SIGKILL return code and owned
GPU allocations disappearing, then launches attempt1 with the same episode,
input and canonical WAL paths. It will not kill a foreign task or bypass a
failed identity check for cleanup. Partial diagnostic tails are preserved.

This is **cold processes/weights reloaded with existing filesystem caches**.
It is not cold disk cache, surviving-worker adoption, machine reboot, power
loss or storage corruption. Weight hashing occurs before experiment launch
and can warm filesystem cache; all arms share that condition. Model runtime,
asset and descriptor hashes are frozen. No cache flushing or `sudo` operation.

The target transition alone does not establish identical cuts. `FAULT_CUT`
also records WAL sequences and raw hash, full per-session committed history
and P/Z/text, durable frontiers, accepted frontiers, rejected sessions and
pre-crash accepted debt. Exact logical-cut matching ignores irrelevant
cross-session record ordering and wall timestamps but retains actual model
outcomes. **Unmatched cuts remain reported with no paired difference.** They
must not be filtered after seeing which arm won. If no exact matches result,
that is a pilot design finding, not evidence for a speedup.

## Clocks and actual observations

The primary fault origin is controller `perf_counter` immediately before
SIGKILL; signal-sent and owner-exited times are also retained. No reboot or
cross-host clock comparison is performed. The original arrival origin remains
unchanged across the two attempts, including all downtime and cold reload.

1. **Old-fact RTO:** all positive durable frontiers present in pre-recovery WAL
   have been applied by the actual restarted Consumer. This includes synced
   but not yet published facts, and does not count as new generation.
2. **First-new-fact RTO:** the first actual certified Consumer frontier strictly
   beyond that session's recovered WAL frontier. Renderer replay, workers-ready
   and a historical receipt cannot satisfy this metric.
3. **Pre-crash debt RTO:** all audio durably accepted before the fault beyond
   the recovered canonical frontiers is actually certified and consumed.
   No such debt => null/N/A, not zero. It is not final EOF/newly offered work.
4. **Whole-run service:** original arrival to last real Consumer/physical
   drain, all offered fine frontiers with D2/C8, P50/P95/P99, goodput and
   WER/CER. Resource lifecycle through process teardown is recorded separately.

Existing `startup_profile` spans permit attribution (identity/renderer/imports,
worker weights/warmup, WAL/re-render/debt, real Consumer receipts), but do not
substitute for these clocks. Time spent validating the descriptor is included.

## Cost, audit, failures

External board-power samples continuously enclose prefix startup, work, kill,
restart imports/weights, new work and teardown on both GPUs. Killed physical
work is not free. Worker receipt traces distinguish submitted, fully completed,
drained and abandoned/no-receipt work; a logical enqueue without physical
submission is not invented as GPU execution. CPU energy is not measured;
attempt1 ConsumerCPU, inputfsync counts/time, journal sizes and profile spans
are reported. Prefix host counters lost at SIGKILL are not fabricated.

`paired_recovery_audit.py` adapts the archived CK5 independent recorded-prefix
audit. It verifies framed hash chains, actual model input/row identity/Stop,
single physical leases, canonical parent/interval/Z/P matches, immutable
precrash WAL prefix, exactly one restart epoch, actual private-chain legality,
trusted published receipt identities, original clock, accepted-debt discharge
and all-offered metrics. The controller separately checks runtime source hashes,
configuration and initialization order. A separate frozen native asset/text
replay remains an explicitly pending gate: this controller is not a proof of
neural correctness or browser/network delivery.

Failure before the target, malformed or mismatched log, invalid receipt,
incomplete resume, source mutation or retained GPU worker stops the queue.
No fallback fault point, partial success relabeling, repeat replacement or
silent target change. Old/full failure outputs stay immutable.

## Integration and execution

Copy `paired_recovery_controller.py` and `paired_recovery_audit.py` to the
execution source root; copy `recovery_fault.py` to `runtime/src/revtrace/`.
Apply `recovery_runner.patch` only to the verified runner baseline in
`RUNNER_PATCH_IDENTITY.json`. It preserves existing CRLF bytes. The patch adds
one explicit logical fault hook and changes no safety predicate or normal run.
The source root already supplies read-only helpers in `x_service_metrics.py`
and the external `memory_gpu_pilot.Power` sampler.

Then commit/freeze again, verify complete source, and prepare a matching
descriptor (package/source identity must match actual frozen environment).
Representative command, to be instantiated by the parent only:

```text
<model-env-python> <new-frozen-source>/paired_recovery_controller.py
  --output <8TB>/results/revtrace/freeze_boundary_20261027/recovery_c4_v1
  --source-manifest <new-manifest.json>
  --manifest <8TB>/results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json
  --render-descriptor <approved-QWEN_RENDER_DESCRIPTOR.json>
  --render-descriptor-sha256 <verified-full-sha256>
  --sessions 4 --arrival staggered --repeats 1 --fault-target 0:192000
```

Required independent postpilot review: cut matching; frozen config/source;
actual startup phase attribution; old/new/debt metrics separately; complete
negative results; native replay; both implementations; all workers released.
Only then decide whether to freeze repetitions. No claimed RTO or percentage
benefit exists before these real runs.
