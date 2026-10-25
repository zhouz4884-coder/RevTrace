"""Lightweight anchor and explicit installation-timing intervention hooks."""
from collections import deque
import time
from .ces_anchor import ConditionalRiskModel,choose_anchor,quantile

class V6OwnerMixin:
    def _v6_init(self):
        self.v6=self.ces.get('v6',{})
        if self.v6.get('policy','none') not in ('none','fine','anchor_cost','anchor_causal'):
            raise ValueError('unknown declared V6 policy')
        self._v6_times=deque(maxlen=128);self._v6_ages={};self._v6_context={};self._v6_holds={}
        self._v6_profile=None
        if self.v6.get('policy') in ('anchor_cost','anchor_causal'):
            if not callable(self.consumer_ack_source):raise ValueError('anchor needs actual Consumer ACKs')
            self._v6_profile=ConditionalRiskModel(self.cal.get('v6_joint_risk',{}))

    def _v6_choose(self,features,now,limit):
        rows=sorted(features,key=lambda t:(t.ready,t.sid))[:limit]
        identities={t.sid:(t.sid,self.sessions[t.sid].state.contract_epoch,self.sessions[t.sid].state.checkpoint_id,t.window,self.contract_digest) for t in rows}
        for sid,key in identities.items():
            self._v6_ages={k:v for k,v in self._v6_ages.items() if k[0]!=sid or k==key}
            self._v6_ages.setdefault(key,0)
        self._v6_context=identities
        predicted=max(.0001,quantile(list(self._v6_times),.9) if self._v6_times else float(self.v6.get('initial_plan_budget_s',.005)))
        predicted+=float(self.v6.get('dispatch_allowance_s',.002))
        started=time.perf_counter()
        # Risk is deliberately disabled unless a separately frozen randomized
        # stage-C estimate explicitly passes its generalization/support gate.
        risk={}
        effect=self.v6.get('causal_effect',{})
        if self.v6.get('policy')=='anchor_causal' and effect.get('enabled'):
            for t in rows:
                s=self.sessions[t.sid]
                pending=any(self.jobs[j]['role']=='proposal' and self.jobs[j]['session_id']==t.sid for _,ids in self.inflight.values() for j in ids)
                depth=max(0,s.branch_chunk-s.state.audio_frontier_window//32000)
                if not pending and depth>=int(effect.get('minimum_private_depth',1)):
                    risk[t.sid]=float(effect['cost_per_exposure_s'])
        options=dict(self.v6,policy='causal' if self.v6.get('policy')=='anchor_causal' else 'cost')
        decision=choose_anchor(rows,now=now+predicted,cal=self.cal,options=options,
            deferrals={sid:self._v6_ages[k] for sid,k in identities.items()},risk=risk,
            observed_rate=sum(self._closed_credit.values())/max(.01,now-self.t0),predictor=self._v6_profile)
        elapsed=time.perf_counter()-started;self._v6_times.append(elapsed)
        if decision.get('chosen_index',0)>0 and self.clock()>now+predicted:
            decision={'operation':'generate','sids':[t.sid for t in rows],'reason':'anchor-planning-age-overrun-default',
                'plan':[{'operation':'generate','sids':[t.sid for t in rows]}],'prediction_not_authorization':True}
        decision.update(v6_planning_budget_seconds=predicted,v6_chooser_wall_seconds=elapsed,
            v6_issue_check_perf=self.clock(),v6_observable_risk=risk,v6_policy=self.v6['policy'])
        return decision

    def _v6_dispatched(self,decision):
        selected=set(decision['sids'])
        for sid,key in self._v6_context.items():self._v6_ages[key]=0 if sid in selected else self._v6_ages[key]+1

    def _v6_held_results(self):
        held=[];delay=float(self.v6.get('authority_hold_seconds',0.));window=int(self.v6.get('hold_at_window',5))
        if delay<=0:return held
        now=self.clock()
        for s in self.sessions.values():
            r=s.auth_result
            if r is None:continue
            j=self.jobs[r['job_id']]
            if j['end_window']!=window:continue
            until=r['received_perf']+delay
            if j['job_id'] not in self._v6_holds:
                self._v6_holds[j['job_id']]=until
                self._event('v6-installation-intervention',job_id=j['job_id'],session_id=s.sid,
                    window=window,hold_seconds=delay,received_perf=r['received_perf'],apply_after_perf=until,
                    controlled_intervention=True,running_Worker_not_cancelled=True)
            if now<until:held.append((s,r));s.auth_result=None
        return held
