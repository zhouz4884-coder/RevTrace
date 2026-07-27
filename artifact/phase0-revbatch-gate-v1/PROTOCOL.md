# RevBatch performance and exact-revision death gate

## Question

Qwen3-ASR's official streaming wrapper maintains one mutable stream, appends
each two-second chunk to a growing audio buffer, rolls back five output tokens,
and calls the underlying vLLM engine with a singleton list. The same engine
supports ordinary list batching. This gate asks whether batching ready
revisions from independent sessions creates a paper-scale performance
opportunity while preserving every official revision.

The candidate is not yet a method. It may proceed only if live performance,
exact revision semantics, and the inadequacy of simple static batching all pass.

## Fixed source boundary

- Qwen3-ASR repository commit:
  `7c6daf77a2421100f5fb066495372c00129d39ff`.
- Official package versions: qwen-asr 0.0.6, vLLM 0.14.0, Transformers 4.57.6.
- Models: Qwen3-ASR-0.6B and Qwen3-ASR-1.7B.
- Hardware: one RTX 3090 per model; the two model sweeps run independently.
- Large models, environments, caches, datasets, logs, temporary files, and raw
  results remain under the designated 8 TB disk.

The D0 audit is frozen in
`results/revbatch/d0/source_audit.json`. Generic offline ASR batching,
duration-aware request ordering, and realtime correctness fixes are prior art.
The candidate scope is multi-session batching under growing-buffer,
token-rollback revision semantics.

## Workload

Each session receives 16 kHz mono audio in two-second chunks. English and
Chinese sessions use the two public samples distributed in the Qwen3-ASR
repository documentation. The server could not establish a stable connection
to Hugging Face for LibriSpeech before execution, so the input protocol was
narrowed before any GPU run. Source recordings are repeated and offset to form
fixed 15, 30, 60, and 120 second performance streams. This gate measures
execution behavior, not WER, and does not present repeated audio as a quality
benchmark.

The formal matrix contains:

- concurrency 1, 4, 8, 16, and 32 at 30 seconds;
- duration 15, 60, and 120 seconds at concurrency 8;
- alternating English and Chinese sessions whenever concurrency exceeds one.

These inputs exercise scheduling, growing-audio, rollback, and exact revision
equivalence only. They do not support an ASR quality or dataset-generalization
claim.

## Compared paths

### Singleton reference

For every ready session, build exactly the official accumulated-audio input and
rollback prefix, then call `model.generate([input])`. Requests ready in the
same revision round execute serially.

### Batched oracle

Build the same per-session inputs and prefixes, submit all ready revisions in
one `model.generate(inputs)` call, then route each output to its own mutable
stream state. This is an upper-bound execution path, not an online scheduler.

Multimodal processor caching is disabled so the batched path cannot benefit
from artifacts populated by the singleton reference. Eager execution and
greedy decoding are fixed.

## Gate A: live performance

Both models must meet at least one threshold:

- audio-throughput speedup at least 1.5x;
- streaming SLO goodput speedup at least 1.5x; or
- event P99 reduction at least 30%.

Results are live RTX 3090 measurements. A local model, CPU proxy, FLOP estimate,
or scheduling simulation cannot pass Gate A.

## Gate B: exact revision semantics

For each model:

- at least 1,000 logical chunk events;
- exact generated token IDs for every revision;
- exact raw decoded state and parsed chunk transcript for every revision;
- exact final transcript for every session;
- an independent smoke comparison between the copied singleton harness and
  the official `streaming_transcribe` function.

Any systematic batch-shape divergence fails Gate B. WER or approximate text
similarity cannot replace the exact oracle.

## Gate C: static-policy sufficiency

Gate C runs only after A and B pass. It compares immediate execution, fixed
5/10/20/50 ms batching windows, length bucketing, and a deadline/shape-aware
oracle using empirically measured batch service times. The oracle must improve
over the best static policy by at least 1.3x SLO goodput or reduce P99 by at
least 30%.

Simulation output is explicitly bounded as a scheduling upper-bound analysis;
it is not reported as live serving performance. If a static policy remains
within 10% of the oracle, the candidate is an engineering integration rather
than a top-conference systems topic.

## Reproduction

On the remote RTX 3090 server:

```bash
bash scripts/remote/setup_revbatch_gate.sh
bash scripts/remote/launch_revbatch_gate.sh smoke
bash scripts/remote/launch_revbatch_gate.sh formal
```

The setup and launch scripts are restart-safe and keep runtime state on the
data disk. Formal raw results are copied back into
`results/revbatch/probe/` before aggregation.
