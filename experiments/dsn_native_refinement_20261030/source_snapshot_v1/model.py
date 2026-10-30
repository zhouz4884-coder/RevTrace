"""Executable specification of owned full-call refinement (finite symbolic cuts).

This is a specification model, not extracted Python/CUDA verification. A bit
stands for a COMPLETE opaque feedback state: equal text is deliberately weaker.
Original C/U is a nondeterministic allowed relation, never a fixed replay oracle.
"""
from dataclasses import dataclass, replace
from collections import deque

@dataclass(frozen=True, order=True)
class Cut:
    frontier: int
    state: int

@dataclass(frozen=True)
class Step:
    job_id: int
    start: Cut
    end: Cut

@dataclass(frozen=True)
class Job:
    job_id: int
    worker: int
    incarnation: int
    epoch: int
    birth: Cut
    start: Cut
    target: int
    dependencies: tuple
    phase: str = "running"
    projection: Cut | None = None
    result: Cut | None = None
    choice: int | None = None
    receipt_owned: bool = False

@dataclass(frozen=True)
class Record:
    transition_id: int
    job_id: int
    start: Cut
    end: Cut
    authorized_epoch: int
    authorized_incarnation: int

@dataclass(frozen=True)
class Publication:
    kind: str
    epoch: int
    root: Cut
    steps: tuple = ()
    transition_id: int = 0
    replay: bool = False

@dataclass(frozen=True)
class State:
    canonical: Cut = Cut(0,0)
    canonical_index: int = 0
    epoch: int = 0
    jobs: tuple = ()
    steps: tuple = ()
    witnesses: tuple = (Cut(0,0),)
    worker_incarnations: tuple = (0,0)
    worker_states: tuple = ("up","up")
    records: tuple = ()
    transaction: tuple | None = None       # (job_id, "prepared" or "synced")
    publications: tuple = ()
    consumer_canonical: Cut = Cut(0,0)
    consumer_steps: tuple = ()
    consumer_epoch: int = 0
    owner_alive: bool = True
    writes_blocked: bool = False
    faults: int = 0
    issued: int = 0
    accepted: int = 2
    original_clocks: tuple = (0,1,2)
    clocks: tuple = (0,1,2)
    dispatch_evidence: tuple = ()

class Violation(AssertionError):
    pass

def need(ok, reason):
    if not ok:
        raise Violation(reason)

def tail(canonical, steps):
    return steps[-1].end if steps else canonical

def path_cuts(canonical, steps):
    cuts=[canonical];last=canonical
    for step in steps:
        need(step.start==last, "gapped_whole_provisional_path")
        need(step.end.frontier>step.start.frontier, "nonadvancing_provisional_path")
        cuts.append(step.end);last=step.end
    return tuple(cuts)

def reconcile(steps, new):
    for index, step in enumerate(steps):
        if step.end.frontier==new.frontier:
            return steps[index+1:] if step.end==new else ()
    return ()

def job_at(s, job_id):
    return next(j for j in s.jobs if j.job_id==job_id)

def set_job(s, job):
    return replace(s,jobs=tuple(job if j.job_id==job.job_id else j for j in s.jobs))

def input_status(s, j):
    """Input truth is separate from coverage and physical/epoch authority."""
    actual=next((w for w in s.witnesses if w.frontier==j.start.frontier),None)
    return "UNKNOWN" if actual is None else ("CONFIRMED" if actual==j.start else "REFUTED")

def invalidity(s, j):
    if j.epoch!=s.epoch:
        return "epoch_changed"
    if j.phase in ("running","finished") and j.incarnation!=s.worker_incarnations[j.worker]:
        return "incarnation_changed"
    if input_status(s,j)=="REFUTED":
        return "actual_same_frontier_complete_input_mismatch"
    if j.target<=s.canonical.frontier:
        return "covered_without_remaining_use"
    return None

def original_cu(start, target, choice):
    """A permitted ORIGINAL transition can vary by protected execution choice."""
    need(choice in (0,1), "not_an_original_execution_choice")
    return Cut(target,(start.state+choice)%2)

def same_text(a,b):
    # Hidden cursor/state may differ at equal frontier despite equal visible text.
    return a.frontier==b.frontier

