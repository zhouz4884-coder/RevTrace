# RevTrace V100 V1--V4 execution report

## Decision

**`V1_V4_MATRIX_COMPLETE_AND_AUDITED_PASS`**

The full independent V100 matrix completed 84/84 cells with zero retained
cell failures.  A second local audit reloaded every raw JSON record and passed
479/479 structural, denominator, finite-value, transaction, ancestry, and
directionality checks.

This is a separate RHEL 7.6 / 8x Tesla V100 32 GB / Transformers-eager
contract.  Absolute values are not pooled with the RTX 3090 / vLLM contract,
and V3 is single-node replica scale-out rather than multi-node scaling.

## V0 legality and environment

- Node: `gpu2`, 8x `Tesla V100-PCIE-32GB`.
- Python 3.10.6, PyTorch 2.4.1, CUDA 12.1, Transformers 4.57.6.
- Both Qwen3-ASR-0.6B and Qwen3-ASR-1.7B loaded and completed repeated
  same-input FP16 inference exactly.
- Model config SHA-256 values and a full package freeze are retained in the V0
  artifact.

## V1 -- authority microprofile and execution-shape evidence

- All 24 microprofile cells completed for two models, two dtypes, and batch
  sizes 1/2/4/8/16/32.
- Batched repeatability was 100% within this run: zero repeat mismatches for
  both models and both dtypes.
- Batched output was nevertheless not singleton-equivalent.  Each model had
  62 batch-versus-singleton request mismatches across the FP16 and FP32 cells.
  FP32 therefore improves stability but is not an unconditional
  batch-invariance certificate on this V100 contract.
- At batch 32, FP16 reached 29.244 requests/s (0.6B) and 26.257 requests/s
  (1.7B), respectively 14.687x and 12.841x over sequential singleton work in
  the same cell.

## V2 -- normal-load, apples-to-apples c16 comparison

| Model | RevTrace-SG speedup | SG display P99 | SG verify fraction | SG edit P95 | Hybrid-DGFT speedup | Hybrid display P99 | Hybrid edit P95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 4.682x | 1.095 s | 6.67% | 0.00% | 5.764x | 1.086 s | 0.00% |
| Qwen3-ASR-1.7B | 3.248x | 1.440 s | 10.00% | 0.00% | 4.657x | 1.466 s | 3.18% |

- All V2 modes use the same c16, 30 s, bilingual, 240-display-event workload.
- RevTrace-SG is exact against its independent FP16 singleton reference for
  all 16/16 final sessions in both models.
- Coarse-DGFT reaches 6.072x (0.6B) and 4.893x (1.7B); Hybrid-DGFT reaches
  5.764x and 4.657x.  The 1.7B coarse/hybrid quality boundary is explicit:
  P95 edit rate 3.18%, with 8/16 exact sessions.
- RevTrace-SG reduces measured total energy per audio second from 8.877 to
  4.961 J (44.1%) for 0.6B, and from 13.941 to 8.563 J (38.6%) for 1.7B,
  despite using the second GPU for verification.
- All observed transaction-install and uncertified-risk/ancestry violation
  counters are zero.  These are empirical zero observations, not a claim of
  mathematical zero risk.

## V3 -- 8-GPU single-node scale-out

The strongest SLO-valid production point is 4 proposer plus 4 authority
replicas at c64:

| Model | Audio xRT | Display P99 | SLO misses | 8-GPU scale efficiency vs p1a1 | Protocol violations |
|---|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 147.138x | 1.115 s | 0/960 | 91.1% | 0 |
| Qwen3-ASR-1.7B | 114.488x | 1.471 s | 0/960 | 100.7% | 0 |

- At c32, p4a4 reaches 106.85x/96.87x with sub-second display P99
  (0.856/0.887 s).
- At c128, throughput saturates at 148.930x/111.133x while display P99 rises
  to 2.266/2.799 s.  Therefore c128 is retained as an honest overload/capacity
  boundary; the 2 s-SLO capacity is c64 for both models.
- Adding authority replicas alone has little effect when proposer capacity is
  fixed.  Joint proposer-authority scaling is required, which directly
  supports the DGFT two-stage bottleneck model rather than a generic
  "more GPUs" explanation.

