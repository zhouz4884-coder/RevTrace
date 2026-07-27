# Anytime randomized-audit risk contract

## Target

RevTrace uses randomized canonical shadow execution to bound the cumulative
number of unsafe fast-path state entries. The target is

\[
\Pr\left(\exists t:\ M_t > U_t\right)\leq \alpha,
\]

where \(M_t\) is the latent cumulative count of fast-path state-entry errors and
\(U_t\) is an anytime-valid upper confidence sequence.

## Fixed-probability base audit

Every risk-eligible transition receives an independent base-audit coin
\(A_i\sim\mathrm{Bernoulli}(p)\). The coin is independent of the canonical
outcome. Let \(S_t=\sum_{i\leq t} A_iE_i\), where \(E_i\) indicates a true
state-entry error.

For each fixed \(\lambda<0\),

\[
\mathcal E_t(\lambda)=
\frac{\exp(\lambda S_t)}
{\left(1-p+p\exp(\lambda)\right)^{M_t}}
\]

is a nonnegative martingale in the error-event clock. A fixed convex mixture
over \(\lambda\) is therefore an e-process. Ville's inequality gives the
time-uniform guarantee, and inversion yields \(U_t\).

The result permits:

- arbitrary temporal drift in \(E_i\);
- dependence among error events;
- optional stopping based on the confidence sequence.

It requires:

- the base audit probability to be frozen for the certified population;
- the audit coin to be independent of the canonical error outcome;
- every caught error to be recorded, including errors repaired before state
  commit.

## Adaptive extra audits

Adaptive audits may be added for diagnostics, queue control, or root-cause
analysis. They are excluded from \(S_t\) and cannot tighten the formal bound
unless their predictable inclusion probabilities are incorporated in a
separate valid construction.

## Scope of the bound

The current bound applies to high-margin, nonterminal FP16 proposer transitions.
Low-margin transitions and terminal transitions are canonicalized by the
deployed mechanism and are outside this risk population.

The certificate is statistical. It is not a deterministic arithmetic-path
certificate and does not establish singleton equivalence.

## Simulation acceptance

The mathematical guarantee comes from the e-process proof. Monte Carlo is used
only as a regression test. A simulation passes when:

1. the observed coverage-violation frequency is no greater than \(\alpha\) in
   each frozen scenario; and
2. the zero-caught-error bound at 30,000 entries is no greater than
   \(\delta=0.5\%\).

Wilson intervals are reported as diagnostics, not used as a second and more
conservative theorem test.
