# RevGuard state-entry contract and precision intervention gate

## Decision

`LIVE_MECHANISM_GATE_PASS_DETERMINISTIC_CERTIFICATE_UNRESOLVED`

The mechanism and performance loop now closes on the frozen two-model
workload. A float16 batched proposer plus selective float16 singleton
verification produced zero observed full-output or state-projection violations
over 480 live revision events. Verification remained below 10% and below the
pre-registered 0.8 verifier/proposer service-ratio headroom on both models.

This is not yet a deterministic margin certificate. The admission rule is an
empirical scheduling policy, while exact repair for selected requests comes
from canonical singleton execution.

## What N1 disproved

For an intermediate revision, the state-relevant projection is the exact
official rollback operation

\[
\Phi_K(P,Y)=
\operatorname{decode}\left(
\operatorname{encode}(P\mathbin{\|}Y)_{1:-K}
\right),
\]

where \(P\) is the previous prefix and \(Y\) is the new generated text. At a
terminal revision, the contract is the complete final output rather than a
rolled-back prefix.

If two executions satisfy

\[
\Phi_t(Y_t^{(a)})=\Phi_t(Y_t^{(b)})
\]

at every transition and begin from the same state, induction through the
state-update function gives identical future revision states. This
commit-projection argument is valid.

The hoped-for empirical premise was not valid. Across the default BF16 c=8 and
c=16 controls, 17 complete singleton/batch mismatches were observed, and 16
changed the next state projection. Only 1/17 was absorbed by rollback.

The reason is structural: fixed-\(K\) rollback is applied after concatenation
and retokenization. A suffix decision that changes output length by one token
also moves the global rollback frontier by one token. Therefore, “the differing
token lies in the last \(K\)” does not imply equal next state.

## Cause triage

The evidence separates code, model mechanism, and research-hypothesis failure.

- Code/state mixing was ruled out by preparing each input once from canonical
  singleton state and mutating state only after all paired executions.
- The new projection implementation was checked event-by-event against the
  original `rollback_prefix` implementation and fails closed on disagreement.
- BF16 singleton execution was previously 720/720 repeat-exact, while BF16
  singleton/batch and batch-repeat controls diverged.
- Identical jobs replicated across eight slots still produced different rows,
  ruling out ordinary per-session revision-state crossing.
- FP32 was previously 720/720 repeat- and cross-shape exact, showing a
  precision-sensitive execution mechanism.

The new interventions refine the cause:

| Intervention | Model | Events | Cross-shape mismatches | State mismatches | Batch speedup |
|---|---:|---:|---:|---:|---:|
| BF16 default, c=8 | 0.6B | 120 | 3 | 3 | 4.92x |
| BF16 default, c=8 | 1.7B | 120 | 3 | 3 | 4.15x |
| Decoder Triton only, c=8 | 0.6B | 120 | 2 | 2 | 4.09x |
| Decoder Triton only, c=8 | 1.7B | 120 | 3 | 3 | 3.86x |
| MM Torch SDPA only, c=8 | 0.6B | 120 | 1 | 1 | 4.56x |
| MM Torch SDPA only, c=8 | 1.7B | 120 | 3 | 3 | 4.10x |
| Both non-Flash, BF16 c=8 | 0.6B | 120 | 1 | 0 | 4.82x |
| Both non-Flash, BF16 c=8 | 1.7B | 120 | 1 | 1 | 4.21x |
| FP16 default, c=16 | 0.6B | 240 | 1 | 0 | 7.54x |
| FP16 default, c=16 | 1.7B | 240 | 1 | 1 | 6.37x |
| FP16 plus both non-Flash, c=16 | 0.6B | 240 | 0 | 0 | 6.10x |
| FP16 plus both non-Flash, c=16 | 1.7B | 240 | 3 | 2 | 5.28x |

Attention reductions contribute to the phenomenon, and FP16's finer mantissa
substantially reduces it. Neither is a cross-model deterministic fix.
Combinations are non-monotonic because backend changes alter the direction, not
only the magnitude, of rounding perturbations near token decision boundaries.

## Live mechanism result

The selected policy is:

1. generate every ready revision with an FP16 batch;
2. verify a revision with the FP16 singleton path when the minimum margin over
   the complete candidate is at most 0.05;
3. always verify a terminal revision;
4. permit only the selected policy output to update revision state.

The full candidate margin is required. Looking only at tokens that appear to
survive rollback is unsound because a suffix length decision moves the rollback
frontier.

| Model | Events | Proposal mismatches | Verified | Verification fraction | Policy violations | State violations | Single-GPU speedup | Dual-stage lower bound | Verifier/proposer |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 240 | 0 | 19 | 7.92% | 0 | 0 | 4.57x | 7.43x | 0.626 |
| Qwen3-ASR-1.7B | 240 | 1 | 22 | 9.17% | 0 | 0 | 4.12x | 6.51x | 0.581 |

Both ratios are below 0.8, so the measured verifier service can be hidden by
the second RTX 3090 with the frozen 20% headroom.

## Mathematical boundary

For batch logits \(z_B\), singleton logits \(z_1\), and batch top-1 margin
\(m_B\),

\[
m_B > 2\lVert z_B-z_1\rVert_\infty
\quad\Longrightarrow\quad
\arg\max z_B=\arg\max z_1.
\]

The system observes \(m_B\) online but does not have a reliable worst-case
bound on \(\lVert z_B-z_1\rVert_\infty\). Consequently:

- the singleton result is a real repair for selected revisions;
- zero violations over the frozen live workload is valid empirical evidence;
- margin 0.05 alone is not a deterministic certificate for unverified
  revisions;
- FP32 remains a stable alternative canonical trajectory, not an exact
  restoration of official BF16 singleton output.

## Next research step

The strongest next step is no longer broader backend search. It is one of:

1. derive or measure a sound online perturbation bound for the state-entry
   projection; or
2. accelerate canonical singleton verification while preserving its arithmetic
   path; or
3. identify the smallest FP32/deterministic operator slice that is invariant
   across batch shape, slot, composition, and repeat.

Dynamic rollback remains downstream queue control. It does not establish
exactness and should be evaluated only after the certificate path is frozen.
