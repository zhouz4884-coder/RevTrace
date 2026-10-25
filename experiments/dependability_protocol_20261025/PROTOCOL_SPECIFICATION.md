# P3 — Two permissions, explicit state machine and proof obligations

Status: specification draft tied to checked code; independent bounded
enumeration is REQUIRED and not yet claimed complete. The N1 GPU experiment
tests concrete schedules, not the universal state machine.

## 1. Trust boundary and variables

One coordinator owns each session. A trusted Authority/complete verifier is
non-Byzantine and selects using the **actual** bound model input, not merely
matching declared metadata. Trusted adapter/render code is deterministic under
its frozen assets. The storage device honors successful synchronous writes and
keeps complete acknowledged records intact. The local Consumer applies an
authenticated, single-owner FIFO stream; a restart starts a declared new stream.
Neither arbitrary worker corruption, host compromise, network authentication,
bit-flip correction, ASR truth nor complete recognition follows from this model.

For session s, use canonical state

    C_s = (e, v, F, P, selected_Z, receipt_history)

where e is execution epoch, v monotone version, F committed audio frontier,
P adapter feedback projection. Private state

    B_s = (g, birth_parent, root_F, root_P, tip_q, tip_P, completed_nodes)

has a generation g; it is not a second canonical history. Frozen job J contains
session, role, epoch, birth Parent, root/actual conditioning P, audio interval
[a,b), prefix/interval digests, chunk and advance, private generation, declared
contract/runtime, generation budget and stopping rule. Its actual processed
input X (including audio realization, IDs, tensors/dtype/layout) is recorded
separately. Declared equality does not by itself prove X equality.

Physical worker state L=(incarnation,batch_id,ordered jobs,lease). A complete
immutable row R carries its job/source identity, full Z/stop/P/text evidence.
`RowComplete` does not imply `BatchDrained`: row consumption may precede lease
release; a late delivered row never authorizes a second installation.

Durable state D is a prefix of complete checksummed WAL frames, including
successful admission identities and render witnesses. Publication queue Q has
typed provisional/canonical messages. Consumer state U has an independent
certified (e,v,F,P,Z,text,transaction) and an optional whole provisional view.

## 2. Transition obligations

1. **Release audio.** Increase released frontier only when actual audio arrives.
2. **Dispatch proposal.** Target b must be released and b>root_F. If a newer
   canonical parent is eligible (F<b), rebasing constructs a new frozen job and
   generation. An already executing job is not reinterpreted under a new parent.
3. **Dispatch authority / correct-context verifier.** Freeze current C and an
   interval starting at F. Bind actual realization, full token/stop/budget and
   projection selection evidence. A verifier may reject then pay for generation.
4. **RowComplete.** Bind actual Worker incarnation/batch/job receipt. A row is
   immutable after completion. Multiple delivery paths still name one result.
5. **BatchDrained.** Release physical lease only after all model work drains;
   logical retirement cannot reclaim already issued GPU work.
6. **Receive proposal.** Check current contract/epoch, target>F and active
   generation before mutating private tip/publishing. The legacy single-guard
   ablation removes only this freshness decision; it retains other protections.
7. **Select/validate authority.** Require same session/epoch/current Parent,
   gap-free nonempty interval, unused transaction/certificate identity, actual
   selection evidence, exact Z/P and D1 text derivation. Deadline pressure never
   weakens this predicate. Authority provenance is not transcript completeness.
8. **Persist.** Append a complete transition/frame, synchronize, then replace
   volatile canonical state and return a durable receipt. A group sync may make
   a valid prefix durable without making the entire group globally atomic.
9. **Publish canonical.** Exact installed transaction/F/version/Z/P and trusted
   text are published as a full snapshot. A provisional message cannot overwrite
   that certified lane, even when its target is farther ahead.
10. **Consume provisional.** Version/epoch/frontier fences reject covered or
    retired messages. Ahead-target continuity additionally requires exact state
    equality at the new canonical boundary followed by every actual private
    input/output edge, matching generation and frozen pending input. This permits
    compatible old-birth-parent views; it does not infer token/audio alignment.