def is_busy(s, worker):
    return any(j.worker==worker and j.phase in ("running","finished") for j in s.jobs)

def has_work(s, start, target):
    return any(j.phase in ("running","finished","buffered") and j.start==start
               and j.target==target and invalidity(s,j) is None for j in s.jobs)

def current_result(s, j):
    return (j.phase=="buffered" and j.result is not None
            and j.start==s.canonical and invalidity(s,j) is None)

def dispatch(s, worker, start, max_issued=4):
    need(s.owner_alive and not s.writes_blocked, "owner_not_writable")
    need(s.transaction is None and not any(current_result(s,j) for j in s.jobs), "ready_parent_commit_precedes_dispatch")
    need(s.worker_states[worker]=="up" and not is_busy(s,worker), "physical_worker_not_released")
    need(s.issued<max_issued, "bounded_issue_cutoff")
    need(start in path_cuts(s.canonical,s.steps), "start_not_on_current_conditional_path")
    target=start.frontier+1
    need(target<=s.accepted and not has_work(s,start,target), "duplicate_or_unaccepted_input")
    j=Job(s.issued,worker,s.worker_incarnations[worker],s.epoch,s.canonical,start,target,
          path_cuts(s.canonical,s.steps)[:path_cuts(s.canonical,s.steps).index(start)+1])
    evidence=(j.job_id,j.worker,j.incarnation,j.epoch,j.birth,j.start,j.target,j.dependencies)
    return replace(s,jobs=s.jobs+(j,),issued=s.issued+1,
                   dispatch_evidence=s.dispatch_evidence+(evidence,))

def project(s, jid, state):
    j=job_at(s,jid);need(j.phase=="running" and j.projection is None,"ASR_not_owned_active")
    need(j.epoch==s.epoch and j.incarnation==s.worker_incarnations[j.worker],"ASR_fenced")
    end=Cut(j.target,state);out=set_job(s,replace(j,projection=end))
    if j.start==tail(s.canonical,s.steps) and end.frontier>s.canonical.frontier:
        steps=s.steps+(Step(jid,j.start,end),)
        pub=Publication("private",s.epoch,s.canonical,steps)
        out=replace(out,steps=steps,publications=out.publications+(pub,))
    return out

def execute_original(s,jid,choice):
    j=job_at(s,jid);need(j.phase=="running" and s.worker_states[j.worker]=="up","C_U_not_executing")
    need(j.epoch==s.epoch and j.incarnation==s.worker_incarnations[j.worker],"C_U_fenced")
    # C-entry cancellation can race with completion. Both are lawful; neither
    # authorizes a partial result. A completed wrong result will be discarded.
    return set_job(s,replace(j,phase="finished",choice=choice,result=original_cu(j.start,j.target,choice)))

def replace_projection(steps,j,canonical):
    for i,step in enumerate(steps):
        if step.start==j.start and step.end.frontier==j.result.frontier:
            kept=list(steps[:i])+[Step(j.job_id,j.start,j.result)];last=j.result
            for successor in steps[i+1:]:
                if successor.start!=last:
                    break
                kept.append(successor);last=successor.end
            return tuple(kept)
    if j.start==tail(canonical,steps) and j.result.frontier>canonical.frontier:
        return steps+(Step(j.job_id,j.start,j.result),)
    return steps

def receive_full(s,jid):
    j=job_at(s,jid);need(j.phase=="finished","not_a_full_completion")
    # Old physical owner must have actually synchronized a terminal outcome.
    need(j.incarnation==s.worker_incarnations[j.worker],"old_worker_cannot_release_new_slot")
    out=set_job(s,replace(j,phase="discarded" if invalidity(s,j) else "buffered",receipt_owned=True))
    if invalidity(s,j) is None:
        out=replace(out,steps=replace_projection(out.steps,j,s.canonical))
        if j.start!=s.canonical:
            out=replace(out,publications=out.publications+(Publication("private",s.epoch,s.canonical,out.steps),))
    return out

