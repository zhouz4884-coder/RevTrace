"""Shared decode-exit actuator policies under the complete feedback protocol.

Only observed coverage or an explicitly retired generation is known useless.
Older parent alone is deliberately a conservative comparison, not Retire.
No prediction, injection label or future output is a policy input.
"""
from copy import deepcopy
import hashlib
from .kernel_runtime import KernelEnvelopeScheduler
from .composed_kernel import sha,Denied

POLICIES=('row_complete','no_cancel','watchdog','parent','covered','causal')


def reason_for(policy,job,*,frontier,parent,generation,now,started,watchdog_seconds):
    if policy not in POLICIES:raise ValueError('unknown physical retirement policy')
    if job['role']!='proposal' or policy in ('row_complete','no_cancel'):return None
    if policy=='watchdog':
        return 'watchdog-timeout' if started is not None and now>=started+watchdog_seconds else None
    if policy=='parent':return 'parent-version-superseded' if parent>job['parent'] else None
    if frontier>=job['audio_end_sample']:return 'trusted-coverage'
    if policy=='causal' and generation!=job['branch_generation']:return 'retired-generation'
    return None


class RetirementScheduler(KernelEnvelopeScheduler):
    def __init__(self,**kwargs):
        options=dict(kwargs['contract']['physical_retirement'])
        self.retirement_policy=options['policy']
        self.watchdog_seconds=float(options['watchdog_seconds'])
        if self.retirement_policy not in POLICIES or self.watchdog_seconds<=0:raise ValueError('invalid frozen exit policy')
        self._retirement_requested=set();self._cancelled_jobs=set()
        super().__init__(**kwargs)

    def _make_job(self,s,role):
        job=super()._make_job(s,role)
        fixture=self.contract.get('retirement_fault_fixture')
        key=f'{s.sid}:{job["end_window"]}'
        if role=='proposal' and fixture and key in fixture['fault_plan']:
            if job['chunk_id']<2:raise ValueError('fault fixture requires actual feedback consumption')
            target=fixture['targets'][key]
            if (job['source_id'],job['chunk_id'],int(fixture['fault_plan'][key]))!=(target['source_id'],target['chunk_id'],target['donor_index']):
                raise ValueError('actual input fixture target/source/chunk changed')
            donor=fixture['donors'][int(fixture['fault_plan'][key])%len(fixture['donors'])]
            job['fault_actual_prompt_tokens']=list(donor['tokens'])
            self._event('F2-injection-issued',job_id=job['job_id'],session_id=s.sid,window=job['end_window'],
                donor_id=donor.get('id'),donor_index=int(fixture['fault_plan'][key]),
                actual_prompt_sha256=sha(donor['tokens']),scope='controlled actual model-input substitution; no output mutation')
        return job

    def _tick(self):
        super()._tick()
        self._request_retirement()

    def _commit_ready(self):
        super()._commit_ready()
        # A current trusted installation is immediately observable here.
        self._request_retirement()

    def _request_retirement(self):
        now=self.clock()
        for name,(worker,ids) in list(self.inflight.items()):
            if not hasattr(worker,'cancel_job'):continue
            for jid in ids:
                if jid in self._retirement_requested or jid in self._cancelled_jobs:continue
                job=self.jobs[jid]
                if job['role']!='proposal' or jid in worker.inbox.seen:continue
                s=self.sessions[job['session_id']]
                started=getattr(worker,'_retirement_started_perf',None)
                if started is not None and started<job['enqueue_perf']:started=None
                reason=reason_for(self.retirement_policy,job,frontier=s.state.audio_frontier_window,
                    parent=s.state.checkpoint_id,generation=s.branch_generation,now=now,
                    started=started,watchdog_seconds=self.watchdog_seconds)
                if reason is None:continue
                if reason=='watchdog-timeout':invalidated=started+self.watchdog_seconds
                elif reason=='retired-generation':
                    invalidated=min(self.t0+e['time'] for e in self.events if e['kind']=='private-generation-retired'
                        and e['session_id']==s.sid and e['generation']>job['branch_generation']
                        and self.t0+e['time']>=job['enqueue_perf'])
                else:
                    eligible=[e for e in self.events if e['kind']=='commit' and e['session_id']==s.sid and
                        (e['audio_end_sample']>=job['audio_end_sample'] if reason=='trusted-coverage' else e['version']>job['parent'])]
                    invalidated=min(self.t0+e['installed'] for e in eligible)
                identity=sha({k:v for k,v in job.items() if k!='_delivery'})
                self.kernel.event('owner-retirement-intent','cancel-request',jid,
                    dict(id=jid,worker=name,identity=identity,reason=reason,requested_perf=now))
                audit=worker.cancel_job(jid,reason,requested_perf=now)
                self._retirement_requested.add(jid)
                evidence=dict(job_id=jid,session_id=s.sid,worker=name,
                    observed_current_F=s.state.audio_frontier_window,current_parent=s.state.checkpoint_id,
                    job_generation=job['branch_generation'],current_generation=s.branch_generation,
                    invalidation_kind=reason,invalidated_perf=invalidated,
                    watchdog_seconds=self.watchdog_seconds,
                    execution_started_perf=started)
                self._event('cancel-request',**{**{k:v for k,v in audit.items() if k!='kind'},**evidence})

    def _accept_cancelled(self,name,audit):
        jid=audit['job_id'];job=self.jobs[jid];s=self.sessions[job['session_id']]
        if jid in self._cancelled_jobs:raise Denied('duplicate owner cancellation terminal')
        binding=audit['binding']
        if job['role']!='proposal' or binding['job_id']!=jid:raise Denied('invalid owner cancellation target')
        message=audit['message'];now=self.clock();audit=dict(audit,received_perf=now)
        self.kernel.event('actual-private-safe-point','row-cancelled',jid,dict(id=jid,worker=name,
            identity=sha({k:v for k,v in job.items() if k!='_delivery'}),reason=audit['reason'],
            request_id=audit['request_id'],terminal_digest=audit['terminal_digest'],
            requested_perf=audit['requested_perf'],acknowledged_perf=audit['acknowledged_perf'],
            emitted_perf=audit['emitted_perf'],decoded_tokens=audit['decoded_tokens']))
        self._cancelled_jobs.add(jid)
        s.fine_busy=False
        self._account_window(s,job['end_window'],'cancelled-private-inflight')
        s.fine_window=max(s.fine_window,job['end_window']+1)
        self._event('row-cancelled',**{**{k:v for k,v in audit.items() if k!='kind'},
            'session_id':s.sid,'received_perf':now,'window':job['end_window'],
            'audio_end_sample':job['audio_end_sample'],'physical_worker_released':False})
        self._event('worker-cancelled-record',job=deepcopy(job),cancellation=deepcopy(audit))
        # This does not release a physical lease or install state.
        self._reconcile_covered_windows(s)
