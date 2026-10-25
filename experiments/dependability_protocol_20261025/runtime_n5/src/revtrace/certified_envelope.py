"""Arrival-replay degradation with durable input obligations and no new writes.

Canonical selection/validation/installation remain the inherited audited core.
This module changes ingress credit and not-yet-issued private work only.
"""
from dataclasses import asdict
import hashlib,json,math,time
from .live_qwen import LiveQwenScheduler,fingerprint,quantile
from .degradation_state import CreditBook,Mode
from .input_debt_journal import InputJournal

class CertifiedEnvelopeScheduler(LiveQwenScheduler):
    METHODS={'fine_fair','dgft_original','standard_fair','queue_expiry','cde_age','cde_full','standard_cde'}
    def __init__(self,*,consumer,input_journal_path,**kwargs):
        self.options=dict(kwargs['contract']['envelope']);self.method=self.options['method']
        if self.method not in self.METHODS:raise ValueError('unfrozen envelope method')
        if kwargs['contract'].get('diagnostic_omit_receive_freshness') or kwargs['contract'].get('verification_policy')!='canonical_generate':
            raise ValueError('envelope does not bypass selection or introduce a candidate selector')
        self.origin=float(kwargs['contract']['episode_origin_perf']);self.consumer=consumer
        self._envelope_ready=False;self.input_journal=None;self.book=None;self.mode=Mode.RECOVERY
        self._stream_applied=False;self._acks={};self._last_input_signature=None;self._grant_cursor=0
        self._last_pressure=None;self._decision_cpu=0.;self._decision_host=0.;self._decision_count=0
        self._last_decision_pressure=None
        super().__init__(**kwargs)
        if self.origin>self.t0:raise ValueError('original arrival clock cannot be future')
        epochs={s.state.contract_epoch for s in self.sessions.values()}
        if len(epochs)!=1:raise ValueError('single owner epoch required')
        self.owner_epoch=epochs.pop();self.quantum=round(self.fine*self.rho*self.sample_rate)
        budget=round(float(self.options['budget_audio_seconds'])*self.sample_rate)
        if self.method=='dgft_original':budget=max(budget,sum(len(s.audio)//4+self.quantum for s in self.sessions.values()))
        if budget<self.quantum:raise ValueError('budget must fit one whole authority interval')
        try:
            self.input_journal=InputJournal(input_journal_path,manifest_sha256=self.contract['manifest_sha256'],
                policy_sha256=fingerprint({'envelope':self.options,'manifest':self.contract['manifest_sha256'],
                    'origin_perf':self.origin,'rho':self.rho,'sample_rate':self.sample_rate}))
            snap=self.input_journal.snapshot
            if snap:
                if snap['budget']!=budget:raise ValueError('input budget changed across recovery')
                self.book=CreditBook.restore(snap,{sid:s.state for sid,s in self.sessions.items()},
                    epoch=self.owner_epoch,origin_perf=self.origin)
            else:
                self.book=CreditBook(budget,epoch=self.owner_epoch)
                for sid,s in self.sessions.items():
                    if s.state.audio_frontier_window:raise ValueError('canonical history has no accepted-input ledger')
                    self.book.session(sid)
            for sid,s in self.sessions.items():
                b=self.book.session(sid)
                if b.accepted and hashlib.sha256(s.audio[:b.accepted*4]).hexdigest()!=b.accepted_prefix_sha256:
                    raise ValueError('accepted immutable input bytes unavailable or changed')
                if b.accepted>len(s.audio)//4:raise ValueError('input prefix beyond manifest')
                if s.auth_done and s.state.audio_frontier_window==len(s.audio)//4:
                    s.fine_window=math.ceil(s.duration/self.fine)+1
                if b.rejected:self._retire_rejected(s,b.rejection_reason)
            self._recovered_frontiers={sid:s.state.audio_frontier_window for sid,s in self.sessions.items()}
            self._envelope_ready=True
            self._set_mode(Mode.RECOVERY,force=True)
            self._event('input-ledger-recovered',epoch=self.owner_epoch,
                accepted={str(k):s.accepted for k,s in self.book.sessions.items()},
                certified={str(k):s.certified for k,s in self.book.sessions.items()},
                reserved={str(k):s.reserved for k,s in self.book.sessions.items()},
                discarded_partial_tail_bytes=self.input_journal.truncated_tail_bytes)
        except BaseException:
            self.close();raise

    def _ready_time(self,s,window):return self.origin+s.offset+self._end_seconds(s,window)
    def _reconcile_covered_windows(self,s):
        # Base recovery marks a fully committed session done without moving
        # its unused fine cursor. Never create a second process's outcomes for
        # windows already excluded by resumed_start_window.
        if s.done:return
        return super()._reconcile_covered_windows(s)
    def _retire_rejected(self,s,reason):
        if s.state.audio_frontier_window or s.fine_busy or s.auth_busy:raise ValueError('rejection cannot erase admitted/issued audio')
        for w in range(s.resumed_start_window+1,math.ceil(s.duration/self.fine)+1):
            if (s.sid,w) not in self.window_outcomes:self._account_window(s,w,'ingress-rejected')
        s.auth_done=True;s.done=True;s.fine_window=math.ceil(s.duration/self.fine)+1
        self._event('input-session-rejected',session_id=s.sid,reason=reason,certified_frontier=0)
    @staticmethod
    def _input_signature(book):
        return (book.epoch,tuple((sid,s.accepted,s.reserved,s.eof,s.rejected,s.rejection_reason,s.accepted_prefix_sha256)
            for sid,s in sorted(book.sessions.items())))
    def _consume_acks(self):
        for ack in self.consumer.drain_acks():
            if isinstance(ack,dict):
                if (ack.get('kind')=='stream-start-applied' and ack['owner_incarnation']==self.t0
                    and ack['contract_digest']==self.contract_digest):self._stream_applied=True
                continue
            if (ack.owner_incarnation,ack.contract_digest,ack.canonical_epoch)!=(self.t0,self.contract_digest,self.owner_epoch):
                raise ValueError('consumer observation from wrong owner/contract/epoch')
            if ack.session_id not in self.sessions:raise ValueError('unknown consumer session')
            prior=self._acks.get(ack.session_id)
            if prior and ack.sequence<=prior.sequence:raise ValueError('consumer observation order')
            self._acks[ack.session_id]=ack
            self.book.observe_consumer(ack.session_id,epoch=ack.canonical_epoch,
                canonical_version=ack.canonical_version,legal_frontier=ack.valid_visible_frontier)
    def _caught_up(self,frontiers):
        return self._stream_applied and all(F==0 or (sid in self._acks and self._acks[sid].certified_frontier>=F)
            for sid,F in frontiers.items())
    def _set_mode(self,mode,force=False):
        if not force and mode==self.mode:return
        old=self.mode;self.mode=mode
        self._event('envelope-mode',previous=old.value,current=mode.value)
        for sid,s in self.sessions.items():
            if mode in [Mode.CERTIFIED_ONLY,Mode.RECOVERY] and old not in [Mode.CERTIFIED_ONLY,Mode.RECOVERY]:
                s.branch_generation+=1;s.branch_tokens=s.state.prompt_tokens;s.branch_parent=s.state.checkpoint_id
                s.branch_root_tokens=s.state.prompt_tokens;s.branch_root_frontier=s.state.audio_frontier_window
                s.branch_chunk=s.segment_start
                self._event('private-generation-retired',session_id=sid,generation=s.branch_generation,
                    reason='certified-view-mode',physical_GPU_cancelled=False)
            s.display_revision+=1
            self._event('view-mode',session_id=sid,mode=mode.value,displayed=self.clock()-self.t0,
                display_revision=s.display_revision,contract_digest=self.contract_digest,
                contract_epoch=s.state.contract_epoch,owner_canonical_version=s.state.checkpoint_id)
    def _pressure(self):
        now=self.clock();age=0.;unseen=0;private_q=authority_q=0
        physical={role:0 for role in ['proposal','authority']}
        for worker,ids in self.inflight.values():
            if ids:physical[self.jobs[ids[0]]['role']]+=1
        for sid,s in self.sessions.items():
            b=self.book.session(sid)
            if b.accepted>b.certified:
                w=min(math.ceil(s.duration/self.fine),math.floor(b.certified/(self.fine*self.sample_rate))+1)
                age=max(age,max(0.,now-self._ready_time(s,w)))
            V=self.book.valid_private_frontier(sid)
            unseen+=max(0,b.accepted-max(b.certified,V))
            if not s.fine_busy:
                self._reconcile_covered_windows(s)
            if (not s.auth_done and not s.auth_busy and s.auth_result is None and
                self._ready_time(s,s.segment_end)<=now and self._target(s,s.segment_end)<=b.accepted):authority_q+=1
            if (not s.done and not s.fine_busy and s.fine_window<=math.ceil(s.duration/self.fine) and
                self._ready_time(s,s.fine_window)<=now and self._target(s,s.fine_window)<=b.accepted):private_q+=1
        return dict(oldest_uncertified_age=age,unseen_accepted_audio_samples=unseen,
            accepted_debt_samples=self.book.debt,reserved_debt_samples=self.book.committed_credit,
            actual_authority_ready_queue=authority_q,actual_private_ready_queue=private_q,
            authority_physical_leases=physical['authority'],private_physical_leases=physical['proposal'],
            pending_offered_audio_samples=sum(max(0,s.offered-s.accepted) for s in self.book.sessions.values() if not s.rejected))
    def _target(self,s,w):return min(round(self._end_seconds(s,w)*self.sample_rate),len(s.audio)//4)
    def _choose_mode(self,p):
        if self.mode==Mode.RECOVERY and not self._caught_up(self._recovered_frontiers):return Mode.RECOVERY
        age=p['oldest_uncertified_age'];warn=float(self.options['warning_age']);crit=float(self.options['critical_age']);clear=float(self.options['clear_age'])
        causal=self.method in ['cde_full','standard_cde'];age_only=self.method=='cde_age'
        if causal or age_only:
            urgent=(age_only or (p['unseen_accepted_audio_samples']>=self.fine*self.sample_rate and
                p['actual_authority_ready_queue']+p['authority_physical_leases']>0))
            if age>=crit and urgent:return Mode.CERTIFIED_ONLY
            if self.mode==Mode.CERTIFIED_ONLY and age>clear:return Mode.CERTIFIED_ONLY
            if age>=warn and (age_only or p['actual_private_ready_queue']+p['private_physical_leases']>0):return Mode.DEGRADED
        if self.method=='queue_expiry':
            k=int(self.options['queue_threshold'])
            if p['authority_physical_leases'] and p['actual_authority_ready_queue']>=k and p['actual_private_ready_queue']>=k:return Mode.CERTIFIED_ONLY
        if p['pending_offered_audio_samples'] and self.book.committed_credit>=self.book.budget:return Mode.BACKPRESSURE
        return Mode.NORMAL
    def _ingress(self):
        # Work on a clone: failed synchronization cannot mutate dispatch-eligible A.
        draft=CreditBook.restore(self.book.snapshot(self.origin),{sid:s.state for sid,s in self.sessions.items()},
            epoch=self.owner_epoch,origin_perf=self.origin)
        # Ordinary cloning preserves observed view, unlike restart recovery.
        for sid in draft.sessions:
            draft.sessions[sid].visible=self.book.sessions[sid].visible
            draft.sessions[sid].visible_version=self.book.sessions[sid].visible_version
        now=self.clock();ids=sorted(self.sessions);new_reject=[]
        for sid,s in self.sessions.items():
            elapsed=max(0.,now-self.origin-s.offset)
            full=len(s.audio)//4;eof=elapsed>=s.duration
            O=full if eof else min(full,math.floor(elapsed/self.fine)*round(self.fine*self.sample_rate))
            if O>draft.session(sid).offered or (eof and not draft.session(sid).eof):
                draft.offer(sid,max(O,draft.session(sid).offered),eof=eof)
        rotated=ids[self._grant_cursor:]+ids[:self._grant_cursor];self._grant_cursor=(self._grant_cursor+1)%len(ids)
        allow_grant=self.mode not in [Mode.CERTIFIED_ONLY,Mode.RECOVERY]
        for sid in rotated:
            s=self.sessions[sid];b=draft.session(sid)
            if b.rejected:continue
            if allow_grant:draft.reserve(sid,self.quantum)
            accepted=min(b.offered,b.reserved)
            if accepted>b.accepted:
                b.accepted=accepted;b.accepted_prefix_sha256=hashlib.sha256(s.audio[:accepted*4]).hexdigest()
            rejection=float(self.options.get('reject_new_after_seconds',0))
            if (self.method!='dgft_original' and rejection>0 and b.accepted==0 and b.offered>0 and
                now-self._ready_time(s,1)>=rejection):
                draft.reject_unaccepted(sid,'unaccepted-new-session-backpressure-timeout');new_reject.append(sid)
        draft.check();signature=self._input_signature(draft)
        if signature!=self._last_input_signature:
            before={sid:b.accepted for sid,b in self.book.sessions.items()}
            began=time.perf_counter();receipt=self.input_journal.checkpoint(draft.snapshot(self.origin))
            self.book=draft;self._last_input_signature=signature
            self._event('input-snapshot-synchronized',input_sequence=receipt['sequence'],
                snapshot_sha256=receipt['snapshot_sha256'],host_wall_seconds=time.perf_counter()-began,
                accepted_debt_samples=self.book.debt,reserved_debt_samples=self.book.committed_credit)
            for sid,b in self.book.sessions.items():
                if b.accepted>before[sid]:self._event('input-ack',session_id=sid,from_sample=before[sid],
                    to_sample=b.accepted,prefix_sha256=b.accepted_prefix_sha256,input_sequence=receipt['sequence'],
                    actual_offered_sample=b.offered,reserved_end=b.reserved)
            for sid in new_reject:self._retire_rejected(self.sessions[sid],self.book.session(sid).rejection_reason)
        else:
            self.book=draft
    def _tick(self):
        cpu=time.thread_time();host=time.perf_counter();self._consume_acks()
        p=self._pressure();self._last_decision_pressure=dict(p)
        mode=self._choose_mode(p)
        if mode!=self.mode:self._event('envelope-mode-decision',chosen=mode.value,previous=self.mode.value,
            pressure=p,observed_perf=self.clock(),input_sequence=self.input_journal.seq-1)
        self._set_mode(mode);self._ingress()
        summary=(self.mode.value,tuple(p.items()))
        if summary!=self._last_pressure:
            # Quantize only the log age, not the control input, to avoid per-ms
            # rich I/O. Structural queue/lease changes remain visible.
            frozen=dict(p,oldest_uncertified_age=round(p['oldest_uncertified_age'],1))
            key=(self.mode.value,tuple(frozen.items()))
            if key!=self._last_pressure:
                self._event('envelope-observation',mode=self.mode.value,**frozen);self._last_pressure=key
        self._decision_cpu+=time.thread_time()-cpu;self._decision_host+=time.perf_counter()-host;self._decision_count+=1
    def _ready(self,role):
        if not self._envelope_ready:return []
        if self.mode==Mode.RECOVERY:return []
        if role=='proposal' and self.mode==Mode.CERTIFIED_ONLY:return []
        if role=='proposal' and self.method!='dgft_original':
            for s in self.sessions.values():
                if s.done or s.fine_busy:continue
                self._reconcile_covered_windows(s)
                while s.fine_window<=math.ceil(s.duration/self.fine):
                    w=s.fine_window;b=self.book.session(s.sid)
                    if self._target(s,w)>b.accepted or self.clock()<=self._ready_time(s,w)+float(self.options['display_slo']):break
                    self._account_window(s,w,'expired-private-not-issued')
                    self._event('private-deadline-retired',session_id=s.sid,window=w,audio_end_sample=self._target(s,w),
                        original_deadline_perf=self._ready_time(s,w)+float(self.options['display_slo']),
                        canonical_frontier=s.state.audio_frontier_window,accepted_frontier=b.accepted,physical_GPU_cancelled=False)
                    s.fine_window+=1
        return [s for s in super()._ready(role) if not self.book.session(s.sid).rejected and
            self._target(s,s.fine_window if role=='proposal' else s.segment_end)<=self.book.session(s.sid).accepted]
    def _make_job(self,s,role):
        window=s.fine_window if role=='proposal' else s.segment_end
        if self._target(s,window)>self.book.session(s.sid).accepted:raise ValueError('unaccepted audio cannot reach model')
        job=super()._make_job(s,role)
        self._event('envelope-dispatch-decision',job_id=job['job_id'],role=role,session_id=s.sid,
            mode=self.mode.value,pressure=self._last_decision_pressure,
            actual_accepted_frontier=self.book.session(s.sid).accepted,
            actual_canonical_frontier=s.state.audio_frontier_window,input_sequence=self.input_journal.seq-1)
        return job
    def _finish_commit(self,s,result,job,*args,**kwargs):
        before=s.state.audio_frontier_window
        if job['audio_end_sample']>self.book.session(s.sid).accepted:raise ValueError('admission beyond accepted prefix')
        super()._finish_commit(s,result,job,*args,**kwargs)
        self.book.observe_admission(s.sid,epoch=s.state.contract_epoch,version=s.state.checkpoint_id,
            parent_frontier=before,frontier=s.state.audio_frontier_window,receipt=job['job_id'])
    def run(self):
        while True:
            if self.clock()-self.t0>float(self.contract['timeout_seconds']):raise TimeoutError('bounded envelope run unfinished; retain debt and all offered inputs')
            self._tick();self._receive();self._commit_ready()
            for sid,s in self.sessions.items():
                if not self.book.session(sid).rejected:
                    s.done=s.auth_done and not s.fine_busy and s.fine_window>math.ceil(s.duration/self.fine)
            self._dispatch()
            for s in self.sessions.values():
                if not s.fine_busy:self._reconcile_covered_windows(s)
            all_offered=all(b.eof for b in self.book.sessions.values())
            if (all_offered and all(s.done for s in self.sessions.values()) and not self.inflight and
                self._caught_up({sid:s.state.audio_frontier_window for sid,s in self.sessions.items()})):break
            self.sleep(float(self.options.get('tick_seconds',.005)))
        self._tick();expected={(s.sid,w) for s in self.sessions.values() for w in range(s.resumed_start_window+1,math.ceil(s.duration/self.fine)+1)}
        assert set(self.window_outcomes)==expected,'all offered fine windows, including rejection/retirement, must be accounted'
        commits=[e for e in self.events if e['kind']=='commit'];elapsed=self.clock()-self.t0
        return dict(wall_seconds_including_arrival_and_drain=elapsed,episode_elapsed_seconds=self.clock()-self.origin,
            audio_seconds=sum(s.duration for s in self.sessions.values()),
            audio_seconds_per_wall_second=sum(s.duration for s in self.sessions.values())/max(self.clock()-self.origin,1e-12),
            fine_window_accounting_complete=True,fine_window_outcomes={x:list(self.window_outcomes.values()).count(x) for x in set(self.window_outcomes.values())},
            certified_commits=len(commits),token_limit_events=sum(e.get('hit_token_limit',False) for e in self.events),
            final_states=[dict(session_id=s.sid,text=s.text,state=asdict(s.state)) for s in self.sessions.values()],
            final_input_snapshot=self.book.snapshot(self.origin),input_fsync_calls=self.input_journal.fsync_calls,
            input_fsync_seconds=self.input_journal.fsync_seconds,input_journal_bytes=self.input_journal.path.stat().st_size,
            envelope_decision_CPU_seconds=self._decision_cpu,envelope_decision_host_seconds=self._decision_host,
            envelope_decisions=self._decision_count,display_p99_seconds=quantile([e['latency_seconds'] for e in self.events if e['kind']=='display'],.99) if any(e['kind']=='display' for e in self.events) else 0.,
            contract_digest=self.contract_digest,evidence_type=self.contract['evidence_type'],
            metric_warning='legacy event P99/throughput are diagnostics only; primary all-offered episode metrics are independently reconstructed')
    def close(self):
        try:
            if self.input_journal is not None:self.input_journal.close()
        finally:super().close()