def cancel(s,jid,proof=None,mutation=None):
    j=job_at(s,jid);need(j.phase=="running","no_owned_running_prefix")
    reason=invalidity(s,j)
    if mutation=="ancestor_mismatch_cancels_unknown":
        loss=any(w.frontier<j.start.frontier and any(d.frontier==w.frontier and d!=w for d in j.dependencies) for w in s.witnesses)
        reason=reason or ("ancestor_only" if loss else None)
    need(reason is not None,"UNKNOWN_input_is_not_an_invalidation_proof")
    need(reason!="ancestor_only","ancestor_mismatch_does_not_refute_future_complete_input")
    if proof is not None:
        need(proof==reason,"unbound_cancellation_proof")
    return set_job(s,replace(j,phase="cancelled"))

def prepare(s,jid,mutation=None):
    need(s.owner_alive and not s.writes_blocked and s.transaction is None,"owner_write_not_serial")
    j=job_at(s,jid);need(j.phase=="buffered" and j.result is not None,"no_full_C_U_result")
    if mutation!="commit_unknown_input":
        need(j.start==s.canonical and invalidity(s,j) is None,"unconfirmed_full_input")
    need(s.canonical_index==len(s.records),"cannot_write_before_prior_durable_install")
    return replace(s,transaction=(jid,"prepared"))

def sync_record(s):
    need(s.transaction is not None and s.transaction[1]=="prepared","no_prepared_transition")
    j=job_at(s,s.transaction[0]);need(s.owner_alive and not s.writes_blocked,"writes_stopped")
    # Guard against incorrect coordinator prepare/late completion mutations.
    need(j.start==s.canonical,"Canonical_input_not_current_complete_cut")
    need(j.epoch==s.epoch,"old_epoch_cannot_gain_new_write_permission")
    need(j.phase=="buffered" and j.receipt_owned,"complete_result_was_not_owned_before_worker_fence")
    need(j.choice is not None and j.result==original_cu(j.start,j.target,j.choice),"not_original_C_U")
    r=Record(len(s.records)+1,j.job_id,j.start,j.result,s.epoch,j.incarnation)
    return replace(s,records=s.records+(r,),transaction=(j.job_id,"synced"))

def install(s,mutation=None):
    need(s.transaction is not None,"no_prepared_transition")
    jid,phase=s.transaction;j=job_at(s,jid)
    need(phase=="synced" or mutation=="install_before_sync","Canonical_install_before_durable_record")
    need(j.start==s.canonical and j.epoch==s.epoch,"Canonical_parent_or_epoch_changed")
    steps=reconcile(s.steps,j.result)
    out=set_job(s,replace(j,phase="installed"))
    pub=Publication("canonical",s.epoch,j.result,steps,len(s.records))
    out=replace(out,canonical=j.result,canonical_index=len(s.records),transaction=None,
                steps=steps,witnesses=s.witnesses+(j.result,),publications=s.publications+(pub,Publication("private",s.epoch,j.result,steps)))
    return out

def apply_consumer(s,mutation=None):
    need(s.publications,"no_publication")
    p=s.publications[0];out=replace(s,publications=s.publications[1:])
    if p.epoch!=s.consumer_epoch:
        return out  # expected old publication: no new authority
    if p.kind=="private":
        need(p.root==s.consumer_canonical,"private_publication_wrong_applied_root")
        path_cuts(p.root,p.steps)
        if tail(p.root,p.steps).frontier>=tail(s.consumer_canonical,s.consumer_steps).frontier:
            out=replace(out,consumer_steps=p.steps)
        if mutation=="certify_private_projection":
            out=replace(out,consumer_canonical=tail(p.root,p.steps),consumer_steps=())
        need(out.consumer_canonical==s.consumer_canonical,"provisional_view_acquired_certification")
    else:
        need(1<=p.transition_id<=len(s.records),"publication_lacks_durable_original_fact")
        r=s.records[p.transition_id-1]
        need(r.end==p.root,"publication_changed_its_original_fact")
        if p.root.frontier<s.consumer_canonical.frontier:
            return out  # idempotent old durable-fact replay, never regress
        if p.root==s.consumer_canonical:
            return out
        expected=reconcile(s.consumer_steps,p.root)
        compatible=bool(expected) and tail(s.consumer_canonical,s.consumer_steps).frontier>p.root.frontier
        out=replace(out,consumer_canonical=p.root,consumer_steps=() if mutation=="snapshot_consumer" else expected)
        if compatible:
            need(tail(out.consumer_canonical,out.consumer_steps)==tail(s.consumer_canonical,s.consumer_steps),
                 "compatible_Canonical_application_withdrew_whole_view")
    return out

