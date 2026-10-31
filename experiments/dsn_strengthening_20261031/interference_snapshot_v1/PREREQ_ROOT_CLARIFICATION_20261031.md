# Root prerequisite clarification before any new probe output

Recorded 2026-10-31 after the authorized original 40 NN trials and b867 zero-NN
posthoc review completed, and **before any two-client probe model output**.
The previous development commit `61abb744b90dda3fa4dd976e5deca75fd6e10d00`
remains historical. No original execution/RUN/GATE/result file is edited.

Root explicitly accepted the observed resident contract as useful: all four
trials' task/reference/per-request clocks and continuous model PIDs passed;
Full-call passed 7/8 original per-request D2/C8 gates versus Conservative 0/8,
with actual audio credit 64.118875 versus 31.0 out of 66.33975 seconds. These
are the completed single-client resident results, not a prediction of probe
performance or a claim of resident SLO invariance.

The previous prerequisite incorrectly demanded 8/8 resident D2/C8. Its corrected
meaning is: both repeats contain four distinct requests per arm, complete exact
task/reference/clock/PID evidence and no missing D/C frontier, and each repeat
retains the already used strong opportunity test (`credit gain >= 1 second` OR
`Full-call all-offered D99 <= 0.75 * Conservative D99`). The actual request
passes and every original miss are retained. A reference/clock/obligation/PID
failure still blocks the probe. This changes a pre-probe admission prerequisite,
not any historical success label or metric.

The buffer prerequisite likewise consumes the actual new evidence schema:
source b867, frozen config/input-index hashes, formal31 CPU PASS, posthoc
aggregate PASS, four per-case `PASS_ZERO_NN_POSTHOC_MECHANISM_REAUDIT` wrappers,
their nested real mechanism PASS, exact original task/reference PASS, unchanged
complete raw/watchdog indexes and current bytes. Original4eb receipt-reader
failure, CLI exit1, watchdog FAIL and compound NO_GO remain failed. A wrapper
cannot hide a task/protocol/physical failure, or retroactively grant end-to-end
execution success.

The prospective two-client contract and opportunity hard gate are unchanged:
fixed B offset2s, fixed A0/A1/B0/B1 sid order, original independent EOS sources,
500ms/all-offered D2/C8/NN59/C/U/FP32, original admission proposals, maximum four
actual attempts, first-pair stop, Conservative zero C8 misses on all requests,
actual A-spec/B-ready dispatch inversion and B relative harm threshold. No
source/phase sweep, budget/weight policy or candidate scheduler is introduced.

Implementation/CPU/schema evidence is local only. Root still owns independent
review, formal freeze, CURRENT/no-argument source gate, Linux controls and any
explicitly authorized future GPU window. This clarification alone launches
nothing and implies no expected probe success.
