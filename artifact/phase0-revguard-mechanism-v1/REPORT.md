# RevGuard same-input mechanism and selective-verification gate

## Decision

`MECHANISM_ORACLE_VALIDATED_EXACT_CERTIFICATE_UNRESOLVED`

The original RevBatch experiment established a large batching opportunity but
rejected ordinary batching as an exact revision-preserving transformation.
This follow-up separates three possible causes:

1. revision-state or output-routing code contamination;
2. execution-shape/runtime behavior on an otherwise identical request; and
3. amplification of an initial token difference by the Qwen3-ASR rollback
   feedback loop.

The same-input controls rule out the first explanation for the measured
cross-shape differences. They also show that the first cause cannot yet be
described narrowly as ordinary BF16 GEMM rounding: identical replicated jobs
can produce different rows inside one vLLM batch. A live selective canonical
verifier recovers the singleton token sequence on all tested events while
retaining substantial speed, but the margin rule is empirical rather than a
deterministic certificate and the verifier is not fully hidden by the
proposer.

The result therefore validates a mechanism opportunity, not a completed exact
solution or a production guarantee.

## Frozen environment and evidence boundary

- 2 x NVIDIA RTX 3090 24 GiB;
- Qwen3-ASR-0.6B and Qwen3-ASR-1.7B;
- PyTorch 2.9.1+cu128, vLLM 0.14.0, Transformers 4.57.6;
- eager execution, asynchronous scheduling disabled, prefix caching disabled;
- greedy decoding with at most 32 generated tokens;
- official public Qwen3-ASR English and Chinese audio;
- all models, data, environments, caches, logs, and raw results on the
  designated 8 TB disk.

The bilingual streams test execution and revision semantics. They do not
support ASR quality, dataset-generalization, or production-frequency claims.
The dual-GPU result below is computed from live per-stage service times; it is
not a deployed cross-GPU serving system.

## M1: same-input causal control

For every revision, the harness prepares one immutable prompt/audio job, hashes
it, and evaluates it four times:

1. singleton A;
2. singleton B;
3. batch A;
4. batch B.

Only singleton A updates the next revision state. Consequently, all four
outputs for an event read the same prompt, accumulated audio, rollback prefix,
and byte-identical audio array. An earlier batched output cannot contaminate
the next event.

### Results

| Model | Cell | Events | Singleton repeat exact | Batch repeat exact | Singleton vs batch exact |
|---|---|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | c=8 | 120 | 100.00% | 100.00% | 96.67% |
| Qwen3-ASR-0.6B | c=16 | 240 | 100.00% | 99.17% | 97.08% |
| Qwen3-ASR-1.7B | c=8 | 120 | 100.00% | 99.17% | 97.50% |
| Qwen3-ASR-1.7B | c=16 | 240 | 100.00% | 99.58% | 98.75% |

Singleton execution is stable across all 720 repeated events. Cross-shape
differences remain after feedback is removed. The 1.7B c=8 run and both c=16
runs also contain batch-repeat differences, so a greedy batched result cannot
itself be treated as a canonical certificate.

### Identical-job replica probe

For each c=8 cross-shape mismatch, the exact same job was replicated into all
eight batch positions. Across four 0.6B and three 1.7B mismatch probes:

- 0/7 batches produced identical token sequences in all rows;
- 0/7 batches had every row match the singleton result;
- rows often formed groups that selected different low-margin continuations.

This removes heterogeneous audio and prompt content as a necessary cause.
It points to request-slot, internal microbatch, multimodal processing, or
kernel/runtime nondeterminism. It does not by itself distinguish a vLLM/Qwen
implementation defect from permissible finite-precision execution-order
variation. The correct current label is `runtime/execution-shape behavior
under investigation`, not a proven RoPE or mask bug.

This behavior is consistent with an existing vLLM bug report in which greedy
outputs change under concurrent requests even after testing FP32 and disabling
prefix caching:
https://github.com/vllm-project/vllm/issues/23138. The current experiment is
more specific because it uses replicated multimodal Qwen3-ASR jobs and records
request-row differences.

### FP32 mechanism control

The c=8 and held-out c=16 experiments were rerun with FP32 weights and a reduced
`max_model_len=16384` so the model and required KV cache fit on a 24 GiB 3090.
For both models:

- singleton repeat exactness was 360/360;
- batch repeat exactness was 360/360;
- FP32 singleton-versus-FP32 batch exactness was 360/360.

At c=8, FP32 batches retained 3.54x and 2.86x speedup; at c=16 the speedups
rose to 5.55x and 4.21x relative to the corresponding FP32 singleton paths.
The c=16 FP32 batches were also 4.75x and 3.36x faster than the measured BF16
singleton paths, although they do not preserve those paths' outputs. This
strongly attributes the BF16 divergence in this workload to
precision-sensitive parallel execution rather than a deterministic
rollback-state routing error.

However, FP32 does not preserve the frozen BF16 canonical trajectory. Compared
with the BF16 run, only 108/120 and 116/120 FP32 singleton events matched for
0.6B and 1.7B, and feedback changed later input hashes. Even among events whose
input hashes remained identical, BF16 singleton and FP32 singleton differed in
6/90 and 2/118 cases. FP32 therefore defines a more stable execution contract;
it is not an exact repair for the official BF16 singleton contract.