def fail_worker(s,worker):
    need(s.owner_alive and s.worker_states[worker]=="up","worker_not_live")
    states=list(s.worker_states);states[worker]="failed"
    return replace(s,worker_states=tuple(states),faults=s.faults+1)

def observe_exit(s,worker):
    need(s.worker_states[worker]=="failed","physical_exit_not_observed")
    states=list(s.worker_states);states[worker]="exited"
    jobs=tuple(replace(j,phase="lost") if j.worker==worker and j.phase in ("running","finished") else j for j in s.jobs)
    return replace(s,worker_states=tuple(states),jobs=jobs)

def restart_worker(s,worker):
    need(s.worker_states[worker]=="exited","cannot_reuse_before_observed_exit")
    inc=list(s.worker_incarnations);inc[worker]+=1
    states=list(s.worker_states);states[worker]="up"
    return replace(s,worker_incarnations=tuple(inc),worker_states=tuple(states))

def owner_crash(s):
    need(s.owner_alive,"owner_already_dead")
    return replace(s,owner_alive=False,writes_blocked=True,worker_states=("failed","failed"),
                   publications=(),faults=s.faults+1)

def recover(s,mutation=None):
    need(not s.owner_alive or s.writes_blocked,"no_recovery_needed")
    tip=s.records[-1].end if s.records else Cut(0,0);epoch=s.epoch+1
    pubs=tuple(Publication("canonical",epoch,r.end,(),r.transition_id,True) for r in s.records)
    clocks=(epoch,)+s.clocks[1:] if mutation=="reset_input_clocks" else s.clocks
    jobs=tuple(replace(j,phase="discarded") if j.phase=="buffered" else j for j in s.jobs)
    # The external Supervisor/Consumer survives. Epoch fencing explicitly
    # withdraws old provisional ownership, while already certified facts stay.
    return replace(s,canonical=tip,canonical_index=len(s.records),epoch=epoch,witnesses=(tip,),jobs=jobs,
                   steps=(),transaction=None,owner_alive=True,writes_blocked=False,
                   consumer_steps=(),consumer_epoch=epoch,
                   publications=pubs,clocks=clocks)

def receive_duplicate_or_late(s,jid,wire_epoch=None,wire_incarnation=None):
    j=job_at(s,jid)
    epoch=j.epoch if wire_epoch is None else wire_epoch
    incarnation=j.incarnation if wire_incarnation is None else wire_incarnation
    if epoch!=s.epoch or incarnation!=s.worker_incarnations[j.worker] or j.phase in ("installed","discarded","cancelled","lost"):
        return s, "LOCAL_REJECT_EXPECTED_STALE_OR_DUPLICATE"
    return s, "CURRENT_OWNED_RESULT_REQUIRES_NORMAL_VALIDATION"

def check(s):
    need(s.clocks==s.original_clocks,"accepted_input_clock_changed")
    need(s.accepted==len(s.original_clocks)-1,"accepted_input_obligation_lost")
    last=Cut(0,0);seen=set()
    for i,r in enumerate(s.records,1):
        j=job_at(s,r.job_id)
        need(r.transition_id==i and r.job_id not in seen,"duplicate_transition_identity")
        need(r.start==last and r.start==j.start,"original_transition_input_not_previous_fact")
        need(j.choice is not None and j.receipt_owned and r.end==j.result==original_cu(j.start,j.target,j.choice),"fact_not_original_C_U_output")
        need(r.authorized_epoch==j.epoch and r.authorized_incarnation==j.incarnation,"authority_reissued_to_fenced_job")
        seen.add(r.job_id);last=r.end
    cuts=(Cut(0,0),)+tuple(r.end for r in s.records)
    need(0<=s.canonical_index<len(cuts) and s.canonical==cuts[s.canonical_index],"Canonical_not_durable_prefix")
    need(s.consumer_canonical in cuts,"Consumer_certified_nonfact")
    if s.transaction is not None:
        prepared=job_at(s,s.transaction[0])
        need(prepared.start==s.canonical and prepared.epoch==s.epoch and prepared.receipt_owned,
             "prepared_transition_does_not_have_confirmed_owned_input")
    path_cuts(s.canonical,s.steps);path_cuts(s.consumer_canonical,s.consumer_steps)
    for j,e in zip(s.jobs,s.dispatch_evidence):
        need((j.job_id,j.worker,j.incarnation,j.epoch,j.birth,j.start,j.target,j.dependencies)==e,
             "birth_or_frozen_input_relabelled")
    for w in (0,1):
        owned=[j for j in s.jobs if j.worker==w and j.phase in ("running","finished")]
        need(len(owned)<=1,"physical_owner_double_allocated")
        need(all(j.incarnation==s.worker_incarnations[w] for j in owned),"old_physical_lease_reused")
    return True

