# Recovery event identity: durable installation is not client acknowledgement

Numeric observations and original raw files remain unchanged. The historical
`row_gpu_crash_v1/SUMMARY.json` field `acknowledged_segment_survives` is named
too broadly. In this experiment it denotes the internal durable commit marker,
not a returned client receipt or a Consumer-observed Canonical publication.

Source-level order in frozen SDK2bc71af is:

1. `_commit_ready`:original WAL `commit_transitions` successfully returns;
2. `_finish_commit`:in-memory state is set,then the `commit` event is emitted;
3. CLI injection callback sees that event,writes `ACK_FOR_KILL.json` and pauses;
4. controller SIGKILLs the owner before that callback returns;
5. the following Canonical publication and `install-ack` code have not executed.

The file name `ACK_FOR_KILL` is an experiment synchronization marker,not evidence
of an external client acknowledgement. Its raw `kind` is `commit`,not `install-ack`.
Do not change that marker or rewrite the frozen summary to hide the naming issue.

Supported statement:one real GPU owner-process crash after an early full-row
durable install and before publication/physical batch drain recovered that
transition;59unique final admissions,0duplicates. Cold restart→first certified
Consumer36.21553393267095s;kill→Consumer39.151357791386545s. These clocks remain
unchanged and include cold initialization in the resumed path.

Not tested by this particular GPU case:kill after returned client acknowledgement,
kill after Consumer application,host power loss,warm-worker adoption,or all
possible crash schedules. The separate Linux original-WAL CPU fixtures cover
before WAL,post-WAL/prepublication,and postpublication with synthetic model rows;
they must not be promoted to those missing GPU evidence tiers.

Normal row-serving audits check actual Consumer application and physical leases
separately. The original persisted-admission recovery argument still relies on
successful synchronous storage and intact journal data. This correction changes
the evidence label,not the measured result or the preserved admission predicate.