## Mathematical boundary

Let the batched and canonical log-probability vectors at one greedy decoding
step be \(z^{B}\) and \(z^{1}\). Let \(c\) be the batched top-1 token and define

\[
m_B = z^{B}_c - \max_{j\ne c} z^{B}_j,
\qquad
\epsilon = \lVert z^{B}-z^{1}\rVert_\infty .
\]

For every competitor \(j\),

\[
z^{1}_c-z^{1}_j
\ge
z^{B}_c-z^{B}_j-2\epsilon
\ge
m_B-2\epsilon .
\]

Therefore,

\[
\boxed{m_B>2\epsilon
\Longrightarrow
\arg\max z^{B}=\arg\max z^{1}.}
\]

The experiment observes \(m_B\) through top-20 vLLM log probabilities. It does
not possess a sound online upper bound on the full-distribution
\(\epsilon\). A threshold on margin alone is therefore a useful risk signal,
not a deterministic exactness certificate.

The second mechanism is revision feedback. If \(S_t\) is the revision state,
\(F_B\) and \(F_1\) are batch and canonical execution, and \(G\) is the state
update, then

\[
Y_t^B=F_B(S_t),\qquad
Y_t^1=F_1(S_t),\qquad
S_{t+1}=G(S_t,Y_t).
\]

The same-input experiment measures the first inequality
\(F_B(S_t)\ne F_1(S_t)\) without feeding it back. The original RevBatch run
then shows how such an inequality changes the rollback prefix and thus the
future input state. Feedback is an amplifier, not the measured root cause.

## M2: empirical margin partition

The c=8 cell was used only to freeze the threshold

\[
\min_t m_{B,t}>1.0.
\]

The threshold was then evaluated on the different c=16 batch shape.

| Model | c=8 calibration coverage | c=8 false-safe | c=16 held-out coverage | c=16 false-safe |
|---|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 80.83% | 0 | 80.00% | 0 |
| Qwen3-ASR-1.7B | 78.33% | 0 | 81.67% | 0 |

This passes the preregistered empirical partition gate: both models exceed 50%
coverage with no held-out-shape false-safe event. It does not establish a
distribution-free or deterministic guarantee.

## M3: live selective canonical-verification oracle

The live policy executes every ready revision through the batched proposer.
Revisions at or below the frozen margin threshold are recomputed through the
singleton canonical path. A separate full singleton pass supplies the
reference but is excluded from policy service time. Policy state is updated
only with the selected output.

| Model | Events | Verified | Violations | Single-GPU speedup | Ideal two-stage pipeline lower bound |
|---|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 240 | 46 (19.17%) | 0 | 2.99x | 4.94x |
| Qwen3-ASR-1.7B | 240 | 41 (17.08%) | 0 | 2.88x | 5.28x |

The oracle passes the live mechanism gate: zero observed token-sequence
violations and more than 2x single-GPU speedup for both models.

The pipeline lower bound is

\[
S_{\mathrm{pipe}}
=
\frac{T_{\mathrm{singleton}}}
{\max(T_{\mathrm{proposer}},T_{\mathrm{verifier}})}.
\]

It assumes perfect overlap, no transfer cost, and a steady queue. It should not
be reported as a deployed two-GPU result.

## M4: verifier headroom fails

The canonical verifier consumed 1.54x and 1.20x the proposer service time for
0.6B and 1.7B. The frozen headroom condition required

\[
T_{\mathrm{verifier}}\le0.8T_{\mathrm{proposer}}.
\]

Both models fail. The second GPU can pipeline the stages, but it cannot fully
hide verification; the verifier becomes the throughput bottleneck.

Dynamic rollback was not implemented after this failure. Enlarging rollback
only changes the provisional/committed frontier and cannot restore the
official singleton trajectory. Running that controller before establishing a
certificate or a faster canonical verifier would mix two different contracts.

## Interpretation and next research decision

The experiment gives an evidence-based decomposition:

- **not an upstream revision-state code contamination:** same jobs are compared
  before any batched state update;
- **not proven to be only normal BF16 rounding:** identical jobs diverge by
  request row, and batch repeats can differ;
- **a real model/runtime mechanism:** low-margin greedy decisions vary with the
  execution schedule or shape;
- **a real model-level amplifier:** decoded text is fed into future revision
  prompts;
- **a viable empirical repair:** selective canonical recomputation preserves
  all tested references at 2.88-2.99x on one GPU;
- **not yet an exact solution:** margin lacks a sound perturbation bound, and
  the verifier is not fully hidden.

The correct next target is not a complex deadline scheduler. It is to localize
the replicated-row divergence inside the Qwen3-ASR/vLLM path and determine
whether a canonical batch kernel or a sound perturbation certificate can make
verification cheaper. If the divergence is a fixable runtime bug, the paper
identity becomes correctness plus revision-feedback containment. If it is
irreducible numerical behavior and no useful bound is available, the exact
paper claim must be abandoned in favor of an explicitly statistical stability
contract.
