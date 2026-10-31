"""Observe original coordinator proposals/registrations; never change a proposal.

The unmodified Owner still owns sid/slot iteration and dispatch. An observation
is not an actual dispatch: the independent audit must bind it to dispatch.jsonl
and an actual same-UID physical worker result. Both arms use this same wrapper.
"""
from __future__ import annotations
import copy,pathlib,time
from common import need

def attach_observer(cls,accepted,sources,emit,clock=time.perf_counter):
    original_next=cls.next_full_start;original_register=cls.register;pending={};counter=0
    def observed_next(self,sid,accepted_frontier,*args,**kwargs):
        nonlocal counter
        accepted_before={k:int(v.value) for k,v in accepted.items()};before=clock()
        proposal=original_next(self,sid,accepted_frontier,*args,**kwargs)
        if proposal is not None:
            counter+=1;pending[id(self)]=dict(proposal_id=counter,proposal_before_perf=before,proposal_after_perf=clock(),source_id=sid,start=proposal,accepted_argument=accepted_frontier,accepted_before=accepted_before)
        return proposal
    def observed_register(self,**kwargs):
        before=clock();sid=kwargs['source_id'];start=kwargs['start'];proposal=pending.pop(id(self),None)
        if proposal is not None:
            need(proposal['source_id']==sid and proposal['start'] is start,'observed proposal not the original registered object')
        # All operations below inspect state. In particular, never call the
        # scheduler on another sid (next_full_start refreshes original state).
        accepted_before=proposal['accepted_before'] if proposal else {k:int(v.value) for k,v in accepted.items()}
        decision_snapshot_perf=proposal['proposal_before_perf'] if proposal else clock()
        canonical={k:copy.deepcopy(self.canonical(k).state) for k in sources}
        live=[copy.deepcopy(dict(job_id=j['job_id'],source_id=j['source_id'],dispatch_epoch=j['dispatch_epoch'],start=j['start'].state,end=j['end'])) for j in self.jobs.values()]
        completed=[copy.deepcopy(dict(job_id=x['job']['job_id'],source_id=x['job']['source_id'],dispatch_epoch=x['job']['dispatch_epoch'],start=x['job']['start'].state,end=x['job']['end'])) for x in self.completed_full.values()]
        epochs=dict(self.epochs);is_current=start.same(self.canonical(sid))
        job=original_register(self,**kwargs)
        emit(dict(kind='observed_original_registration',owner_epoch=getattr(self,'owner_epoch',0),job_id=job['job_id'],worker=kwargs['worker'],worker_incarnation=kwargs.get('worker_incarnation'),source_id=sid,start=copy.deepcopy(start.state),end=kwargs['end'],dispatch_epoch=job['dispatch_epoch'],original_dispatched_perf=kwargs['dispatched_perf'],registration_before_perf=before,registration_after_perf=clock(),decision_snapshot_perf=decision_snapshot_perf,proposal_id=proposal['proposal_id'] if proposal else None,proposal_before_perf=proposal['proposal_before_perf'] if proposal else None,proposal_after_perf=proposal['proposal_after_perf'] if proposal else None,accepted_argument=proposal['accepted_argument'] if proposal else None,started_on_current_canonical=is_current,canonical_cuts=canonical,accepted_before=accepted_before,session_epochs=epochs,live_jobs_before=live,completed_jobs_before=completed))
        return job
    cls.next_full_start=observed_next;cls.register=observed_register
    def restore():cls.next_full_start=original_next;cls.register=original_register
    return restore

def observed_owner_main(config,manifest,out,epoch,control,publication,accepted,origin,initials_hint):
    import resilience_owner as original
    from native_service import Journal
    path=pathlib.Path(out)/('OWNER_OBSERVATIONS_e%d.jsonl'%epoch);log=Journal(path)
    restore=attach_observer(original.ResilientFullSpecCoordinator,accepted,{s['source_id']:s for s in config['settings']['sources']},log.write)
    try:return original.owner_main(config,manifest,out,epoch,control,publication,accepted,origin,initials_hint)
    finally:restore();log.close()
