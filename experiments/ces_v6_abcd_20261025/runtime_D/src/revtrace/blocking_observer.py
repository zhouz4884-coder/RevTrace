"""Event-driven descriptive wait intervals, never a causal attribution oracle."""
import math

class BlockingObserver:
    def __init__(self,scheduler):
        self.s=scheduler;self.open={};self.last_signature=None
    def update(self,force=False,finish=False):
        s=self.s;now=s.clock();elapsed=now-s.t0
        signature=(len(s.events),int(elapsed//s.fine),getattr(s,'_wal_active',False))
        if not force and signature==self.last_signature:return
        active={};authority=s.executors['authority']
        issued_targets={(j['session_id'],j['audio_end_sample']) for j in s.jobs.values() if j['role']=='authority'}
        occupied=[w for w in authority if w.name in s.inflight]
        batch={w.name:list(s.inflight[w.name][1]) for w in occupied}
        for session in s.sessions.values():
            total=math.ceil(session.duration/s.fine)
            for target in range(session.resumed_start_window+s.rho,total+s.rho,s.rho):
                target=min(target,total);end=round(s._end_seconds(session,target)*s.sample_rate)
                release=s._ready_time(session,target)
                if release>now or end<=session.state.audio_frontier_window:continue
                if (session.sid,end) in issued_targets:continue
                own=[j for ids in batch.values() for j in ids if s.jobs[j]['session_id']==session.sid]
                other=[j for ids in batch.values() for j in ids if s.jobs[j]['session_id']!=session.sid]
                # A dispatch is capacity occupancy, not evidence of execution.
                executing=[];exec_unknown=False
                for w in occupied:
                    ids=batch[w.name]
                    if any(j in own for j in ids):
                        phase=getattr(w,'execution_phase',None)
                        # Start telemetry is not a continuous execution oracle:
                        # the batch could finish before its completion is polled.
                        if phase not in ['completed','delivery-hold','idle']:exec_unknown=True
                barrier=(s.contract.get('proposal_barrier','segment')=='segment' and
                         session.auth_result is not None and session.fine_end_result is None)
                bits={'self_inflight':session.auth_busy,
                    'self_exec_on_gpu':None if exec_unknown else bool(executing),
                    'commit_pending':session.auth_result is not None,'barrier_hold':barrier,
                    'candidate_missing':s.contract.get('verification_policy')=='grouped_replay' and (session.sid,target) not in s._proposal_results,
                    'worker_capacity_occupied':len(occupied)==len(authority),
                    'other_session_jobs_on_worker':bool(other),
                    'coordinator_wal_sync':None if getattr(s,'_wal_active',False) else False,
                    'owner_wal_call':getattr(s,'_wal_active',False),
                    'parent_uninstalled':target!=session.segment_end,'scheduler_delay':False}
                bits['scheduler_delay']=not any(v for k,v in bits.items() if k not in ['self_exec_on_gpu','scheduler_delay'])
                value={'session_id':session.sid,'target_window':target,'audio_end_sample':end,
                    'audio_release':release-s.t0,'committed_frontier':session.state.audio_frontier_window,
                    'committed_version':session.state.checkpoint_id,'bitmap':bits,
                    'batch_members':batch,'own_job_ids':own,'other_job_ids':other,
                    'scope':'overlapping descriptive occupancy; UNKNOWN execution until worker telemetry; not causal fractions'}
                active[session.sid,target]=value
        if finish:active={}
        for key,old in list(self.open.items()):
            if key not in active or active[key]!=old['value']:
                self.emit(old['value'],old['start'],elapsed);del self.open[key]
        for key,value in active.items():
            if key not in self.open:self.open[key]={'value':value,'start':max(value['audio_release'],elapsed)}
        self.last_signature=(len(s.events),int(elapsed//s.fine),getattr(s,'_wal_active',False))
    def emit(self,value,start,end):
        if end<=start:return
        row={'kind':'authority-wait-interval','time':end,'entered':start,'exited':end,
             'duration':end-start,**value}
        self.s.events.append(row);self.s.emit(row)
