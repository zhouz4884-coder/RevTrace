"""Actual owner observations for the closed-loop scheduling model.

This adapter never calls a model or installs predicted state. Only immutable
currently released jobs and actual Consumer/WAL observations enter its state.
An exact-chain preview is conditional on a *future real* verification success.
"""
from dataclasses import asdict,replace
from collections import defaultdict
from bisect import bisect_right
import copy,math

from .dgft import digest_tokens
from .continuity_proof import eligible_chain
from .ces_policy import Target,cost
from .ces_v5_policy import V5Target,predict_batch
from .ces_closed_loop import (Identity,SuccessorObligation,TargetContext,
    PlannerConfig,ClosedLoopState,choose_closed_loop)

CLOSED_MODES={'service_cost','reserved_progress','inherit','causal'}


class ClosedLoopOwnerMixin:
    def _closed_init(self):
        options=self.ces.get('closed_loop_config',{})
        self.closed_config=PlannerConfig(**options)
        self.closed_state=ClosedLoopState(scope=(self.t0,self.contract_digest))
        self._closed_contexts={};self._closed_committed={};self._closed_credit={}
        self._closed_choice=None;self._closed_feature_records={}
        self._closed_proposer_dispatches=0
        self._closed_worker_started={};self._closed_fraction_cache={}
        self.closed_private_cdf_bins=int(self.ces.get('private_cdf_bins',32))
        if not 4<=self.closed_private_cdf_bins<=256:raise ValueError('bounded private CDF budget required')
        self.closed_proposer_policy=self.ces.get('proposer_policy','ready')
        if self.closed_proposer_policy not in ('ready','shared_progress','causal_joint'):
            raise ValueError('undeclared physical proposer selection policy')

    def _closed_installed(self,fields):
        sid=fields['session_id'];s=self.sessions[sid]
        job=self.jobs[fields['job_id']]
        self._closed_committed[sid,job['end_window']]=(self.t0+fields['installed'],job['audio_ready_perf'],
            (job['audio_end_sample']-job['audio_start_sample'])/self.sample_rate)
        if self.mode in CLOSED_MODES:
            retired=self.closed_state.admitted(sid,epoch=s.state.contract_epoch,frontier=job['audio_end_sample'],
                now=self.t0+fields['installed'])
            self._event('closed-loop-service-retired',session_id=sid,installed_perf=self.t0+fields['installed'],
                retired=retired,service_book=self.closed_state.to_audit(),actual_durable_install_observed=True)

    def _closed_observed_credit(self):
        for key,(installed,released,audio) in self._closed_committed.items():
            seen=self._first_visible.get(key)
            if seen is not None and seen<=released+self.ces['display_slo'] and installed<=released+self.ces['commit_slo']:
                self._closed_credit[key]=audio
        return sum(self._closed_credit.values())

    def _closed_profiles(self):
        return self.cal.get('closed_loop_profiles',{})

    def _closed_worker_event(self,fields):
        if fields.get('status')=='batch-started':
            started=fields['started_perf']
            if not math.isfinite(started):raise ValueError('finite actual worker start required')
            for job_id in fields['job_ids']:
                if job_id not in self.jobs or started<self.jobs[job_id]['enqueue_perf']-1e-7:
                    raise ValueError('worker start does not match an issued job')
                self._closed_worker_started[job_id]=started

    def _proposal_fractions(self,n,audio_seconds=None):
        audio_bin=None if audio_seconds is None else ('0-8' if audio_seconds<=8 else '8-16' if audio_seconds<=16 else '16+')
        key=(n,audio_bin)
        if key in self._closed_fraction_cache:return self._closed_fraction_cache[key]
        profile=self._closed_profiles().get('proposal',{})
        by_n=profile.get('row_fraction_by_n',{})
        choices=[]
        if audio_bin is not None:
            choices.append((str(n)+'/'+audio_bin,profile.get('row_fraction_by_n_audio',{}).get(str(n),{}).get(audio_bin)))
        choices.extend([(str(n),by_n.get(str(n))),('global',by_n.get('global'))])
        selected=None;label='conservative-no-supported-profile'
        for name,row in choices:
            if row and row.get('support',0)>=8 and row.get('physical_batches',0)>=8:
                selected=row;label=name;break
        fs=tuple(sorted(float(x) for x in selected['fractions'])) if selected else (1.,)
        if not fs or not all(math.isfinite(f) and 0<=f<=1 for f in fs):
            raise ValueError('invalid empirical row CDF')
        result=(fs,label);self._closed_fraction_cache[key]=result
        return result

    def _proposal_batch_prediction(self,jobs):
        """Empirical physical lease and marginal row fractions, never release."""
        ts=[Target(j['session_id'],j['end_window'],j['audio_ready_perf'],
            j['audio_ready_perf']+self.ces['commit_slo'],False,False,False,0,0,0.,None,
            audio_seconds=j['audio_end_sample']/self.sample_rate,
            interval_seconds=(j['audio_end_sample']-j['audio_start_sample'])/self.sample_rate,
            prompt_tokens=len(j['prompt_tokens'])) for j in jobs]
        lease=cost(self.cal,'proposal',len(jobs),ts)
        fractions,bucket=self._proposal_fractions(len(jobs))
        return max(1e-4,lease),fractions,bucket

    def _pending_private_distribution(self,s,frontier,now):
        matches=[]
        for worker,ids in self.inflight.values():
            owned=[self.jobs[j] for j in ids]
            for j in owned:
                if (j['role']=='proposal' and j['session_id']==s.sid and
                    j['job_id'] not in self._row_completed and j['audio_end_sample']>=frontier and
                    j.get('branch_generation')==s.branch_generation):
                    matches.append((j,owned))
        if not matches:return (),None,False,{'status':'no-uncompleted-frozen-private-job'}
        if len(matches)!=1:raise ValueError('at most one frozen Private job per session')
        j,owned=matches[0];lease,fs,bucket=self._proposal_batch_prediction(owned)
        fs,bucket=self._proposal_fractions(len(owned),j['audio_end_sample']/self.sample_rate)
        started=self._closed_worker_started.get(j['job_id'])
        age=max(0.,now-started) if started is not None else 0.
        delivery=max(0.,float(self.cal.get('v5_risk_model',{}).get('owner_delivery_seconds',0.)))
        # No received row implies no Consumer application from this job. A
        # GPU-terminal row may already be in IPC; condition modeled *delivery*,
        # not terminal time. This is a declared partial-observation model.
        first=bisect_right(fs,(age-delivery)/lease)
        values=[max(0.,lease*f+delivery-age) for f in fs[first:]]
        censored=not values
        if not values:values=[lease+delivery]
        # Upper-endpoint empirical bins retain all mass and only delay the
        # model CDF. The uncompressed calibration/CSV remains in the artifact.
        width=max(1,math.ceil(len(values)/self.closed_private_cdf_bins))
        counts=defaultdict(int)
        for i in range(0,len(values),width):
            chunk=values[i:i+width];counts[chunk[-1]]+=len(chunk)
        distribution=tuple((n/len(values),value) for value,n in sorted(counts.items()))
        legal=self._private_branch_currently_legal(s,j)
        return distribution,j,legal,{'status':'pending-actual-job','job_id':j['job_id'],
            'physical_rows':len(owned),'actual_lease_age_s':age,'predicted_full_lease_s':lease,
            'row_CDF_size_bucket':bucket,'survival_conditioned_samples':len(values),
            'age_clock':'observed-worker-start' if started is not None else 'start-not-yet-observed-age-zero',
            'private_delay_includes_delivery':True,'CDF_upper_endpoint_bins':len(distribution),
            'CDF_one_sided_error_bound':min(1.,(width-1)/len(values)),
            'censored_beyond_empirical_support':censored,'current_path_legal':legal,
            'scope':'prediction only; no future result, fault label or free GPU reuse'}

    def _private_branch_currently_legal(self,s,pending):
        """Check existing real root/edges, without inspecting injection labels."""
        if (s.branch_parent!=s.state.checkpoint_id or s.branch_root_frontier!=s.state.audio_frontier_window
            or tuple(s.branch_root_tokens)!=tuple(s.state.prompt_tokens)):
            return False
        cursor=s.segment_start;P=tuple(s.state.prompt_tokens)
        for (sid,w),r in sorted(self._proposal_results.items()):
            if sid!=s.sid or not (cursor<w<=s.branch_chunk):continue
            j=self.jobs[r['job_id']]
            if j.get('branch_generation')!=s.branch_generation:continue
            if j['chunk_id']!=cursor or tuple(j['prompt_tokens'])!=P:return False
            cursor=w;P=tuple(r['state_tokens'])
        return (cursor==s.branch_chunk and P==tuple(s.branch_tokens)
            and pending['chunk_id']==cursor and tuple(pending['prompt_tokens'])==P
            # A retained in-flight descendant can still name an older birth
            # Parent. Its actual frozen state edge, generation and rebased
            # canonical root above establish eligibility, not birth equality.
            and 0<=pending['audio_start_sample']<=s.branch_root_frontier)

    def _conditional_chain(self,s,target_end):
        r=self._proposal_results.get((s.sid,s.segment_end))
        if r is None:return None,False,{'status':'no-actual-ready-boundary-candidate'}
        j=self.jobs[r['job_id']]
        if j['audio_end_sample']!=target_end:return None,False,{'status':'candidate-boundary-mismatch'}
        target={'prompt_tokens':list(s.state.prompt_tokens),'chunk_id':s.segment_start,'language':s.language}
        selected_P,_=self.trusted_render(target,r['token_ids'])
        shadow=copy.copy(s)
        def check(P):
            shadow.state=replace(s.state,prompt_tokens=tuple(P),audio_frontier_window=target_end,
                checkpoint_id=s.state.checkpoint_id+1)
            return eligible_chain(shadow,self.jobs,self._proposal_results)
        v_ok,v_proof=check(selected_P)
        structural_ok,structural_proof=check(r['state_tokens'])
        return bool(v_ok),bool(structural_ok),{'status':'conditional-exact-chain-preview',
            'candidate_job_id':j['job_id'],'verify_success_projection_digest':digest_tokens(selected_P),
            'verify_success_chain_eligible':bool(v_ok),'verify_success_chain_proof':v_proof,
            'structural_chain_if_boundary_matches':bool(structural_ok),'structural_chain_proof':structural_proof,
            'condition':'requires actual complete FP32 verification, D1, WAL install; no publication now'}

    def _unknown_retention(self,s,mode,structural):
        if not structural:return 0.,{'status':'no-structurally-retainable-chain','support':0}
        r=self._proposal_results.get((s.sid,s.segment_end))
        if r is None:return None,{'status':'no-boundary-node','support':0}
        j=self.jobs[r['job_id']]
        same=j['parent']==s.state.checkpoint_id and tuple(j['prompt_tokens'])==tuple(s.state.prompt_tokens)
        key='same' if same else 'mismatch'
        row=self._closed_profiles().get('compatibility',{}).get(mode,{}).get(key,{})
        probability=row.get('probability')
        if probability is not None and not 0<=probability<=1:raise ValueError('invalid frozen compatibility profile')
        return probability,{'status':'empirical-selected-root-equality-only' if probability is not None else 'unknown-sparse',
            'class':key,'support':row.get('support',0),'probability':probability,
            'lower':row.get('lower'),'upper':row.get('upper'),
            'not_a_same_target_counterfactual':True}

    def _closed_build_contexts(self,features,now):
        contexts={};records={}
        for t in features:
            s=self.sessions[t.sid];end=min(round(self._end_seconds(s,s.segment_end)*self.sample_rate),len(s.audio)//4)
            identity=Identity(s.sid,s.state.contract_epoch,s.state.checkpoint_id,digest_tokens(s.state.prompt_tokens),
                s.state.audio_frontier_window,end,self.contract_digest)
            private,pending,legal,private_audit=self._pending_private_distribution(s,end,now)
            verified,structural,chain_audit=self._conditional_chain(s,end)
            direct,direct_audit=self._unknown_retention(s,'direct',structural)
            fallback,fallback_audit=self._unknown_retention(s,'fallback',structural)
            successors=[];cumulative=0.;cursor=end
            for w in range(s.segment_end+1,min(math.ceil(s.duration/self.fine),
                s.segment_end+self.closed_config.max_successors_per_session)+1):
                released=self._ready_time(s,w)
                if released>now:break
                frontier=min(round(self._end_seconds(s,w)*self.sample_rate),len(s.audio)//4)
                weight=(frontier-cursor)/self.sample_rate
                # Feature-only estimate. A future Parent or generated Z is
                # never constructed, and this object cannot be submitted.
                estimated_prompt=len(s.state.prompt_tokens)
                estimate=replace(t,window=w,ready=released,deadline=released+self.ces['commit_slo'],
                    candidate_ready=False,candidate_tokens=0,candidate_eta=None,display_met=False,
                    display_expired=now>released+self.ces['display_slo'],audio_weight=weight,
                    audio_seconds=frontier/self.sample_rate,interval_seconds=weight,prompt_tokens=estimated_prompt)
                cumulative+=cost(self.cal,'generate',1,[estimate])+max(0.,float(
                    self.cal.get('v5_risk_model',{}).get('owner_delivery_seconds',0.)))
                met,_=self._display_status(s,w,now)
                u_private,_,u_legal,u_audit=self._pending_private_distribution(s,frontier,now)
                successors.append(SuccessorObligation(window=w,frontier_end=frontier,release=released,
                    display_deadline=released+self.ces['display_slo'],commit_deadline=released+self.ces['commit_slo'],
                    audio_weight=weight,remaining_service_s=cumulative,display_met=met,
                    private_ready_delay_s=None,verify_private_compatible=verified if w==s.segment_end+1 else None,
                    unknown_private_probability=None,
                    direct_private_probability=direct if w==s.segment_end+1 else None,
                    fallback_private_probability=fallback if w==s.segment_end+1 else None,
                    inherit_current_transition_model=w==s.segment_end+1,parent_frontier_start=cursor,
                    audio_seconds=frontier/self.sample_rate,estimated_prompt_tokens=estimated_prompt,interval_seconds=weight,
                    private_delay_distribution=u_private,private_path_currently_legal=u_legal,
                    private_delay_includes_delivery=True))
                cursor=frontier
            contexts[t.sid]=TargetContext(identity=identity,successors=tuple(successors),
                verify_private_compatible=verified,direct_private_probability=direct,fallback_private_probability=fallback,
                private_path_currently_legal=legal,private_delay_distribution=private,private_delay_includes_delivery=True)
            records[t.sid]={'identity':asdict(identity),'private_path':private_audit,'chain_preview':chain_audit,
                'target_context':asdict(contexts[t.sid]),
                'direct_root_model':direct_audit,'fallback_root_model':fallback_audit,
                'released_successors':[asdict(u) for u in successors],
                'private_CDF_authority_scenarios_relation':'independent empirical approximation; no claimed joint oracle'}
        self._closed_contexts=contexts;self._closed_feature_records=records
        return contexts

    def _closed_choose(self,features,now,limit):
        contexts=self._closed_build_contexts(features,now)
        decision=choose_closed_loop(features,contexts,now=now,mode=self.mode,cal=self.cal,limit=limit,
            observed_credit_audio=self._closed_observed_credit(),elapsed_seconds=max(0.,now-self.t0),
            state=self.closed_state,display_slo=self.ces['display_slo'],config=self.closed_config)
        self._closed_choice=decision
        self._event('closed-loop-observation',observed_perf=now,contexts={str(k):v for k,v in self._closed_feature_records.items()},
            service_book=self.closed_state.to_audit(),observed_credit_audio=self._closed_observed_credit(),
            elapsed_seconds=max(0.,now-self.t0),prediction_not_authorization=True)
        return decision

    def _closed_dispatched(self,decision):
        dispatched_perf=self.clock()
        receipt=self.closed_state.record_dispatch(decision,self._closed_contexts,now=dispatched_perf)
        self._event('closed-loop-service-dispatch',actual_dispatch_perf=dispatched_perf,
            decision_token=decision['decision_token'],**receipt)

    def _observed_authority_busy_forecast(self,now):
        """A readiness opportunity exists only behind an actual occupied lease."""
        for _,ids in self.inflight.values():
            jobs=[self.jobs[j] for j in ids]
            if not jobs or jobs[0]['role']!='authority':continue
            rows=[]
            for j in jobs:
                rows.append(Target(j['session_id'],j['end_window'],j['audio_ready_perf'],
                    j['audio_ready_perf']+self.ces['commit_slo'],j['ces_operation']=='verify',False,False,
                    len(j.get('candidate_token_ids',[])),0,0.,None,
                    audio_seconds=j['audio_end_sample']/self.sample_rate,
                    interval_seconds=(j['audio_end_sample']-j['audio_start_sample'])/self.sample_rate,
                    prompt_tokens=len(j['prompt_tokens'])))
            starts=[self._closed_worker_started[j['job_id']] for j in jobs if j['job_id'] in self._closed_worker_started]
            age=max(0.,now-min(starts)) if starts else 0.
            outcomes=predict_batch(self.cal,jobs[0]['ces_operation'],rows)
            remaining=[(o.weight,o.lease-age) for o in outcomes if o.lease>age]
            if not remaining:remaining=[(1.,max(o.lease for o in outcomes))]
            total=sum(w for w,_ in remaining)
            return tuple((w/total,t) for w,t in remaining)
        return ()

    def _closed_proposal_selection(self,ready,now):
        policy=self.ces.get('proposer_policy','ready')
        if policy=='ready':return self._order_proposals(ready,now)
        if policy not in ('shared_progress','causal_joint'):raise ValueError('unknown proposer subset policy')
        limit=int(self.contract['microbatch']);ranked=sorted(ready,key=lambda s:(
            self._display_status(s,s.fine_window,now)[0],self._ready_time(s,s.fine_window),s.sid))[:limit]
        features={}
        for s in ranked:
            f=s.fine_window;end=round(self._end_seconds(s,f)*self.sample_rate)
            rebases=s.state.checkpoint_id>s.branch_parent and s.state.audio_frontier_window<end
            prompt_length=len(s.state.prompt_tokens) if rebases else len(s.branch_tokens)
            features[s.sid]=Target(s.sid,f,self._ready_time(s,f),self._ready_time(s,f)+self.ces['commit_slo'],
                False,False,False,0,0,0.,None,audio_seconds=end/self.sample_rate,
                interval_seconds=max(0.,(end-s.state.audio_frontier_window)/self.sample_rate),prompt_tokens=prompt_length)
        allowance=float(self.cal.get('v5_risk_model',{}).get('owner_delivery_seconds',0.))
        busy=self._observed_authority_busy_forecast(now) if policy=='causal_joint' else ()
        past_rate=self._closed_observed_credit()/max(.001,now-self.t0)
        choices=[]
        for n in sorted({min(len(ranked),v) for v in [1,2,4,8,limit]}):
            plan=[rs for rs in [ranked[:n],ranked[n:]] if rs]
            elapsed=credit=evidence_value=0.;paid=[]
            for rs in plan:
                ts=[features[s.sid] for s in rs];lease=cost(self.cal,'proposal',len(rs),ts)
                for s,t in zip(rs,ts):
                    fractions,bucket=self._proposal_fractions(len(rs),t.audio_seconds)
                    met,expired=self._display_status(s,s.fine_window,now)
                    if not met and not expired:
                        cut=(t.ready+self.ces['display_slo']-now-elapsed-allowance)/lease
                        p=bisect_right(fractions,cut)/len(fractions)
                        credit+=min(self.fine,s.duration-(s.fine_window-1)*self.fine)*p
                    # No fictitious wait on an idle Authority. Only a real
                    # occupied lease offers time to prepare an undispatched
                    # current target's candidate. All controls may enable this.
                    if busy and self.mode not in ('fine','standard') and not s.auth_busy and s.fine_window==s.segment_end:
                        audio_bin='0-8' if t.audio_seconds<=8 else '8-16' if t.audio_seconds<=16 else '16+'
                        estimate=self._closed_profiles().get('proposal',{}).get('median_generated_tokens_by_audio_bin',{}).get(audio_bin,{}).get('median_generated_tokens')
                        if estimate is not None:
                            forecast=replace(t,candidate_tokens=max(1,int(round(estimate))))
                            g=cost(self.cal,'generate',1,[forecast]);v=cost(self.cal,'verify',1,[forecast])
                            fallback=cost(self.cal,'fallback',1,[forecast]);p_bad=self.cal.get('global_reject',1.)
                            saving=max(0.,g-v-p_bad*fallback)
                            useful=sum(w*bisect_right(fractions,(min(rem,t.deadline-now-v-p_bad*fallback)-elapsed-allowance)/lease)/len(fractions)
                                for w,rem in busy)
                            evidence_value+=useful*saving*past_rate
                paid.append({'sids':[s.sid for s in rs],'lease_s':lease,'starts_after_s':elapsed})
                elapsed+=lease
            wall=elapsed+allowance
            choices.append({'score':(credit+evidence_value)/max(.001,wall),'credit':credit,
                'wall':wall,'lease':elapsed,'sids':[s.sid for s in plan[0]],'selected':plan[0],
                'evidence':evidence_value,'paid_plan':paid})
        best=min(choices,key=lambda x:(-x['score'],-x['credit'],x['wall'],x['sids']))
        self._event('closed-loop-proposer-choice',policy=policy,ready_sids=[s.sid for s in ready],
            common_cut_sids=[s.sid for s in ranked],selected_sids=best['sids'],
            predicted_paid_lease_s=best['lease'],predicted_full_cut_wall_s=best['wall'],
            predicted_evidence_value=best['evidence'],authority_occupied_lease_observed=bool(busy),
            actual_subset_differs=set(best['sids'])!=set(s.sid for s in ready[:limit]),
            candidates=[{k:v for k,v in x.items() if k!='selected'} for x in choices],
            no_physical_preemption=True,prediction_not_authorization=True,
            objective_scope='bounded current Proposer cut plus observed Authority-lease readiness opportunity')
        self._closed_proposer_dispatches+=1
        return best['selected']
