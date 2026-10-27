# Temporary recovery controller delivery

Current local CPU gate: **24/24 passed**, no GPU/remote calls. The latest
`CPU_GATE.json` also confirms the prepared hook is already integrated by the
parent (`git apply --reverse --check` passes). The earlier attempt to apply it
a second time failed as expected and is retained in
`CPU_GATE_ALREADY_APPLIED_CONTEXT_v1.json`; this is not a model/runtime failure.

Integration files:

- Source root: `paired_recovery_controller.py`, `paired_recovery_audit.py`.
- Runtime module: `recovery_fault.py` → `runtime/src/revtrace/recovery_fault.py`.
- Runner modification: `recovery_runner.patch`, verified against original
  runner SHA256 `928184525beb019cde99dd0545dfabc28eb2c68c91804e365c461bb8f655e381`.
- CPU test: `test_paired_recovery.py`; use source root plus runtime module
  directory on PYTHONPATH (or place the test's helper import as appropriate).
- Frozen design: `RECOVERY_PAIR_PROTOCOL.md`.

Do not miss the final two tests and audit refinement: actual recovered
Consumer **text and P/Z hashes** must match the retained WAL record, not only
its frontier/version. Latest audit SHA256 is recorded in `CPU_GATE.json`.

The audit was adapted from the archived
`experiments/composed_kernel_20261026/audit_ck5_fault_v2.py`. It reuses the
current frozen `x_service_metrics.py` mathematical/hash/private-chain helpers,
not the production scheduler/Consumer to approve its own output. Native asset
and trusted-text replay remain separately pending. The controller does not
claim new model work from CPU rendering of historical certificates.

Independent static review by `/root/freeze_wait_audit` found no process-
ownership/original-clock blocking defect: PID/startticks/pgid/cmdhash and group
ancestry are checked, unmatched logical cuts get no paired claim, and
Standard's current non-boundary-probe path indeed has the same rho3. The
reviewer explicitly limited this to static review; actual worker schemas and
cut-match rate remain to be tested by the parent-scheduled real pilot.

The controller refuses an optimized `python -O` interpreter because recorded
audit assertions are deliberate fail-closed checks. Every failed cell stops
the queue. If cleanup identity cannot be verified, it records
`CLEANUP_REQUIRES_INSPECTION.json` rather than killing a broad process pattern.

Pending before GPU launch: parent integrate final audit/test bytes; new source
commit and byte manifest; Linux CPU tests and matching descriptor gate; fresh
environment/weight identities; parent-only GPU scheduling. No RTO improvement
or same-point pair count exists yet.
