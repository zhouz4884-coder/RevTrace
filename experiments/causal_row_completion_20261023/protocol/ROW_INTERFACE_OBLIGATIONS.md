# Row-complete / Batch-drained: proof obligations, not a new model guarantee

The original pre-prototype32 local CPU tests included23 lifecycle cases and9
observer cases. Frozen SDKv2 subsequently passes210 Linux CPU regressions;
three original-WAL process-kill fixtures remain CPU/synthetic-model evidence.
Neither count substitutes for GPU evidence. Actual operator,live-pilot and
one early-row GPU SIGKILL/cold-resume evidence are separately indexed. The old
119-file runtime remains immutable; all new execution uses the separate SDKv2.

1. **Transport authenticity assumption.** The existing local worker/IPC channel
   is trusted; source identity is worker incarnation,batch/job/session,execution
   contract and immutable actual input/audio binding. A hash is not GPU attestation.
2. **Completeness.** Row-final means full Z at declared EOS or budget terminal,
   plus deterministic P/text/stop checking. Budget-final remains a content cap,
   not proof of recognition completeness. No accepted prefix substitutes for Z.
3. **Worker exclusion.** Starting a physical batch acquires a lease for its full
   job set. Partial results may discharge logical jobs but cannot discharge the
   worker. Only a trusted Batch-drained with the exact result manifest releases
   the lease. Missing,stale,duplicate-conflicting or wrong-incarnation data fail closed.
4. **Immutable early proofs.** Facts already known at row completion are sealed;
   future peer fallback costs and batch timing use a separate accounting record.
   Do not mutate a published proof when later work finishes.
5. **Canonical installation.** Preserve existing current-parent,frontier,contract,
   selected-output and trusted-Render checks. The old A/B/C/D certificate building
   and WAL success still precede state installation/Canonical publication. Each
   transaction identity can enter the accepted history only once.
6. **Private progress.** A Proposer receipt can only reach the original legal
   provisional consumer. An older birth parent is not blanket-invalid if the
   original exact compatibility proof succeeds. Conversely, an early receipt,
   FP32 origin or imminent deadline does not license a mismatched private view.
7. **Early parent changes.** Frozen jobs retain their original inputs. New jobs
   may use a new committed parent only after WAL installation and only for audio
   strictly ahead of that parent. Old results cannot be relabelled as new-parent
   execution. Pending work is charged until physically drained/cancelled in fact.
8. **Crash/retry.** Existing WAL's transaction request digest and restart fencing
   remain authoritative. An acknowledged early row survives only if its real WAL
   commit survived. A restart does not authorize uncommitted old-incarnation rows;
   no new warm-worker adoption algorithm is in scope. Partial group-ready progress
   and same-content retries must be tested with the original journal,not a fake log.
9. **Accounting.** Count additional IPC,CPU render,owner scheduling and fsyncs.
   Earlier row installation may alter future queue/batch/input realizations; prove
   each actual history independently instead of splicing old fixed-rho traces.
10. **Non-novelty control.** Ordinary safe row-return + existing correct causal
   coordination is a strong baseline. If it is equivalent to the proposed path,
   the outcome is a generic executor result,not an independent algorithm increment.

## Preservation argument tied to the implemented transition system

This is a source-level inductive argument under the original trusted-worker and
storage assumptions,not a model-checked proof or a guarantee about faulty GPUs.
Source identity is SDK2bc71af5457de5d065ff9e771d2fad428c5c6ed9; function names
below refer to that frozen source,not historical line numbers.

**Transport invariant.** Before `RowInbox.begin`,the worker is reusable. Begin
fixes one unique nonempty job set,all RowBindings and the worker incarnation.
`receive` must match the complete frozen binding,decode a sealed payload and
validate its causal finite clocks. A first digest yields one logical result;
the same digest yields none,a conflict poisons the lease. No receive changes
`active`. `drain` requires every expected row and the exact digest manifest,
and a clock not earlier than any emission,before clearing `active`. Induction
over any interleaving of row/drain events gives at-most-one logical delivery
per job and no physical worker reuse before full drain. The trusted worker
must report a truthful drain; a hash does not independently establish that.

**Admission preservation.** `RowGPUExecutor.poll` exposes only leased jobs;
`LiveQwenScheduler._receive` retains its old current-Authority-parent and actual
audio/runtime checks. It validates D1 again in the owner. `_commit_ready` builds
the same authority job and calls unchanged `build_dual_axis_certificate` and
`commit_canonical_segment`. WAL `commit_transitions` succeeds before
`_finish_commit` installs/publishes. There is one in-flight Authority per session,
so row delivery can reorder independent sessions but cannot introduce two
same-parent Authority installations within one session. Every new accepted
transition is therefore an instance of the old admission rule. It need not
produce the same history as batch-return: earlier scheduling may change actual
future batch realizations. Every resulting history is audited independently.

**Private progress preservation.** Proposer results take only the old provisional
path. A receipt never converts their role to Authority. After a commit,
`eligible_chain` preserves an old private branch only on actual exact state
edges and frozen in-flight-input compatibility; otherwise the existing
`_make_job` causal rebase or obsolete completion rule applies. Earlier arrival
does not relax any comparison or make old Z a generation under a new parent.
Consequently legal consumer progress may become available earlier,but no
unconditional deadline or forward-progress bound follows from the interface.

**Recovery preservation.** The original WAL request identity,digest and epoch
checks still determine recovered admissions. A crash after an early row but
before its successful WAL record may lose that unacknowledged row;after WAL it
must recover that admission even if peer rows were unfinished. A physical batch
is not the atomic durability unit. Recovered state may contain a legal subset
of that batch;no fabricated all-batch commit is required. Uncommitted receipts
from the old worker incarnation are not adopted. CPU fixtures test partial
progress and duplicate identities;the single GPU kill confirms one concrete
pre-drain post-WAL case,not all crash schedules or host power loss.

**Cost boundary.** These arguments establish permission and lease semantics,
not faster compute. Stream callbacks,Render,serialization,owner polling,
changed fsync grouping,uncancellable old GPU work and full physical drain
remain charged. A verifier's accepted row may be deliverable before failed
peers finish fallback only after the complete correct-context check has ended.
EOS/declared budget finality is distinct from transcript quality/completeness.
