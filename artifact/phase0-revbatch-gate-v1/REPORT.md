# RevBatch performance and exact-revision gate

## Decision

`NO_GO_FOR_REVBATCH_EXACT_REVISION_GATE_B`

Revision batching has a large physical performance opportunity, but the
tested batched execution does not preserve the frozen exact-revision contract.
The topic therefore stops before a deadline-aware scheduler or Gate C policy
oracle is implemented.

This is not a claim that streaming ASR batching is unimportant or that
approximately equivalent batching cannot be useful. It falsifies the proposed
paper identity: an exact, revision-preserving scheduler built by batching the
official Qwen3-ASR generation jobs.

## D0 boundary

The official Qwen3-ASR implementation at commit
`7c6daf77a2421100f5fb066495372c00129d39ff`:

- re-feeds all accumulated audio on every full chunk;
- rolls back the last five tokens after the first two chunks;
- supports only one streaming session per call; and
- invokes vLLM with one request.

The open vLLM realtime-ASR issues describe stateless-segment, growing-buffer,
rollback, and asynchronous-state failures, but do not close multi-session
revision-aware batching. The duration-aware ASR scheduler audited during D0
targets offline request-length scheduling rather than revisable streaming
state. D0 therefore passed into a performance gate; it did not establish
paper-level novelty.

## Frozen execution

- hardware: 2 x NVIDIA RTX 3090 24 GiB;
- one model per GPU:
  - Qwen3-ASR-0.6B;
  - Qwen3-ASR-1.7B;
- PyTorch 2.9.1+cu128, vLLM 0.14.0, Transformers 4.57.6;
- BF16 model execution, eager mode, asynchronous scheduling disabled;
- greedy decoding, at most 32 new tokens per revision;
- two-second chunks, two unfixed chunks, five rollback tokens;
- official public Qwen3-ASR English and Chinese audio, repeated and offset to
  form deterministic performance streams;
- eight cells per model:
  - 30-second streams at concurrency 1, 4, 8, 16, and 32;
  - concurrency 8 at 15, 60, and 120 seconds.

All models, environments, caches, inputs, logs, temporary data, and raw
results remained on the designated 8 TB disk. The bilingual inputs exercise
scheduling and revision semantics only. No ASR quality or
dataset-generalization claim is made.

The singleton reference and batched candidate use identical prompt, accumulated
audio, rollback, parsing, and state-update code. They differ only in whether
vLLM receives one job or all currently ready sessions. Request identities and
event order are asserted before output comparison.

## Cold-start control

The initial 0.6B smoke compared the first cold official execution with the
immediately following copied singleton execution. Their second partial differed
by `Mhm` versus `Hmm`. Repeating the comparison after one official warm-up made
the official and copied singleton records exact for both models. The formal
protocol therefore applies the same warm-up before either measured path.

This correction was made before the formal run and does not relax Gate B:
singleton and batched formal outputs still had to match at every event.

## Gate A: performance

Gate A required both models to reach at least one of: 1.5x audio throughput,
1.5x SLO goodput, or 30% p99 reduction. Both models passed decisively.

| Model | Events | Median throughput speedup | Maximum throughput speedup | Maximum p99 reduction |
|---|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 1,699 | 4.620x | 11.073x | 87.47% |
| Qwen3-ASR-1.7B | 1,699 | 4.220x | 8.752x | 84.69% |

The maximum-throughput cells were 30-second streams at concurrency 32. At
concurrency 8, throughput speedups remained 3.331x/3.075x for 120-second
0.6B/1.7B sessions. The opportunity therefore acts on substantial model work,
not only launch overhead.

These are live coordinator-level GPU measurements, not HTTP-service or
multi-node serving results.

## Gate B: exact revision equivalence

Gate B required, independently for each model:

- at least 1,000 revision events;
- 100% generated-token exact match;
- 100% partial transcript exact match; and
- 100% final transcript exact match.

Both models failed.

| Model | Revision events | Token exact | Partial transcript exact | Final transcript exact |
|---|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 1,699 | 94.29% | 92.05% | 94.12% |
| Qwen3-ASR-1.7B | 1,699 | 97.12% | 96.70% | 92.94% |

The failure is not confined to the largest batch:

- 0.6B first diverged at concurrency 4;
- 1.7B first diverged at concurrency 8;
- both English and Chinese sessions diverged;
- at concurrency 8 and 120 seconds, 0.6B token/transcript/final exactness fell
  to 86.46%/78.75%/62.50%;
- the corresponding 1.7B rates were 95.00%/97.08%/75.00%.

Several early differences are lexical alternatives such as Chinese
`配置`/`定制`; later differences propagate through rollback state. Since each
revision feeds its preceding decoded text back into the next prompt, a small
batch-shape numerical difference can become a different future revision
trajectory. High WER or semantic similarity would not repair the frozen exact
execution contract.

## Gate C: sequential stop

Gate C was not run:

`NOT_RUN_SEQUENTIAL_STOP`

The preregistered policy gate was conditional on both A and B passing. A
deadline-aware oracle, static-window comparison, and scheduler implementation
would optimize a candidate whose exact semantic premise already failed.
Running them would create a strong performance number for a different,
approximate problem.

## Interpretation

The experiment establishes two useful facts:

1. multi-session batching can recover very large GPU throughput and tail
   latency on the official growing-audio workload; and
2. ordinary batch execution is not an exact semantics-preserving
   transformation for this generative revision process in the tested stack.

The second fact is decisive for RevBatch as stated. A future project could
define and validate a weaker quality or stability contract, but that would be
a new topic with new metrics, not a continuation justified by the current
gate.

## Reproduction

```bash
bash scripts/remote/setup_revbatch_gate.sh
bash scripts/remote/launch_revbatch_gate.sh smoke
bash scripts/remote/launch_revbatch_gate.sh formal
python scripts/finalize_revbatch_gate.py
python scripts/validate_revbatch_gate.py
python scripts/build_revbatch_gate_artifact.py
python scripts/build_revbatch_gate_artifact.py --check
```

The remote scripts intentionally pin the source commit and place heavy state
under the designated data-disk root. The public artifact contains compact raw
records, logs, hashes, and the scripts required to audit the decision.
