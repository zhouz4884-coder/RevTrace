# REVTRACE-CES-V5-GPU-20261025: bounded resumption

The user explicitly resumed server/GPU work on 2026-10-25. The prior CPU-only
pause is revoked for this bounded stage. No previous result or manuscript is
edited. Runtime source is frozen at 126dc815962e8f726b0cbdf214a19318b28a3629;
common calibration is the CPU-audited calibration_v3 (SHA256
35aa67579c04018c42f65d8a180c79b60d1941ae53cc87b1177d3ddb49866e55).

First run a paid GPU1 operator probe: select the first archived Fine physical
batch containing at least four distinct session rows; take its first four rows
in archive order. Compare all four in one homogeneous batch against two
two-row batches. Each layout is repeated twice, order whole/split then
split/whole. Check full tokens, stop, projection, text, actual processed inputs,
row timing and complete drain. Cross-layout equality is measured, not assumed.
This is a fixed-state operator diagnostic, not online serving.

Then run two four-session Strict oracle diagnostics (Clean and Mixed) with
paid same-input generation repeats and complete token/stop self-checks.
These are separate from performance cells. Only after safety/operation gates
pass, run 48 arrival-driven diagnostic cells: eight method labels x two
arrivals x three fresh-process repeats, all Mixed. Labels are Fine, Standard,
old joint Cost-only, shared-risk Cost-only, progress, progress GPU0-order,
Fine GPU0-order and Standard GPU0-order. Every method has Row-complete, D1,
the same two GPUs, original admission checks, WAL and actual Consumer ACKs.
GPU0-order is an ablation, not a full joint-planning claim.

Use the previous validation16 pool as explicitly reused diagnostic sources;
no new independent confirmation is claimed. Arrivals are synchronous or 0.25s
uniform stagger, seeds 20261025..20261027, fine=2s/rho=1, FP16 GPU0 and FP32
GPU1, budget256, eager runtime, selective fallback, group-ready WAL. Source
audio/order and exogenous even-session window5 F2 targets are frozen by
manifest/config, never by observed output or method scheduling.

Primary: actual first legal Consumer Display<=2s and durable install<=8s audio
Goodput over full arrival/serving/drain/Consumer wall. Separately report actual
certified-Consumer commit, stable-until-certified coverage, whole-run dual-P99,
P50/95/99, WER/CER, clipped-window energy on both GPUs, fallback/call counts,
all paid obsolete work, host planning/ACK overhead and fsync. Incomplete cells
and frontiers are not dropped. Paired pilot intervals are descriptive.

Failure: preserve raw evidence and stop for an actual safety or execution bug;
do not retune based on diagnostic results while retaining the same frozen
experiment label. Negative performance remains a result. No larger formal
matrix, new algorithm, manuscript rewrite or automatic submission follows.

All models, audio, environments and large logs remain on the designated8TB.
Record controller/source hashes, config/environment, actual worker ownership,
raw-result index, independent audit and the next-step decision. No foreign
GPU process is terminated. GPU occupancy and source bytes are rechecked before
each actual cell. This protocol is finalized before GPU execution.