11. **Canonical correction.** Retain a whole provisional view only if the same
    exact-chain predicate still holds. Otherwise show the certified snapshot;
    a necessary recognition correction is not a protocol failure or avoidable
    rollback. Do not splice an unproved suffix into certified text.
12. **Crash/restart.** Discard volatile owner state; read/check complete durable
    prefix; reject complete bad frames; truncate only an incomplete final frame.
    Advance execution epoch, reconstruct consumed identities and trusted render,
    start new Consumer stream and republish durable certified facts. Old in-flight
    results are fenced, except a separately verified adoption protocol (not part
    of N1). Identical admitted retry returns its old receipt, not a new transition.

## 3. Properties — not one overloaded 'safety' theorem

**Authorized Ancestry.** Each installed P is selected by a trusted operation
under its recorded current Parent and actual input/contract. Proof is induction
on successful transition installations, conditional on trusted calls and single
ownership. A hash of arbitrarily substituted trusted output does not satisfy it.

**Gap-free Commit.** For every successive admission, a=previous F, b>a,
new F=b, and logical admission identity is unique. Induction does not require
constant rho; variable intervals still need legal job construction and a frozen
contract, not a claim that dynamic scheduling is already implemented.

**Fresh Provisional Publication.** At owner publication, provisional b>current F
and g=active generation. This excludes two stale classes, but does not establish
that every ahead result is rooted at the current canonical projection. Full
Consumer may make an omitted owner fence redundant for actual visibility while
the server-level property still fails. Report both levels.

**Exact-chain Private Continuity.** Any actual provisional view retained/applied
above certified F has an exact same-boundary P root and a complete chain of
actual private edges to its tip. Parent-ID equality is sufficient in some simple
cases but neither universally required nor a substitute for input equality.
Dispatch rebase, receive freshness and Consumer chain checking protect different
boundaries. This is not full linearizability of speculative text.

**Durable Certified View.** Every actually consumed certified snapshot names a
successfully durable admission or its validated replay, with exact Z/P/text and
session/epoch/version/transaction binding. An acknowledged logical admission is
not installed twice after crash. This does not force the Consumer to be current
at every instant or make a local install marker an external client ACK.

**Conditional progress.** If finite chosen intervals have available audio,
workers terminate, required storage succeeds, owner and Consumer are fairly
scheduled and queues drain, pending admissible work/certified publication can
advance. There is no unconditional RTO, overload SLO or cap-free recognition
guarantee. Bounded model exploration is not a liveness proof for unbounded input.

## 4. Planned explicit model cross-validation

Two independent implementations must follow this specification: Python
state-space search and a separately implemented JavaScript enumerator. Compare
reachable canonical state encodings, transition counts, property outcomes and
shortest concrete witnesses under identical declared bounds. No success if a
state/time cutoff was reached. At least two frontiers, private chain depth2,
both relative completion orders, row-before-drain, one restart, pending WAL,
duplicate result/retry and both compatible/incompatible projections are needed.
Separate small two-session cross-binding cases from one-session interleavings.

Run full guards and matched removal of parent/frontier/source/render,
publication freshness, exact-chain retention and write-before-ACK as applicable.
Do not assert each guard individually causes end-user harm: other fences may
correctly block it. Record server property and actual Consumer property apart.
The model treats complete model results as symbolic inputs. CPU enumeration,
production CPU tests, actual GPU F2 and N1 ordering remain separate evidence.

## 5. Code correspondence

`live_qwen.py`: frozen dispatch/rebase, receive, canonical validation/WAL,
typed full publications; `dgft.py`: admission predicate/state replacement;
`row_lifecycle.py`/`row_stream.py`: immutable row/batch provenance and lease;
`continuity_proof.py`: owner-side complete exact private chain;
`certified_display.py`: D1 and actual local FIFO Consumer;
`durable_journal.py`: sync, prefix replay, epoch and request/receipt identity;
`late_delivery.py`: N1 diagnostic ordering only, not a new permission source.
Code identities are in N1_SOURCE_MANIFEST and P0_CORE_SOURCE_COMPARISON, not old
line numbers. Enumeration-to-code correspondence still requires its own audit.
