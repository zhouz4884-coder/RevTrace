# RevControl adaptive certification contract

## Purpose

Phase 3A replaces a hand-selected margin threshold with a controller that
chooses among a preregistered monotone policy family.  The choice is permitted
only inside a simultaneous anytime-valid confidence envelope.

## Contract fingerprint and epochs

An epoch is identified by

\[
\chi=(h_M,h_T,R,D,K,C,P,F),
\]

where the components are the model and tokenizer hashes, runtime, precision,
kernel/backend portfolio, concurrency class, chunk policy, and canonical path.
Changing any component creates a new epoch.  No risk evidence crosses an epoch
boundary.

## Simultaneous policy envelope

For every preregistered threshold \(\tau_k\), the corresponding fast-path
population is

\[
\mathcal P_k=\{i:m_i>\tau_k,\ i\text{ is nonterminal}\}.
\]

Before observing the canonical result, an independent coin with fixed
probability \(p\) decides whether event \(i\) is a base audit.  Each policy
owns a mixture e-process inversion at level
\(\alpha/K\).  A union bound therefore makes all \(K\) confidence sequences
simultaneously valid at arbitrary stopping times.  The controller may select a
policy after observing the joint envelope without invalidating the familywise
guarantee.

The controller minimizes

\[
\lambda_t U_t(\tau)A_t+\mu_t c_t V_t(\tau)
\]

over certified policies.  \(U_t\) is the risk upper bound, \(A_t\) the
state-amplification price, \(V_t\) the empirical verifier fraction, and \(c_t\)
the verifier cost.  Risk and queue prices are updated online; the threshold is
an output, not a human input.

## Fail-closed behavior

- Terminal transitions are always canonical.
- With no certified policy, every state transition is verified.
- A base-audit state disagreement enters short-horizon quarantine and removes
  every policy whose fast path contains that margin unless it remains
  certified under the updated envelope.
- Stale decisions from an older fingerprint or epoch are rejected.

## Two audit channels

The independent base audit is the only channel used by the formal confidence
sequence.  Opportunistic idle audits may estimate value of information or
diagnose drift, but are excluded from formal counts.  Combining the channels
would require a separately preregistered known-propensity estimator.

## Evidence boundary

The controller provides a statistical state-disagreement contract.  It is not
a deterministic floating-point certificate.  Shadow-audit elapsed time is
diagnostic and is never presented as serving performance.
