"""Readiness-only proposal seeds; current-input executor owns all selection.

Retired P results can propose tokens for a NEW authority operation. No old KV,
parent relabeling, new display or canonical write permission is introduced.
"""
from copy import deepcopy

class PrefixSeedMixin:
    def __init__(self,**kw):self.prefix_seed_registry={};super().__init__(**kw)
    def _accept_result(self,name,result):
        super()._accept_result(name,result)
        j=self.jobs[result['job_id']]
        if j['role']=='proposal' and result.get('text_binding'):
            self.prefix_seed_registry[j['job_id']]=dict(job=deepcopy(j),result=deepcopy(result),verified_ready=self.clock())
    def _make_job(self,s,role):
        j=super()._make_job(s,role)
        if role!='authority':return j
        eligible=[r for r in self.prefix_seed_registry.values() if r['job']['session_id']==j['session_id']
            and r['job']['source_id']==j['source_id'] and r['job']['contract_epoch']==j['contract_epoch']
            and r['job']['audio_end_sample']<=j['audio_end_sample'] and r['verified_ready']<=j['enqueue_perf']]
        seed=max(eligible,key=lambda r:(r['job']['audio_end_sample'],r['verified_ready'],r['job']['job_id']),default=None)
        j['prefix_seed']=dict(job_id=seed['job']['job_id'],state_tokens=list(seed['result']['state_tokens']),
            host_verified_perf=seed['verified_ready'],audio_end_sample=seed['job']['audio_end_sample'],
            complete_EOS=bool(seed['result']['terminated_by_eos'])) if seed else None
        self._event('prefix-seed-choice',job_id=j['job_id'],session_id=s.sid,seed=j['prefix_seed'],
            rule='ready HOST verified, latest <= target frontier; no target match oracle; no old-context KV')
        return j