## V4 -- FP32 authority bottleneck attribution

At rho=1, FP32 authority is the bottleneck:

- 0.6B: authority/proposer ratio 2.216, throughput 18.603x.
- 1.7B: authority/proposer ratio 2.669, throughput 12.294x.

Amortizing the authority over five windows moves the ratio below one and
restores service throughput while preserving zero observed protocol
violations:

- 0.6B rho=5: ratio 0.759, throughput 40.630x, display P99 1.084 s.
- 1.7B rho=5: ratio 0.841, throughput 33.909x, display P99 1.359 s.

This is the expected DGFT mechanism result: coarse-grained authority is not
free, but its cost can be amortized until it no longer dominates the proposer.
The trade-off is higher commit latency, which is reported separately from the
low-latency provisional-display contract.

## Problems encountered and fixes

1. The cloned ModelScope CLI contained an absolute shebang; downloads were
   switched to the Python SDK.
2. `qwen-omni-utils` pulled an FFmpeg build that failed on RHEL 7; the unused
   dependency was removed.
3. Current `soxr` required C++17 unavailable with GCC 4.8; `soxr==0.3.7` and
   compatible scientific packages were pinned.
4. ModelScope file locks deadlocked on NFS; downloads were serialized to one
   writer with file-locking disabled and model hashes retained.
5. Old remote `sed` corrupted CRLF-normalized Python lines ending in literal
   `r`; scripts were reuploaded and CRLF conversion changed to Perl.
6. A copied environment plus NumPy 1.26 broke `torch.from_numpy`; NumPy 1.23.4
   and SciPy 1.9.3 were restored.
7. Source audio was 48 kHz; deterministic high-quality soxr resampling to
   16 kHz was added to both smoke and matrix runners.
8. Worker dispatch attempted `int(None)` and startup could wait silently after
   a child failure; fallback handling and fail-fast worker diagnostics were
   added.
9. `return_dict_in_generate` was passed twice by the Qwen wrapper and runner;
   the duplicate runner argument was removed while retaining score output.
10. The first independent audit incorrectly assumed a common V2 schema.  It
    was fixed to distinguish SG risk counters from DGFT ancestry counters;
    the corrected audit passes 479/479 checks.

## Code and artifacts

Core V100 code:

- `scripts/v100/setup_revtrace_v100.pbs`
- `scripts/v100/v100_hf_smoke.py`
- `scripts/v100/run_revtrace_v1_v4.pbs`
- `scripts/v100/run_v100_matrix.py`
- `scripts/v100/finalize_v100_matrix.py`
- `scripts/v100/audit_v100_matrix.py`

Validation:

- Python compilation passed for all V100 scripts.
- 34 existing RevTrace transaction/DGFT/cross-adapter/anytime-risk tests passed.
- Result audit: 479/479 checks passed.

Artifact SHA-256:

- Bundle: `0E6AD0AC862E8FA059A3A86CEC12DCC29BE9F27820B16B5BBA1A65C3D6A7B960`
- Raw summary: `9ABD271F094260CC18F06018172498E524C33AD4ECB340B979A2479366F1F296`
- Independent audit: `CFECFAE7F85713E7F5AABB2D0DEE228F6E2C8B7BE3653E1DE2EE40C12F8EC57D`

## Final good/bad assessment

**Good:** the main paper concern is materially resolved.  RevTrace now has a
real 8-GPU, two-model, normal-load performance matrix with c64 SLO-compliant
capacity, 91--101% scale efficiency, 114--147x audio real-time throughput,
zero observed protocol violations, and an explicit authority-bottleneck
mechanism experiment.

**Bad/boundary:** this is one 8-GPU V100 node using an independent
Transformers/eager contract, not multi-node scale-out.  c128 fails the 2 s
display SLO.  FP32 batch is not singleton-equivalent on V100, and 1.7B
coarse/hybrid DGFT has a 3.18% P95 edit boundary.  These results must remain
visible and must not be pooled with RTX 3090/vLLM absolute numbers.
