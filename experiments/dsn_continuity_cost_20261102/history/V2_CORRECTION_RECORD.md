# H1 V1 -> V2: original reference state must remain immutable to queries

V1 actual frozen source: `bf81d68a81bd84375fb7f4b2029be02398cfbab1`.
The formal 15-control execution failed before any historical raw analysis:
2 failures and 7 errors share the original certified-P identity mismatch at
Consumer row 1. See `controls/HISTORY_V1/STDERR.txt` and its preserved gate.

Cause: the analyzer assigned an empty digest into `view.states[sid]['Psha']`
when forming a genesis query. That dictionary was the original reference
replay state. The original pre-Canonical Consumer correctly keeps the
certified projection as None, so the query assignment polluted the next
baseline application. The identity gate correctly exposed the defect.

V2 takes a shallow query-state dictionary copy, then normalizes only that
copy's genesis projection. The original reference/fixture, original raw,
required identity assertions, selection/permission rules, metrics and frozen
input/configuration remain unchanged. Added controls verify no original
genesis-state mutation and that a real certified-P mismatch still fails.
The preparation helper also refuses to rewrite a frozen Git source checkout.

V1 is preserved. V2's actual commit/manifest will be supplied by root; it is
not retroactively attached to the failed V1 execution. No V2 controls or raw
analysis were executed while preparing this correction.
