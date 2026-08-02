# R8 remaining-problem triage

## Current decision

`PARTIAL_REPAIR_CONFIRMED; UNIVERSAL_WHISPER_QUALITY_UNRESOLVED`

The same-prompt singleton arbitration repair was evaluated on the existing
128-session confirmation workloads without changing EFSC/CSM thresholds.

| Model | Outliers before | Outliers after | Mean WER delta after | 95% upper after | Repair outcome |
|---|---:|---:|---:|---:|---|
| Whisper tiny.en | 2 | 1 | -2.412 pp | -1.664 pp | partial |
| Whisper base.en | 2 | 2 | -2.845 pp | -1.935 pp | no outlier reduction |
| Whisper small.en | 6 | 4 | -4.509 pp | -3.023 pp | partial |

No new catastrophic session was introduced. The repaired path performed 11,
12, and 18 same-prompt canonical repairs for tiny/base/small, respectively.

## Fixed defect

The previous asymmetric-context handler immediately cleared the text prompt
before canonical execution. This conflated two different causes:

1. batch-shape arithmetic changed an EOS/continuation decision while the
   context was still valid;
2. the context itself was insufficient or corrupt.

The repaired policy first executes a singleton with the exact replay prompt.
It clears the prompt and reanchors from raw audio only if the same-prompt
singleton remains structurally invalid. This preserves a valid one-token
continuation instead of retranscribing a full window and duplicating content.

## Remaining failure classes

### A. Observable asymmetric conflict

The proposer and replay have strongly different output lengths. Same-prompt
singleton arbitration can solve some of these cases. This class is repairable
with the current two-GPU system.

### B. Shared batch-path error

The proposer and independent replay agree, or differ only weakly, while the
singleton canonical transition is different. Neither margin nor candidate
agreement contains the missing label. Threshold tuning cannot make this class
deterministically safe.

Legal solutions are:

- verify every state-entry transition with the frozen singleton arithmetic
  path;
- implement an arithmetic-path-preserving grouped verifier;
- replace the canonical with a batch-invariant deterministic execution path
  and version that migration explicitly.

### C. Context-sufficiency ambiguity

The same audio window legitimately has different transcripts under different
previous-text prompts. An empty-prompt raw replay is causally independent but
is not equivalent to the original singleton context. An output-only selector
cannot always infer which semantic unit belongs in the session transcript.

A stronger mechanism must preserve a certified canonical prompt checkpoint and
replay every unchecked transition from that checkpoint before committing its
display/state segment. Final exactness requires all unchecked segments to be
closed before terminal commit.

### D. Whisper continuous-replay cost

Continuous independent replay explains the stable 2.5--2.6x wall speedup but
also limits GPU-normalized speedup and energy reduction. Reducing this cost is
only sound after B/C are closed; simply replaying less reintroduces undetected
state divergence.

## Resource requirements

No additional GPU is required for the next semantic experiments. The current
two RTX 3090 cards can evaluate checkpoint replay and always-verify bounds.

An arithmetic-path-preserving verifier requires:

- Triton/CUDA kernel development and profiling;
- a frozen GPU/driver/compiler support contract;
- cross-batch-size, slot, composition, and repeated-run bitwise tests;
- optionally a second GPU architecture for a portability claim.

A clean publication-quality validation also requires a new untouched test
manifest or external long-form dataset. The current confirmation set has been
used for failure localization and can no longer serve as the final untouched
holdout for the repaired mechanism.

## Recommended order

1. Measure the always-singleton state-entry verifier as a correctness/performance
   upper bound.
2. Implement checkpointed canonical replay from the last certified prompt and
   measure the quality-cost frontier.
3. Continue only if the legal oracle retains at least a material end-to-end
   service advantage.
4. If it does, reduce verification cost through grouped path-preserving
   execution or certified cutset replay.
5. Freeze the mechanism and run once on a fresh untouched dataset.

