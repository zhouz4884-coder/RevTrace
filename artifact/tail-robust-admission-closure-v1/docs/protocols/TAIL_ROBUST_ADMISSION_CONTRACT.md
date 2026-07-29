# Tail-Robust Admission Contract

This protocol closes the Phase 7 tail-variance boundary without replacing or
renaming negative evidence.

## Statistical unit

All sessions released in one synchronous round share the same state-entry
latency. The release round, not a duplicated per-session event, is therefore
the independent tail unit. A capacity contract is evaluated across five
independent held-out processes using:

- the maximum seed-level P99;
- a one-sided 95% Student-t upper bound over the five seed-level P99 values;
- the observed number of deadline-miss rounds;
- the frozen contract-scoped state-risk upper bound; and
- online selection-authority violations.

For the 2.0-second deadline, admission uses a 0.1-second guard:

\[
\max_s \widehat{Q}_{0.99,s} \le 1.9\;\mathrm{s},
\qquad
U_{0.95}\!\left(\widehat{Q}_{0.99,s}\right) \le 1.9\;\mathrm{s}.
\]

The same maximum and one-sided upper-bound checks are applied separately to
terminal and nonterminal round P99 values. This prevents the mandatory
terminal path or selective nonterminal path from being hidden by the pooled
round distribution. Admission additionally requires zero observed
deadline-miss rounds,
\(U_{\mathrm{risk}}\le 0.005\), and zero online selection-authority
violations. This is a contract-, hardware-, workload-, and duration-scoped
capacity certificate, not a universal latency theorem.

## Calibration and held-out separation

The c12 threshold is calibrated once in a dedicated process. The resulting
threshold, contract fingerprint, and canonical runtime digest are frozen
before five held-out processes start. Held-out replay observations cannot
modify the online threshold or supply selection authority.

## Version-linearized state mutation

For one session, every result carries:

\[
(\mathrm{parent\ version},\mathrm{next\ version},
\mathrm{contract\ epoch},\mathrm{policy\ epoch}).
\]

A result may mutate state only if all epochs are current, its parent version
equals the committed session version, and its revision identifier has not
already committed. If two results share one parent version, committing either
advances the version and fences the other. By induction, accepted mutations
form a single prefix-ordered chain.

This is a structural ordering guarantee. Content conformance is separate:
the online transition either uses the canonical draw or a fast-path draw
admitted by the frozen statistical risk contract.

## Explicit non-claims

RevTrace does not:

- make floating-point inference deterministic;
- promise equality to a later independent canonical replay;
- convert zero observed online violations into mathematical zero risk;
- promote the rejected c14 capacity point if a diagnostic rerun happens to be
  faster; or
- extrapolate a 30-second capacity certificate to 120-second sessions without
  the separate age-bucket profile.
