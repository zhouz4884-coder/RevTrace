# RevTrace Deployed System Gate

## Decision

`DEPLOYED_SYSTEM_GATE_PASS_DETERMINISTIC_CERTIFICATE_UNRESOLVED`

The deployed mechanism is now supported by real two-GPU service measurements,
fresh canonical replay, a versioned state-entry ledger, synchronized terminal
bursts, and a flip-rich execution-shape stress suite. It is no longer supported
only by a sequential policy-time sum or an ideal pipeline lower bound.

The deterministic certificate remains unresolved. Margin 0.05 is an effective
empirical scheduling signal, but no online bound currently proves that an
unverified FP16 batched output equals the FP16 singleton canonical output.

## Frozen mechanism

The measured service uses:

1. an FP16 multi-session batched proposer on GPU 0;
2. a full-candidate minimum-margin risk filter;
3. an FP16 batch-size-one canonical verifier on GPU 1 for low-margin and
   terminal revisions;
4. a per-session revision ticket binding every result to its parent version;
5. fail-closed rejection of stale, replayed, or wrong-parent results;
6. terminal work stealing, which uses the otherwise idle proposer GPU to
   execute half of a synchronized terminal verification burst through the same
   FP16 singleton arithmetic path;
7. a fresh post-run singleton replay, excluded from service timing, that checks
   every selected output and every exact next-state projection.

Only a selected, version-matched transition may update the state used by a
future revision. Provisional batching never receives permission to advance the
committed state merely because it is fast.

## D0: generic WSIR novelty does not survive

The installed vLLM 0.14.0 tree already contains batch-invariant matmul, bmm,
softmax, RMSNorm, linear, and attention controls. The public vLLM feature is
beta and explicitly targets deterministic output independent of batch size and
request order. TBIK likewise fixes reduction order for invariant inference.

Therefore generic Weight-Shared Isolated Reduction or a generic
batch-invariant kernel cannot be the paper's novelty.

The current Qwen3-ASR path is not covered end to end. With
`VLLM_BATCH_INVARIANT=1` and FlashAttention selected, both models terminated in
the installed `_log_softmax_batch_invariant` path:

```text
assert not _half_to_float, "not implemented"
...
EngineDeadError
```

This is a reproducible multimodal compatibility gap, but by itself it is an
upstream integration problem rather than a sufficient systems-paper
contribution.

Relevant primary sources:

- <https://docs.vllm.ai/en/latest/features/batch_invariance/>
- <https://arxiv.org/abs/2511.17826>
- <https://arxiv.org/abs/2601.17768>
- <https://arxiv.org/abs/2605.30218>

## R1: flip-rich safety stress

The stress suite reconstructs one naturally observed FP16-sensitive revision
per model from its canonical streaming state. It changes only legal serving
context: batch size, row slot, co-runner composition, and repeat. It does not
inject logit noise, mutate the model input, or advance state between paired
executions.

| Model | Target-row executions | Real proposer flips | Flip rate | Margin false-safe |
|---|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 924 | 613 | 66.34% | 0 |
| Qwen3-ASR-1.7B | 924 | 408 | 44.16% | 0 |

These rates characterize a deliberately flip-rich stress set, not natural
production prevalence. The result establishes that the policy encountered
1,021 real failures rather than merely passing clean traces, and that all
observed failures fell on the fail-closed side of the frozen margin rule.
It still does not convert the rule into a mathematical certificate.

## R2: deployed two-GPU system

The frozen workload is 30 seconds, 16 concurrent bilingual sessions, 2-second
chunks, FP16, and margin threshold 0.05. Each model produces 240 live revision
events. All terminal revisions require canonical verification.

| Model | Verify | Output/state/stale violations | Wall speedup | GPU-normalized speedup | 2-s SLO goodput speedup | State-entry P99 | Deadline miss |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 7.92% | 0 / 0 / 0 | **5.53x** | **2.77x** | **5.23x** | 2.98 s | 5.42% |
| Qwen3-ASR-1.7B | 9.17% | 0 / 0 / 0 | **4.75x** | **2.38x** | **4.49x** | 2.59 s | 5.42% |

