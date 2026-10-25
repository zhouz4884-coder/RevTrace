# Before formal result analysis: metric expansion and same-input oracle

No runtime, workload, measured result or original objective is changed.
audit_n5_formal_v1 adds the already required metrics to the independent normal
checker:legal provisional frontier coverage (only ahead of the currently applied
certified view), rejected/uncompleted audio, actual IPC/Consumer application
latencies, rollback, render/Consumer CPU and WAL commit-group write/fsync costs.

An exact offline offered timeline is reconstructed from the frozen arrival
schedule plus each native EOF, synchronized A notices and actual commits. This
answers peak/AUC offered backlog between owner ticks; the earlier sampled
controller-observation peak is retained under its old name. Terminally rejected
offered audio stays in service/quality denominators but is separated from
pending-admission queue debt. The controller never reads this future timeline.

Metric definitions were frozen by N5_VALIDATION_PROTOCOL_v1 before validation.
This is implementation of missing readouts, not post-hoc replacement of the
objective or choice of winning audio. Test against all12old same-input recorded
development runs:all previous primary metrics must match exactly. New fields
do not sum overlapping IPC/owner/GPU costs or present subcomponentCPU as total
system energy. Canonical fsync counts commit groups; directory/initialization
calls are not counted by that hook. All actual costs remain paid in end-to-end
time/power. Total owner CPU and CPU power are not separately measured.

Null exported P99 represents an infinite/missing latency, not a dropped request.
Formal aggregation must retain it. Partial Goodput is not whole-run dual-P99
pass. Statistical comparison units are whole repeated runs (three per frozen
cell), not the hundreds of windows. Report three paired differences, ranges and
small-sample uncertainty without turning a bootstrap into proof of general
superiority. Zero baseline Goodput has no defined relative speedup; use absolute
differences. No pooled ratio across distinct workloads/quality contracts.
