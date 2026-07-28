# Phase 7 reviewer-defense and SOTA comparison report

Decision: `PHASE7_REVIEWER_DEFENSE_COMPLETE_WITH_COMPATIBILITY_BOUNDARIES`.
There is no Phase 8. Phase 7 freezes the submission evidence and the limits of
the claim.

## A. Contract-safe reshape and complete execution signatures

`ShapeEnvelope` is now a finite set of complete `ExecutionSignature` objects,
not a Cartesian product of independently observed fields. A reshape candidate
must carry a certificate bound to the exact contract digest, and joint
admission checks both its guarded P99 and risk upper bound. Property tests
verify that:

- an unseen field combination cannot warm-start;
- an uncertified reshape cannot be admitted;
- a known failure raises only the matching applicability key;
- an unrelated contract is not dragged by a global failure floor.

The first c64 queue attempt deliberately exposed the importance of this
change. An English threshold (`0.031251`) was manually reused for a new
`mixed` contract. The resulting 960-event run produced 5 output and 2 state
violations, including a margin-8.39 divergence. The failed raw run is retained
as `raw-invalid-mixed-cert.json`; it is evidence against certificate transfer,
not a result hidden by retuning.

## B. SOTA source comparison

| Baseline | Source result on RTX 3090 | Exact scope |
|---|---|---|
| Thinking Machines `batch_invariant_ops` | bitwise invariant; P50 pair latency 0.618 ms vs 0.133 ms ordinary (4.65x) | source operator |
| `batch_invariant_ops` Qwen3-ASR integration | 8/8 state exact; 2.086x over singleton vs 2.198x ordinary FP16 | c4/d4 smoke only |
| TBIK | Triton fallback bitwise invariant; 0.272 ms vs 0.101 ms (2.68x) | source operator; Hopper path unavailable |
| vLLM Batch Invariance | real Qwen3-ASR decode reached then failed at unsupported `_half_to_float` log-softmax | incompatibility preserved |
| SGLang deterministic inference | source imports, but Qwen3-ASR path requires newer Torch/CUDA-13 FlashInfer stack | frozen-stack incompatibility |
| LLM-42 | source imports; text server requires custom invariant kernel absent from wheel; local build blocked by missing `nvcc` | original-source attempt preserved |
| MarginGate-inspired revision | fixed 0.05 threshold misses the real margin-0.109375 state failure | faithful adaptation, not original ASR |
| Owner/version-only state | rejects stale owner/version, but accepts the legal current-version numerical flip | faithful RW-TTT adaptation |
| LLM-42-style revision | zero selected state errors by verifying every transition; measured canonical goodput 1.565 events/s | faithful revision adaptation |

The guarantee matrix separates arithmetic determinism, stale-result fencing,
adaptive evidence, and joint risk/SLO admission. Operator/import probes are
never promoted to end-to-end serving claims.

## C. Component ablation

Frozen counterexample replay gives the following causal ordering:

1. margin-only repeats the 0.109375 failure and permits cross-contract reuse;
2. session versioning rejects stale writers but not legal numerical flips;
3. epoch fencing removes two stale-policy/contract commits;
4. contextual failure memory removes known-failure recurrence;
5. exact-contract renewal reduces EN return recertification from 1,358 to 64
   events (1,294-event adaptation-regret reduction);
6. joint risk/SLO admission removes the 448 c64 active-service deadline misses
   by reshaping to active c16;
7. full RevTrace additionally requires explicit execution signatures and a
   certificate-bound reshape.

The measured EN-ZH-EN trace consumed 112.295 verifier GPU-seconds. We do not
fabricate per-ablation GPU seconds where an intervention was replayed offline.

## D. Full c64 offered-load accounting

The corrected live run declares all 64 English sessions at time zero and
admits four measured active-c16 waves.

| Metric | Result |
|---|---:|
| offered / active / initially queued | 64 / 16 / 48 |
| active state-entry P99 | 1.942 s |
| active deadline misses | 0 / 960 |
| admission latency P50 / P99 | 21.812 / 42.988 s |
| end-to-end P99 including queue | 44.797 s |
| drain wall time | 55.678 s |
| completed audio goodput | 34.484 audio-s/wall-s |
| completion goodput | 1.149 sessions/s |
| energy | 8.765 J/completed-audio-s |
| observed output / state violations | 3 / 1 |

The one state violation in 960 events gives an exact one-sided 95% upper bound
of 0.4932%, below the frozen 0.5% state-risk contract. It is not mathematical
zero. Inspection shows that the violating event had already taken the
canonical path; a later canonical replay differed, confirming that FP16
canonical execution remains statistical rather than bitwise deterministic.
This is why the paper must not claim a deterministic certificate.

## E. Risk-contract sensitivity

For delta in {0.25%, 0.5%, 1.0%}, the exact zero-error audit requirements are
1,197, 598, and 299. The frozen 0.109376 contextual failure floor is unchanged
and admits 1,855/1,920 events with no fast-path state error on the frozen c32
trace; the derived verification fraction is 5.052%. Thus delta controls
evidence acquisition time, not a hand-tuned threshold. Relative warm-up costs
are 2.002x, 1.0x, and 0.5x. Performance numbers in the sensitivity JSON are
explicitly a shared live-run reference, not three unrun measurements.

## Problems found and classification

1. **Configuration/semantic error:** an EN certificate was initially attached
   to `mixed`; fixed by exact-contract rerun and retained as a Phase 7A
   counterexample.
2. **Code/config typo:** the first corrected rerun used unsupported language
   label `en`; the parser requires `English`. No result was produced; fixed and
   rerun.
3. **Numerical mechanism:** FP16 fixed-shape canonical replay can still differ;
   not a state-routing bug. The measured result is kept under a statistical
   risk contract.
4. **Source compatibility:** vLLM, SGLang, LLM-42 and TBIK failures are
   preserved with raw logs and not rewritten as method failures.

## Code used or changed

- `src/revtrace/phase6.py`: explicit shape-signature envelope and
  certificate-bound reshape.
- `src/revtrace/phase7.py`: SOTA adaptations, risk math, guarantee and ablation
  primitives.
- `scripts/run_phase7_reviewer_defense.py`: frozen-evidence tables and source
  manifests.
- `scripts/finalize_phase7_c64_queue.py`: admission, queue, end-to-end, energy,
  and exact binomial-risk accounting.
- `scripts/remote/run_phase7d_c64_queue.sh`: real two-GPU offered-load run.
- `scripts/remote/run_phase7_*`: source probes for BIO, TBIK, vLLM, SGLang,
  and LLM-42.
- `tests/test_phase6.py`, `tests/test_phase7.py`: semantic/property tests.

Final validation: 77 tests pass.

