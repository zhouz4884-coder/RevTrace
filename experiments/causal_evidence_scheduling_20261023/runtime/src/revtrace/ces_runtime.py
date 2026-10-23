"""Evidence-choice owner using unmodified admission, D1, WAL and row leases."""
import math,time
from dataclasses import replace
from .live_qwen import LiveQwenScheduler
from .online_admission import gate_candidate,target_identity
from .ces_policy import Target,choose,cost

def validate_evidence(job,result,contract):
    op=job.get('ces_operation')
    if op not in ['generate','verify']:raise ValueError('undeclared evidence mode')
    if result.get('ces_operation')!=op:raise ValueError('worker operation binding mismatch')
    proof=result.get('online_verification')
    if op=='generate':
        if proof is not None:raise ValueError('generation cannot masquerade as verification')
        audit=result.get('execution_context_audit',{})
        if audit.get('fault_override') or audit.get('executed_prompt_tokens')!=job['prompt_tokens'] or audit.get('actual_audio_sha256')!=job['prefix_audio_sha256']:
            raise ValueError('generation consumed wrong context/audio')
        return
    if not proof or proof['mode']!='strict' or proof['target_identity']!=target_identity(job):raise ValueError('wrong verification target')
    if proof['dtype']!='float32' or proof['context_override_used'] or proof['executed_prompt_tokens']!=job['prompt_tokens'] or proof['actual_audio_sha256']!=job['prefix_audio_sha256']:
        raise ValueError('untrusted correct-context evidence')
    if proof['fallback_used']:
        paid=proof.get('fallback_row_compute_seconds_so_far') if proof.get('row_completion_protocol') else proof['fallback_batch_seconds']
        if not proof['fallback_generated'] or not paid or paid<=0 or job['job_id'] not in proof['fallback_executed_job_ids']:raise ValueError('fallback absent/unpaid')
    else:
        ok,_=gate_candidate('strict',job['candidate_token_ids'],proof['predicted_token_ids'],proof['candidate_margins'],eos=proof['eos_token_ids'],budget=contract['authority_runtime']['max_new_tokens'])
        if not ok or result['token_ids']!=job['candidate_token_ids']:raise ValueError('incomplete token/stop verification')

