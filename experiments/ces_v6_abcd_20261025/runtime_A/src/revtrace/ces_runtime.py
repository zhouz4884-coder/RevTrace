"""Evidence-choice owner using unmodified admission, D1, WAL and row leases."""
import math,time
from dataclasses import replace
from .live_qwen import LiveQwenScheduler
from .online_admission import gate_candidate,target_identity
from .ces_policy import Target,choose,cost
from .certified_display import ConsumerAck
from .ces_closed_loop_owner import ClosedLoopOwnerMixin,CLOSED_MODES

V5_MODES={'risk_cost','progress','progress_joint'}
FEATURE_MODES=V5_MODES|CLOSED_MODES

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

class CESScheduler(ClosedLoopOwnerMixin,LiveQwenScheduler):
    def __init__(self,**kwargs):
        self.ces=kwargs['contract']['ces_study'];self.mode=self.ces['method'];self.cal=self.ces['calibration']
        self.consumer_ack_source=kwargs.pop('consumer_ack_source',None)
        self._pending_acks=[];self._seen_ack_sequences=set();self._first_visible={}
        self._row_completed=set();self.reject_observations={};self.ack_counts={'accepted':0,'duplicate':0,'wrong_identity':0};self.ack_wall_total=0.
        self.proposer_order=self.ces.get('proposer_order','deadline' if self.mode=='progress_joint' else 'ready')
        if self.proposer_order not in ('ready','deadline'):raise ValueError('unknown proposer order')
        if self.mode in FEATURE_MODES and not callable(self.consumer_ack_source):raise ValueError('V5 requires actual Consumer ACK source')
        self.last_reject={};self.observed=set();self.selected={};self.wait_until=0.;self.wait_started={}
        self.decision_attempts=0;self.feature_wall_total=0.;self.planner_wall_total=0.
        super().__init__(**kwargs)
        if self.fine!=2 or self.rho!=1:raise ValueError('CES frozen fine/rho required')
        self._closed_init()

    def _event(self,kind,**fields):
        if kind=='executor-complete':self._row_completed.add(fields['job_id'])
        if kind=='worker-status' and hasattr(self,'_closed_worker_started'):
            self._closed_worker_event(fields)
        emitted=super()._event(kind,**fields)
        if kind=='commit' and hasattr(self,'closed_state'):
            self._closed_installed(fields)
        return emitted

    def _drain_consumer_acks(self,now):
        started=time.perf_counter()
        if self.consumer_ack_source is not None:self._pending_acks.extend(self.consumer_ack_source())
        pending=[]
        for ack in self._pending_acks:
            if not isinstance(ack,ConsumerAck):raise ValueError('untyped Consumer progress message')
            if ack.observed_perf>now:
                pending.append(ack);continue
            s=self.sessions.get(ack.session_id)
            if (ack.owner_incarnation!=self.t0 or ack.contract_digest!=self.contract_digest or
                s is None or ack.canonical_epoch!=s.state.contract_epoch):
                self.ack_counts['wrong_identity']+=1;continue
            if ack.sequence in self._seen_ack_sequences:
                self.ack_counts['duplicate']+=1;continue
            if (ack.observed_perf<self.t0 or ack.valid_visible_frontier<0 or
                ack.valid_visible_frontier>len(s.audio)//4 or ack.certified_frontier>ack.valid_visible_frontier):
                raise ValueError('invalid actual Consumer progress bounds')
            self._seen_ack_sequences.add(ack.sequence);self.ack_counts['accepted']+=1
            # First legal visibility is historical: a later retraction cannot
            # erase it. Current canonical publication alone never creates it.
            for window in range(1,math.ceil(s.duration/self.fine)+1):
                frontier=round(min(self._end_seconds(s,window),s.duration)*self.sample_rate)
                if frontier>ack.valid_visible_frontier:break
                if ack.observed_perf+1e-7<self._ready_time(s,window):raise ValueError('Consumer ACK precedes audio release')
                key=(s.sid,window)
                self._first_visible[key]=min(self._first_visible.get(key,float('inf')),ack.observed_perf)
            self._event('ces-consumer-ack',**vars(ack),ack_received_perf=self.clock())
        self._pending_acks=pending
        self.ack_wall_total+=time.perf_counter()-started

    def _display_status(self,s,window,now):
        deadline=self._ready_time(s,window)+self.ces['display_slo']
        applied=self._first_visible.get((s.sid,window))
        met=applied is not None and applied<=deadline
        return met,not met and now>deadline

    def _order_proposals(self,ready,now):
        if self.proposer_order=='ready':return ready
        # Already late/covered work retains progress through a stable FIFO
        # aging bound. The finite released pool cannot starve forever.
        def key(s):
            released=self._ready_time(s,s.fine_window)
            met,expired=self._display_status(s,s.fine_window,now)
            aged=now-released>=self.ces['commit_slo']
            return (0 if aged else (1 if not met and not expired else 2),
                    released+self.ces['display_slo'],s.sid)
        return sorted(ready,key=key)

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
        private=[self.jobs[i] for _,ids in self.inflight.values() for i in ids if i not in self._row_completed and self.jobs[i]['role']=='proposal' and self.jobs[i]['session_id']==s.sid]
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
        base=Target(s.sid,s.segment_end,self._ready_time(s,s.segment_end),
          self._ready_time(s,s.segment_end)+self.ces['commit_slo'],bool(r),
          bool(j and j['parent']==s.state.checkpoint_id and j['prompt_tokens']==list(s.state.prompt_tokens)),
          self.last_reject.get(s.sid,False),len(r['token_ids']) if r else 0,len(descendants),
          sum(max(0.,now-j['enqueue_perf']) for j in descendants),eta,projection_compatible,
          min(self._end_seconds(s,s.segment_end),s.duration),
          min(self._end_seconds(s,s.segment_end),s.duration)-s.state.audio_frontier_window/self.sample_rate,
          len(s.state.prompt_tokens))
        if self.mode not in FEATURE_MODES:return base
        from .ces_v5_policy import V5Target
        previous=self.reject_observations.get(s.sid)
        rejection_age=max(0.,now-previous['observed_perf']) if previous and previous['rejected'] else None
        # A rejected result is a recent observation, not a permanent session
        # property. Parent changes and elapsed time weaken this cost feature.
        active_reject=bool(previous and previous['rejected'] and
            s.state.checkpoint_id<=previous['parent']+1 and rejection_age<=self.ces['commit_slo'])
        met,expired=self._display_status(s,s.segment_end,now)
        return V5Target(**dict(vars(base),previous_reject=active_reject),
            display_met=met,display_expired=expired,audio_weight=base.interval_seconds,
            reject_age_seconds=rejection_age)

    def _dispatch(self):
        self._drain_consumer_acks(self.clock())
        for role,workers in self.executors.items():
            idle=[w for w in workers if w.name not in self.inflight]
            if not idle:continue
            for worker in idle:
                ready=super()._ready(role)
                if role=='authority' and self.mode=='strict':
                    ready=[s for s in ready if (s.sid,s.segment_end) in self._proposal_results]
                if not ready:continue
                limit=int(self.contract['microbatch'])
                if role=='proposal':chosen=self._closed_proposal_selection(ready,self.clock())[:limit]
                else:
                    self._drain_consumer_acks(self.clock())
                    now=self.clock()
                    if now<self.wait_until:continue
                    feature_started=time.perf_counter()
                    features=[] if self.mode in ['fine','standard'] else [self._features(s,now) for s in ready]
                    features=[replace(t,candidate_eta=None) if now-self.wait_started.get((t.sid,t.window),now)>=self.ces['wait_cap'] else t for t in features]
                    feature_wall=time.perf_counter()-feature_started
                    plan_started=time.perf_counter()
                    if self.mode in ['fine','standard']:
                        decision={'operation':'generate','sids':[s.sid for s in ready[:limit]],'reason':'fixed-independent-no-predictor'}
                    elif self.mode in CLOSED_MODES:
                        decision=self._closed_choose(features,now,limit)
                    elif self.mode in V5_MODES:
                        from .ces_v5_policy import choose_v5
                        decision=choose_v5(features,now=now,mode=self.mode,cal=self.cal,limit=limit,
                          display_slo=self.ces['display_slo'],wait_cap=self.ces['wait_cap'])
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
                if role=='authority' and self.mode in CLOSED_MODES:
                    self._closed_dispatched(decision)
                self._event('batch-dispatched',worker=worker.name,role=role,job_ids=[j['job_id'] for j in jobs])

    def _commit_ready(self):
        for s in self.sessions.values():
            if s.done or s.auth_done or s.auth_result is None:continue
            r=s.auth_result;j=self.jobs[r['job_id']];validate_evidence(j,r,self.contract)
            if j['job_id'] not in self.observed:
                self.observed.add(j['job_id'])
                if j['ces_operation']=='verify':
                    rejected=not r['online_verification']['candidate_accepted']
                    self.last_reject[s.sid]=rejected
                    self.reject_observations[s.sid]={'rejected':rejected,'observed_perf':self.clock(),
                        'parent':j['parent'],'job_id':j['job_id'],'end_window':j['end_window']}
                elif self.mode in FEATURE_MODES:
                    # A fresh independent transition ends the previous
                    # verifier episode. It does not predict future acceptance.
                    self.reject_observations.pop(s.sid,None)
        return super()._commit_ready()

    def run(self):
        result=super().run()
        result['CES_host_cost']={'decision_attempts':self.decision_attempts,
          'feature_wall_seconds':self.feature_wall_total,'planner_wall_seconds':self.planner_wall_total,
          'scope':'actual owner wall, all attempted decisions including waits; not CPU energy'}
        result['CES_consumer_ack']=dict(self.ack_counts,first_visible_frontiers=len(self._first_visible),
            pending_future_observations=len(self._pending_acks),proposer_order=self.proposer_order,
            owner_ack_wall_seconds=self.ack_wall_total,
            scope='actual local Consumer applied observations; scheduling telemetry, never admission evidence')
        if self.mode in CLOSED_MODES:
            result['CES_closed_loop']={'mode':self.mode,'observed_credit_audio':self._closed_observed_credit(),
                'service_book':self.closed_state.to_audit(),'config':self.ces.get('closed_loop_config',{}),
                'proposer_policy':self.closed_proposer_policy,'actual_proposer_choice_events':self._closed_proposer_dispatches,
                'released_successor_planning_online':True,'future_jobs_not_issued_from_predictions':True}
        return result
