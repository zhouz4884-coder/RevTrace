# D source revision: observed credit rate refresh

Independent inspection after A was launched found that V6 read the initially
empty `_closed_credit` dictionary without invoking `_closed_observed_credit()`.
For V6 method=cost, the legacy closed-loop chooser does not run, so qualifying
Consumer/WAL observations never populated that dictionary. Consequently the
utility's observed-rate wall penalty stayed zero. Actual per-target Consumer
display features and all admission checks were still active. This is a policy
wiring defect, not a state-safety violation or a demonstrated performance cause.

The D-only source calls the existing actual-credit derivation, records the
derived rate in every decision and leaves the running A/C source frozen. New
unit tests witness the old empty-book expression and verify refresh precedes
policy evaluation. A includes the pre-fix anchor, not the repaired one. C's
policy=Fine never uses this quantity and is unaffected. D uses the repaired
source for all methods and new fresh-process paired controls.

The first attempted broad `pytest tests` collected19 legacy report/packaging
tests requiring old scripts omitted from this frozen runtime. Its failure XML
is retained as CPU_REGRESSION_D.xml; it is not a safety regression or a pass.
The declared20-file375-case protocol suite plus the two new wiring tests is
run separately as CPU_REGRESSION_D_FOCUSED.xml. Do not call that the full
historical repository suite. The same focused suite is required on Linux.