The wall metric includes proposer/verifier IPC, queueing, version checks,
terminal bursts, work stealing, and commit latency. Model initialization and
the independent post-run audit are excluded from steady-state service timing.
The GPU-normalized result divides the two-GPU throughput by the one-GPU
canonical baseline capacity and therefore does not hide the additional GPU.

Across 480 natural live revisions, the fresh singleton replay found:

- 0 complete-output violations;
- 0 next-state projection violations;
- 0 stale or replayed commits.

Zero observed violations is empirical evidence, not proof. A rule-of-three
95% upper bound from 0/480 is approximately 0.625%.

## Work-stealing ablation

Returning verifier results as soon as each singleton completes exposes the
terminal burst rather than charging every row the complete batch wait.
Terminal-aware work stealing then uses GPU 0 only after its terminal proposal
has completed; no later revision can be delayed by that local canonical work.

| Model | Wall improvement | SLO-goodput speedup after work stealing | P99 reduction | Terminal verifier P95 |
|---|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | +13.21% | 5.23x | 38.27% | 2.26 s |
| Qwen3-ASR-1.7B | +7.66% | 4.49x | 41.65% | 1.94 s |

Work stealing materially improves the system, but does not remove every
deadline miss. Synchronized terminal arrivals remain the measured tail
bottleneck and are preserved in the main table.

## Mechanism decisions

### Continue: revision transactions

The independent paper identity is state-certified revision serving:

- growing multimodal input;
- global text retokenization and rollback;
- a feedback state that can amplify one numerical flip;
- parent-version binding;
- terminal full-output contracts;
- state-entry commit and stale-result rejection.

Generic low-margin verification is not claimed as novel.

### Continue: exactness research, but keep the boundary

The next exactness contribution must be one of:

- a sound state-entry perturbation certificate;
- an arithmetic-path-preserving concurrent singleton verifier;
- a minimal deterministic operator cutset that covers the complete
  audio-to-token dependency cone.

The current results authorize this research, but do not pre-announce its
success.

### Stop: generic WSIR as the main contribution

Existing vLLM batch-invariant kernels and TBIK occupy the generic claim. A
Qwen3-ASR compatibility patch may be useful engineering, but it cannot be the
paper's central novelty.

### Stop for this workload: cascading speculation

Before terminal work stealing, intermediate verifier P95 was 1.11 seconds for
0.6B and 1.32 seconds for 1.7B, below the next 2-second chunk interval.
Speculating descendants would therefore add rollback complexity without hiding
measured cross-revision latency. It should be reconsidered only under a workload
that actually produces verifier lag beyond the next chunk.

### Keep as non-certifying control: acoustic absorption

Additional acoustic context may guide holdback, verifier priority, or dynamic
rollback, but it cannot prove equality to the singleton canonical path across
EOS, punctuation, tokenization, and discrete argmax boundaries.

## Paper-facing claim spine

The strongest defensible claim is:

> Low-precision batching is not a semantics-preserving execution transform for
> feedback-driven generative streaming. RevTrace prevents numerical drift from
> entering future revision state through versioned canonical state-entry
> transactions, and recovers 4.75-5.53x deployed wall throughput and
> 4.49-5.23x 2-second-SLO goodput on two Qwen3-ASR scales.

The paper must not claim:

- deterministic safety from margin alone;
- that the stress flip rate estimates production frequency;
- generic batch-invariant kernel novelty;
- zero deadline misses;
- cross-architecture generality before a second revision-feedback architecture
  is evaluated.

## Next high-level-paper gate

The deployed system and stress gates have passed. The next phase should not add
more Qwen3-ASR rows mechanically. It should pursue two independent requirements:

1. a second revision-feedback architecture, not merely another checkpoint from
   the same family;
2. an independent exactness mechanism or a formally bounded statistical
   contract, while retaining the existing natural/stress evidence split.

Until then, the project is a strong deployed mechanism result with an explicitly
unresolved deterministic certificate, not a finished top-conference paper.