class CESScheduler(LiveQwenScheduler):
    def __init__(self,**kwargs):
        self.ces=kwargs['contract']['ces_study'];self.mode=self.ces['method'];self.cal=self.ces['calibration']
        self.last_reject={};self.observed=set();self.selected={};self.wait_until=0.;self.wait_started={}
        self.decision_attempts=0;self.feature_wall_total=0.;self.planner_wall_total=0.
        super().__init__(**kwargs)
        if self.fine!=2 or self.rho!=1:raise ValueError('CES frozen fine/rho required')

    def _make_job(self,s,role):
        job=super()._make_job(s,role)
        if role=='proposal':
            # Exogenous session/frontier fault map. It is NOT a decision feature.
            entry=self.ces['fault_plan'].get(f'{s.sid}:{job["end_window"]}')
            if entry is not None and job['chunk_id']>=2:
                donor=self.ces['donors'][entry%len(self.ces['donors'])]
                job['fault_actual_prompt_tokens']=list(donor['tokens'])
                self._event('F2-injection-issued',job_id=job['job_id'],session_id=s.sid,end_window=job['end_window'],donor_id=donor['id'],controlled_fault=True)
            return job
        op=self.selected.pop(s.sid)
        job['ces_operation']=op
        if op=='verify':
            r=self._proposal_results.get((s.sid,s.segment_end))
            if r is None:raise ValueError('missing actual candidate, no speculative verify')
            origin=self.jobs[r['job_id']]
            if origin['audio_end_sample']!=job['audio_end_sample']:raise ValueError('candidate frontier mismatch')
            job.update(candidate_token_ids=list(r['token_ids']),candidate_state_tokens=list(r['state_tokens']),
              candidate_text=r['text'],candidate_origin_job_id=origin['job_id'],candidate_origin_parent=origin['parent'],
              candidate_origin_prompt_tokens=origin['prompt_tokens'],candidate_ready_perf=r['completed_perf'],online_selection_mode='strict')
        self._event('ces-operation-bound',job_id=job['job_id'],session_id=s.sid,operation=op,parent=job['parent'],end_window=job['end_window'])
        return job

    def _features(self,s,now):
        r=self._proposal_results.get((s.sid,s.segment_end));j=self.jobs[r['job_id']] if r else None
        private=[self.jobs[i] for _,ids in self.inflight.values() for i in ids if self.jobs[i]['role']=='proposal' and self.jobs[i]['session_id']==s.sid]
        descendants=[j for j in private if j['end_window']>s.segment_end]
        eta=None
        pending=[j for j in private if j['end_window']==s.segment_end]
        if pending:
            x=pending[0];batch=next(len(ids) for _,ids in self.inflight.values() if x['job_id'] in ids)
            eta=max(.001,cost(self.cal,'proposal',batch)-(now-x['enqueue_perf']))
        projection_compatible=False
        if r is not None and self.text_binding and self.mode in ['ces','causal_only']:
            try:
                target={'prompt_tokens':list(s.state.prompt_tokens),'chunk_id':s.segment_start,'language':s.language}
                potential,_=self.trusted_render(target,r['token_ids'])
                projection_compatible=potential==r['state_tokens']
            except ValueError:pass
        return Target(s.sid,s.segment_end,self._ready_time(s,s.segment_end),
          self._ready_time(s,s.segment_end)+self.ces['commit_slo'],bool(r),
          bool(j and j['parent']==s.state.checkpoint_id and j['prompt_tokens']==list(s.state.prompt_tokens)),
          self.last_reject.get(s.sid,False),len(r['token_ids']) if r else 0,len(descendants),
          sum(max(0.,now-j['enqueue_perf']) for j in descendants),eta,projection_compatible,
          min(self._end_seconds(s,s.segment_end),s.duration),
          min(self._end_seconds(s,s.segment_end),s.duration)-s.state.audio_frontier_window/self.sample_rate,
          len(s.state.prompt_tokens))

    def _dispatch(self):
        for role,workers in self.executors.items():
            idle=[w for w in workers if w.name not in self.inflight]
            if not idle:continue
            for worker in idle:
                ready=super()._ready(role)
                if role=='authority' and self.mode=='strict':
                    ready=[s for s in ready if (s.sid,s.segment_end) in self._proposal_results]
                if not ready:continue
                limit=int(self.contract['microbatch'])
                if role=='proposal':chosen=ready[:limit]
                else:
                    now=self.clock()
                    if now<self.wait_until:continue
                    feature_started=time.perf_counter()
                    features=[] if self.mode in ['fine','standard'] else [self._features(s,now) for s in ready]
                    features=[replace(t,candidate_eta=None) if now-self.wait_started.get((t.sid,t.window),now)>=self.ces['wait_cap'] else t for t in features]
                    feature_wall=time.perf_counter()-feature_started
                    plan_started=time.perf_counter()
                    if self.mode in ['fine','standard']:
                        decision={'operation':'generate','sids':[s.sid for s in ready[:limit]],'reason':'fixed-independent-no-predictor'}
                    else:
                        decision=choose(features,now=now,mode=self.mode,cal=self.cal,limit=limit,
                          display_slo=self.ces['display_slo'],wait_cap=self.ces['wait_cap'])
                    decision.update(observed_perf=now,planner_wall_seconds=time.perf_counter()-plan_started,feature_wall_seconds=feature_wall)
                    self.decision_attempts+=1;self.feature_wall_total+=feature_wall;self.planner_wall_total+=decision['planner_wall_seconds']
                    if decision['operation'] is None:
                        if decision.get('wait_seconds'):
                            for t in features:self.wait_started.setdefault((t.sid,t.window),now)
                            remaining=min(self.ces['wait_cap']-(now-self.wait_started[(t.sid,t.window)]) for t in features)
                            self.wait_until=now+min(remaining,decision['wait_seconds'])
                            self._event('ces-decision',features=[vars(t) for t in features],**decision)
                        continue
                    ids=set(decision['sids']);chosen=[s for s in ready if s.sid in ids]
                    self.selected.update({s.sid:decision['operation'] for s in chosen})
                    self._event('ces-decision',features=[vars(t) for t in features],**decision)
                jobs=[self._make_job(s,role) for s in chosen]
                for s in chosen:
                    if role=='proposal':s.fine_busy=True
                    else:s.auth_busy=True
                worker.submit(jobs);self.inflight[worker.name]=(worker,[j['job_id'] for j in jobs])
                self._event('batch-dispatched',worker=worker.name,role=role,job_ids=[j['job_id'] for j in jobs])

    def _commit_ready(self):
        for s in self.sessions.values():
            if s.done or s.auth_done or s.auth_result is None:continue
            r=s.auth_result;j=self.jobs[r['job_id']];validate_evidence(j,r,self.contract)
            if j['job_id'] not in self.observed:
                self.observed.add(j['job_id'])
                if j['ces_operation']=='verify':self.last_reject[s.sid]=not r['online_verification']['candidate_accepted']
        return super()._commit_ready()

    def run(self):
        result=super().run()
        result['CES_host_cost']={'decision_attempts':self.decision_attempts,
          'feature_wall_seconds':self.feature_wall_total,'planner_wall_seconds':self.planner_wall_total,
          'scope':'actual owner wall, all attempted decisions including waits; not CPU energy'}
        return result
