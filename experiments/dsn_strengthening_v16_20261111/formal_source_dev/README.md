# Phase-correct action invariant audit

`model.py` and `test_model.py` are byte-exact copies of the frozen v3
hand-written specification (`deb3260655e2f3312499a34597cc0be6fc15484b`).
No original control is dropped. `invariants.py` checks every enabled action
over the unchanged transition system. It explicitly permits one durable fact
ahead of the installed Owner parent between sync and install, including the
crashed state. Recovery closes that gap without appending or running C/U.

This is a new CPU specification audit. It is not a new neural implementation,
mechanically extracted proof, natural-trace count, or serving result. The old
6,231/14,074 state results retain their original source/run identity. Any new
run must freeze this directory, record a new commit/manifest/config/environment,
and execute on the designated experiment disk. Keep CURRENT and v15 unchanged.

Run the new frozen `run_checks.py` with `--plan`, `--manifest`, and `--out`.
Use the same old two profile bounds first. Its expected counts are the old
counts because the transition system is unchanged; additional guard/action
checks and explicit legal gap examples are the new evidence.
