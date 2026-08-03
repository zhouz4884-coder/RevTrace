# R9.E Online Evidence and Submission Closure

## Decision

`PASS_R9E_ONLINE_SUBMISSION_CLOSURE`

R9.E is the paper-facing closure of the RevTrace Whisper path. All 16 real
two-GPU service cells pass every frozen per-cell threshold. The finalizer also
binds each run to its model tree, policy, source tree, runtime and causal
arrival stream; verifies every online certificate consumption and terminal
audio frontier; and confirms that the optimized executor did not change any
stable output used by the earlier untouched quality evaluation.

## What changed in R9.E

The earlier service runner produced the right stable transcripts but built
transaction evidence after inference and reconstructed parts of the timing
story offline. R9.E replaces that path with an online coordinator:

1. each session receives one immutable causal arrival timestamp shared by the
   proposer and canonical authority;
2. each provisional revision receives a parent version;
3. every canonical segment creates and consumes a contract-bound dual-axis
   certificate before it can advance the audio or feedback-state frontier;
4. stale speculative descendants are invalidated at commit;
5. terminal fallback uses the same fail-closed certificate discipline;
6. display and commit latency are derived from recorded online events;
7. empty fine-grained coverage now has zero deficit, and a replay over 2,050
   historical decisions confirms that this correction changes no frozen
   scheduling decision.

The final executor also removes an implementation defect in which every
decoder step called CUDA scalar synchronization separately for every batch
row. Tokens, margins, selected log probabilities and finished masks are now
transferred once per vector, while EOS state is updated as a GPU vector. This
does not change model arithmetic or policy decisions. All 16 service artifacts
are stable-output hash equivalent to the prior service artifacts.

## Real two-GPU service results

All values are real wall-clock and NVML measurements on two RTX 3090 GPUs.
The wall baseline is the FP16 singleton canonical execution. GPU-normalized
speedup divides the wall speedup by the two GPUs used by the service.

| Model / arrival | Pass | Wall median (min--max) | GPU-normalized median (min) | Energy reduction median (min) | Display P99 max | Commit P99 max | Audio amplification max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Base / sync | 5/5 | 2.740x (2.652--3.200x) | 1.370x (1.326x) | 28.16% (25.51%) | 1.258 s | 24.089 s | 1.012x |
| Base / Poisson | 5/5 | 2.877x (2.633--3.030x) | 1.439x (1.317x) | 31.42% (25.04%) | 1.454 s | 24.155 s | 1.012x |
| Tiny / sync | 3/3 | 2.736x (2.686--2.765x) | 1.368x (1.343x) | 30.11% (29.14%) | 1.003 s | 23.145 s | 1.021x |
| Small / sync | 3/3 | 3.686x (3.272--3.849x) | 1.843x (1.636x) | 32.41% (27.41%) | 1.492 s | 24.564 s | 1.042x |

Across all 16 cells, median wall speedup is 2.841x (range 2.633--3.849x),
median GPU-normalized speedup is 1.421x (range 1.317--1.924x), and median
energy reduction is 31.13% (range 25.04--38.10%). The system consumes 1,048
online commit certificates and records zero transaction-install violations in
the complete service traces. This is an exhaustive observation over these
traces, not an iid failure-rate estimate or a mathematical floating-point
exactness guarantee.

## Quality binding

No new quality run is required because every optimized service cell has the
same stable-output digest as its prior quality-bound service cell. The strict
finalizer binds the six existing quality artifacts to the new service
contracts.

| Cohort | Model | Long sessions | Mean WER delta | Bootstrap 95% upper |
|---|---:|---:|---:|---:|
| Development | Tiny | 128 | -12.23 pp | -10.48 pp |
| Development | Base | 128 | -18.21 pp | -16.17 pp |
| Development | Small | 128 | -25.27 pp | -22.15 pp |
| Third untouched confirmation | Tiny | 40 | -8.26 pp | -5.15 pp |
| Third untouched confirmation | Base | 40 | -11.03 pp | -7.51 pp |
| Third untouched confirmation | Small | 40 | -13.76 pp | -9.09 pp |

The third untouched confirmation is deterministically assembled from 214
previously unused source utterances into 40 long sessions per model. It is not
214 independent long sessions.

## Problems encountered and resolved

### Causal scheduler over-fragmentation

An initial implementation reused the proposer's 0.5-second display coalescer
for canonical authority work and fragmented it into 33 calls. Canonical
segments instead use dependency-wave release under the frozen 36-second commit
budget. No segment executes before its audio and parent state are ready.

### Duplicate evidence hashing

The first online coordinator hashed each audio range when constructing the
certificate and again during commit. The immutable canonical job now owns one
audio digest, and certificate consumption checks the job--certificate binding.

### Misdiagnosed NVML observer overhead

A 10 Hz energy-sampling probe did not improve the remaining workload boundary
and weakened the energy estimate. The hypothesis was rejected and the change
was removed.

### Per-row CUDA synchronization

The actual remaining bottleneck was repeated scalar synchronization in the
batched decoder. Vectorized host extraction restored batching efficiency. On
the three previously failing cells, the corrected path reaches 2.568x, 2.694x
and 2.581x wall speedup, with unchanged stable outputs and zero semantic
violations. The complete fresh matrix then passes 16/16.

## Auditable artifacts

- `results/r9_dgft/FINAL_REPORT_ONLINE.json`: strict aggregate and decision.
- `results/r9_dgft/service/online_closure_matrix/`: 16 full online service
  traces and runner logs.
- `results/r9_dgft/online_closure/contracts/`: three model/runtime/source
  contracts.
- `results/r9_dgft/online_closure/coverage-replay.json`: 22-file, 2,050-segment
  coverage replay with zero changed decisions.
- `scripts/finalize_r9_online_closure.py`: fail-closed finalizer.

## Claim boundary

R9.E establishes a real online, causally scheduled, transaction-certified
Whisper service result across Tiny, Base and Small and complements the Qwen
family evidence. It does not claim universal applicability to all streaming
models. Risk scores remain scheduling signals; state authority comes from the
canonical transition and online certificate. Virtual time is used for causal
arrival and deadline accounting, while GPU wall time and energy are measured
on hardware.
