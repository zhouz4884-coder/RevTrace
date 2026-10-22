"""Minimal C2-only interval selector. No neural selection, KV reuse or recovery worker."""
import math,time
from .live_qwen import LiveQwenScheduler

class ServiceCost:
    def __init__(self,table):
        self.table=table
        if not table or {r['rho'] for r in table}!={1,2,3}:raise ValueError('three past cost curves required')
    def __call__(self,rho,batch,tail=False):
        key='p90_seconds' if tail else 'median_seconds';rs=sorted([r for r in self.table if r['rho']==rho],key=lambda r:r['batch_rows']);n=max(1,batch)
        if n<=rs[0]['batch_rows']:return rs[0][key]
        if n>=rs[-1]['batch_rows']:return rs[-1][key]*n/rs[-1]['batch_rows']
        for a,b in zip(rs,rs[1:]):
            if a['batch_rows']<=n<=b['batch_rows']:return a[key]+(b[key]-a[key])*(n-a['batch_rows'])/(b['batch_rows']-a['batch_rows'])
        raise AssertionError('cost interpolation')

class ElasticAuthorityScheduler(LiveQwenScheduler):
    def __init__(self,**kwargs):
        rule=kwargs['contract']['granularity_policy']
        if rule['allowed']!=[1,2,3] or rule['kind'] not in ['fixed1','fixed2','fixed3','backlog','deadline','joint']:raise ValueError('undeclared granularity rule')
        if kwargs['contract'].get('proposal_barrier')!='decoupled' or kwargs['contract'].get('verification_policy')!='canonical_generate':raise ValueError('bounded prototype supports decoupled canonical-generation only')
        self.rule=rule;self.kind=rule['kind'];self.cost=ServiceCost(rule['service_cost_table']);self.plans={};self.plan_history=[]
        super().__init__(**kwargs)
    def _begin_segment(self,s):
        total=math.ceil(s.duration/self.fine);s.segment_end=min(total,s.segment_start+1);s.auth_result=s.fine_end_result=None;self.plans[s.sid]=None
        self._event('segment-parent',session_id=s.sid,parent=s.state.checkpoint_id,frontier=s.state.audio_frontier_window,start_window=s.segment_start,end_window=s.segment_end,plan_pending=not self.kind.startswith('fixed'))
        if self.kind.startswith('fixed'):self._freeze_plan(s,int(self.kind[-1]),{'reason':'declared-fixed'})
    def _freeze_plan(self,s,rho,observation):
        if type(rho) is not int or rho not in self.rule['allowed']:raise ValueError('undeclared rho')
        if s.auth_busy or s.auth_result is not None or self.plans.get(s.sid) is not None:raise ValueError('cannot mutate pending/inflight authority')
        end=min(math.ceil(s.duration/self.fine),s.segment_start+rho)
        if end<=s.segment_start:raise ValueError('empty authority plan')
        p={'session_id':s.sid,'parent':s.state.checkpoint_id,'start_window':s.segment_start,'end_window':end,'selected_rho':rho,'planned_perf':self.clock()}
        self.plans[s.sid]=p;s.segment_end=end;self.plan_history.append(dict(p))
        self._event('granularity-plan',**p,rule=self.kind,observation=observation)
    def _active(self,now):
        # Only streams that have actually released audio beyond current F.
        return [s for s in self.sessions.values() if not s.auth_done and now>=self._ready_time(s,s.segment_start+1)]
    def _forecast_ready(self,s,rho,now):
        # Do not inspect future acoustic data or future arrival cohorts. An EOF
        # may shorten this forecast only after EOF has actually arrived.
        end=(s.segment_start+rho)*self.fine
        if now>=self.t0+s.offset+s.duration:end=min(end,s.duration)
        return self.t0+s.offset+max(0,end-s.resume_frontier_sample/self.sample_rate)
    def _queue_finish(self,s,rho,now,active):
        wait=0.
        for worker,ids in self.inflight.values():
            js=[self.jobs[jid] for jid in ids]
            if not js or js[0]['role']!='authority':continue
            estimate=max(self.cost(max(1,min(3,j['chunk_advance'])),len(js),True) for j in js)
            wait=max(wait,max(0,estimate-(now-min(j['enqueue_perf'] for j in js))))
        tasks=[]
        for other in active:
            if other.sid==s.sid or other.auth_busy or other.auth_result is not None:continue
            p=self.plans.get(other.sid);r=p['selected_rho'] if p else 3
            tasks.append((self._forecast_ready(other,r,now),other.sid,r,False))
        tasks.append((self._forecast_ready(s,rho,now),s.sid,rho,True));t=now+wait;limit=int(self.contract['authority_microbatch'])
        while tasks:
            ready=sorted([v for v in tasks if v[0]<=t],key=lambda v:(v[0],v[1]))
            if not ready:t=min(v[0] for v in tasks);continue
            batch=ready[:limit];t+=max(self.cost(v[2],len(batch),True) for v in batch)
            if any(v[3] for v in batch):return t
            for v in batch:tasks.remove(v)
        raise AssertionError('forecast lost candidate')
    def _choose(self,s):
        now=self.clock();active=self._active(now);n=max(1,len(active));B=min(int(self.contract['authority_microbatch']),n)
        backlog=sum(max(0,int(min(o.duration,max(0,now-self.t0-o.offset))/self.fine)-o.segment_start) for o in active)
        deadline=self._ready_time(s,s.segment_start+1)+self.rule['commit_deadline_seconds']
        values=[]
        for rho in [1,2,3]:
            eta=self._queue_finish(s,rho,now,active);load=0.
            for other in active:
                p=self.plans.get(other.sid);r=rho if other.sid==s.sid else p['selected_rho'] if p else 3
                load+=self.cost(r,B)/(B*r*self.fine)
            values.append({'rho':rho,'eta':eta,'lateness':max(0,eta-deadline),'demand_estimate':load,'work_per_audio_estimate':self.cost(rho,B)/(rho*self.fine)})
        if self.kind=='backlog':
            a,b=self.rule['backlog_cutoffs'];chosen=1 if backlog<=a else 2 if backlog<=b else 3
        elif self.kind=='deadline':
            feasible=[v for v in values if v['lateness']<=1e-9];chosen=max(v['rho'] for v in feasible) if feasible else min(values,key=lambda v:(v['lateness'],v['work_per_audio_estimate'],v['rho']))['rho']
        else:
            feasible=[v for v in values if v['lateness']<=1e-9 and v['demand_estimate']<=self.rule['capacity_target']]
            chosen=min(v['rho'] for v in feasible) if feasible else min(values,key=lambda v:(v['lateness'],v['work_per_audio_estimate'],v['rho']))['rho']
        return chosen,{'observed_perf':now,'active_released_streams':n,'released_uncommitted_fine_windows':backlog,'earliest_frontier_deadline':deadline,'predictions':values,'unplanned_observed_stream_forecast':3,'future_cohorts_or_text_labels_used':False}
    def _dispatch(self):
        if not self.kind.startswith('fixed'):
            now=self.clock()
            for s in sorted(self._active(now),key=lambda s:(self._ready_time(s,s.segment_start+1),s.sid)):
                if s.auth_busy or s.auth_result is not None or self.plans.get(s.sid) is not None:continue
                started=time.perf_counter();rho,obs=self._choose(s);obs['decision_host_wall_seconds']=time.perf_counter()-started;self._freeze_plan(s,rho,obs)
        return super()._dispatch()
    def _ready(self,role):
        values=super()._ready(role)
        return [s for s in values if self.plans.get(s.sid) is not None] if role=='authority' else values
    def _commit_ready(self):
        for s in self.sessions.values():
            if s.done or s.auth_done or s.auth_result is None:continue
            j=self.jobs[s.auth_result['job_id']];p=self.plans.get(s.sid)
            if not p or p['selected_rho'] not in self.rule['allowed'] or j['parent']!=p['parent'] or j['chunk_id']!=p['start_window'] or j['end_window']!=p['end_window']:raise ValueError('authority result not in frozen declared plan')
            expected_end=min(round(p['end_window']*self.fine*self.sample_rate),len(s.audio)//4)
            if j['audio_start_sample']!=s.state.audio_frontier_window or j['audio_end_sample']!=expected_end or j['chunk_advance']!=p['end_window']-p['start_window']:raise ValueError('authority sample interval differs from frozen plan')
        return super()._commit_ready()
    def _expected_commit_count(self):
        for sid,s in self.sessions.items():
            cursor=s.resumed_start_window
            for p in [p for p in self.plan_history if p['session_id']==sid]:
                if p['start_window']!=cursor or not 0<p['end_window']-cursor<=p['selected_rho']:raise AssertionError('noncontiguous dynamic plan')
                cursor=p['end_window']
            if cursor!=math.ceil(s.duration/self.fine):raise AssertionError('unfinished planned coverage')
        n=len(self.plan_history)
        if self.kind.startswith('fixed') and n!=super()._expected_commit_count():raise AssertionError('fixed plan regression')
        return n