def successors(s,max_issued=3,max_faults=0):
    if s.owner_alive:
        for worker in (0,1):
            if s.worker_states[worker]=="failed":
                yield f"observe_exit:{worker}",observe_exit(s,worker)
            elif s.worker_states[worker]=="exited":
                yield f"restart:{worker}",restart_worker(s,worker)
        if not s.writes_blocked:
            if s.issued<max_issued and s.transaction is None and not any(current_result(s,j) for j in s.jobs):
                for worker in (0,1):
                    if s.worker_states[worker]!="up" or is_busy(s,worker):
                        continue
                    for start in dict.fromkeys((s.canonical,tail(s.canonical,s.steps))):
                        if start.frontier<s.accepted and not has_work(s,start,start.frontier+1):
                            yield f"dispatch:{worker}:{start}",dispatch(s,worker,start,max_issued)
            for j in s.jobs:
                if j.phase=="running" and s.worker_states[j.worker]=="up" and j.epoch==s.epoch:
                    if j.projection is None and s.transaction is None:
                        for bit in (0,1):
                            yield f"ASR_projection:{j.job_id}:{bit}",project(s,j.job_id,bit)
                    for choice in (0,1):
                        yield f"original_CU:{j.job_id}:{choice}",execute_original(s,j.job_id,choice)
                    if invalidity(s,j):
                        yield f"cancel:{j.job_id}",cancel(s,j.job_id)
                elif j.phase=="finished" and s.transaction is None:
                    yield f"receive_full:{j.job_id}",receive_full(s,j.job_id)
                elif current_result(s,j) and s.transaction is None:
                    yield f"prepare:{j.job_id}",prepare(s,j.job_id)
            if s.transaction:
                if s.transaction[1]=="prepared":
                    yield "sync_original_transition",sync_record(s)
                else:
                    yield "install_durable_transition",install(s)
        if s.publications:
            yield "actual_Consumer_application",apply_consumer(s)
        if s.faults<max_faults:
            yield "Owner_process_crash",owner_crash(s)
            for worker in (0,1):
                if s.worker_states[worker]=="up":
                    yield f"worker_fail_stop:{worker}",fail_worker(s,worker)
    else:
        yield "recover_durable_facts_without_new_neural_work",recover(s)

def explore(*,frontiers=2,max_issued=3,max_depth=12,max_faults=0,state_cap=150000):
    initial=replace(State(),accepted=frontiers,original_clocks=tuple(range(frontiers+1)),clocks=tuple(range(frontiers+1)))
    queue=deque([(initial,0)]);seen={initial};edges=0;depth_cutoffs=0;terminals=0
    while queue:
        s,depth=queue.popleft();check(s)
        if s.canonical.frontier==frontiers:
            terminals+=1
        if depth==max_depth:
            depth_cutoffs+=1;continue
        for action,out in successors(s,max_issued,max_faults):
            check(out);edges+=1
            if out not in seen:
                need(len(seen)<state_cap,"state_cap_reached_before_declared_bound")
                seen.add(out);queue.append((out,depth+1))
    return dict(states=len(seen),edges=edges,depth_cutoffs=depth_cutoffs,
                terminal_states=terminals,max_depth=max_depth,frontiers=frontiers,
                max_issued=max_issued,max_faults=max_faults,
                guarantee="all explored states and enabled edges inside these finite bounds; not unbounded liveness or CUDA verification")

