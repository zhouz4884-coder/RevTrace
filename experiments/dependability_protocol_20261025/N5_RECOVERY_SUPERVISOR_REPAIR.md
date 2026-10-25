# Controller-only SIGKILL resource-release repair

Old measured controller run_n5_validation_v1 SHA9d658278...a637 started PID3994806
/start470315262 and stopped after the first Fine development SIGKILL. Owner
process group was killed, recorded Workers had exited or become zombies; the
immediate nvidia-smi query still showed an owned GPU PID. A later read showed
no GPU processes. The controller asserted empty too early and never launched
attempt1. This is not a demonstrated ledger/Consumer recovery failure or PASS.
The failed raw episode, KILL, input/canonical pre-recovery copies and FAILED_POWER
remain at n5_v3/recovery_development; all costs retained.

v2 supervisor uses a NEW results root n5_v3_supervisor_v2. Same frozen runtime
408d756, model, input, policy and fault point. It waits at most30s only for GPU
PIDs from the already verified owned handle set to disappear. Any other PID
fails closed without terminating or adopting it. No process still holding a
physical lease is reused early; a transient SSH or nvidia status is not death.
All strong comparators receive this same engineering repair.

Repeat both development methods from fresh processes, preserve the original
negative attempt. Independent formal fault runs still require an audited
two-method recovery-development GO_SAFETY_ONLY. No clock reset after restart.
