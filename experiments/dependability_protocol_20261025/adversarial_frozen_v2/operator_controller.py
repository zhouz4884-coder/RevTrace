"""Prepared-input fault operator, NOT an arrival-driven serving scheduler.

Reuses actual owner/admission/WAL code. Execute is a supplied real GPU backend
or explicitly labelled CPU fixture. Diagnostic oracle calls cannot install.
"""
import copy,time
from revtrace.live_qwen import LiveQwenScheduler,fingerprint
from revtrace.online_admission import complete_candidate,gate_candidate,target_identity

class PreparedOwner(LiveQwenScheduler):
    def __init__(self,**kw):
        self.prepared_input_released=kw.get('clock',time.perf_counter)();super().__init__(**kw)
    def _ready_time(self,s,window):
        # All immutable prepared audio is explicitly offered before this lab
        # owner starts. No backdated clock, natural-arrival or SLO claim.
        return self.prepared_input_released

class FeedbackOperator:
    METHODS={'renderer_only','strict','revtrace','standard'}
    def __init__(self,owner,*,execute,method,contains_payload):
        if method not in self.METHODS:raise ValueError('unfrozen operator policy')
        if len(owner.sessions)!=1 or owner.rho!=1 or owner.fine!=2:raise ValueError('one-session fixed fine operator')
        self.owner=owner;self.session=next(iter(owner.sessions.values()));self.execute=execute;self.method=method
        self.contains_payload=contains_payload;self.calls=[];self.unsafe_installs=0
    def _call(self,j,purpose):
        r,physical=self.execute(j,purpose);self.calls.append(dict(job=copy.deepcopy(j),result=copy.deepcopy(r),physical=copy.deepcopy(physical),purpose=purpose))
        return r,physical
    @staticmethod
    def attach(j,candidate=None):
        # Empty means an explicit lab instruction to perform existing paid
        # full-FP32 fallback. It is NOT counted as a ready/valid candidate.
        j.update(candidate_token_ids=[] if candidate is None else list(candidate['token_ids']),
            candidate_state_tokens=[] if candidate is None else list(candidate['state_tokens']),
            candidate_text='' if candidate is None else candidate['text'],
            candidate_origin_job_id='NO_CANDIDATE_FORCE_REAL_GENERATION' if candidate is None else candidate['job_id'])
        return j
    def protected_selection(self,j,r,physical,*,allow_unchecked=False):
        p=r.get('online_verification');assert p and p['target_identity']==target_identity(j)
        assert p['dtype']=='float32' and not p['context_override_used']
        assert p['executed_prompt_tokens']==j['prompt_tokens'] and p['actual_audio_sha256']==j['prefix_audio_sha256']
        if p['fallback_used']:
            assert p['fallback_generated'] and j['job_id'] in p['fallback_executed_job_ids']
            phases=[x for x in physical['phases'] if x['phase']=='fresh-FP32-fallback' and j['job_id'] in x['executed_job_ids']]
            assert len(phases)==1 and phases[0]['completed_perf']>phases[0]['started_perf']
            return True
        if p['mode']=='unprotected':
            if not allow_unchecked:raise ValueError('uncertified candidate cannot enter a protected history')
            assert p['unsafe_no_FP32_selection'] and r['token_ids']==j['candidate_token_ids']
            return False
        assert p['mode']=='strict'
        ok,_=gate_candidate('strict',j['candidate_token_ids'],p['predicted_token_ids'],p['candidate_margins'],
            eos=p['eos_token_ids'],budget=self.owner.contract['authority_runtime']['max_new_tokens'])
        assert ok and r['token_ids']==j['candidate_token_ids'];return True
    def install(self,j,r,physical,*,allow_unchecked=False):
        trusted=self.protected_selection(j,r,physical,allow_unchecked=allow_unchecked)
        if not trusted:self.unsafe_installs+=1
        self.owner._accept_result('authority-1',r);self.owner._commit_ready()
        self.owner._reconcile_covered_windows(self.session)
        return trusted
    def authority(self,candidate=None,purpose='selected-authority'):
        j=self.attach(self.owner._make_job(self.session,'authority'),candidate)
        self.session.auth_busy=True;r,p=self._call(j,purpose);return j,r,p
    def oracle(self,target,index):
        j=copy.deepcopy(target);j.pop('_delivery',None);j['job_id']='diagnostic-oracle-'+str(index)+'-'+target['job_id']
        j['enqueue_perf']=self.owner.clock();self.attach(j,None)
        r,p=self._call(j,'DIAGNOSTIC_ONLY_NO_ADMISSION');self.protected_selection(j,r,p)
        return r
    def proposal(self,purpose):
        j=self.owner._make_job(self.session,'proposal');self.session.fine_busy=True;r,p=self._call(j,purpose)
        self.owner._accept_result('proposal-0',r);return j,r,p
    def run(self):
        s=self.session
        # Common real trusted prelude to F=4s. Every mode pays it; weak mode
        # uses empty-candidate generation, never an invented ready candidate.
        for _ in range(2):
            j,r,p=self.authority(purpose='common-trusted-prelude');self.install(j,r,p)
        assert s.state.audio_frontier_window==64000 and s.fine_window==3
        root_before=copy.deepcopy(s.state)
        jp,rp,pp=self.proposal('candidate-at-6s')
        candidate=rp if self.method in ['renderer_only','strict'] else None
        ja,ra,pa=self.authority(candidate,purpose='selected-at-6s-held-before-install')
        metadata_shadow=all(jp[k]==ja[k] for k in ['session_id','parent','contract_epoch','contract_digest',
            'audio_start_sample','audio_end_sample','prefix_audio_sha256','interval_audio_sha256','prompt_tokens'])
        metadata_shadow=metadata_shadow and rp['runtime_digest']==jp['runtime_digest'] and rp['prefix_audio_sha256']==jp['prefix_audio_sha256']
        rendered_P,rendered_Y=self.owner.trusted_render(ja,rp['token_ids'])
        render_shadow=list(rendered_P)==rp['state_tokens'] and rendered_Y.encode()==rp['text'].encode()
        if self.method=='renderer_only':assert metadata_shadow and render_shadow,'shadow equivalence preconditions not met'
        oracle1=self.oracle(ja,1);oracle2=self.oracle(ja,2)
        assert oracle1['token_ids']==oracle2['token_ids'] and oracle1['state_tokens']==oracle2['state_tokens'],'same-input oracle not stable'
        if self.method!='renderer_only':
            self.protected_selection(ja,ra,pa)
            assert ra['token_ids']==oracle1['token_ids'] and ra['state_tokens']==oracle1['state_tokens'],'protected target not equal to bounded actual reference'
        # Legal controlled asynchronous completion: a real Authority result is
        # complete, but not installed until the real Private successor returns.
        # No assertion that this is a natural arrival frequency or schedule win.
        assert s.state==root_before
        jf,rf,pf=self.proposal('future-private-at-8s-before-authority-install')
        trusted=self.install(ja,ra,pa,allow_unchecked=self.method=='renderer_only')
        authority_future=[]
        while not s.auth_done:
            j,r,p=self.authority(purpose='future-real-authority-continuation')
            authority_future.append(dict(job_id=j['job_id'],input_has_payload=self.contains_payload(j['prompt_tokens']),
                actual_processed_prefix_has_payload=self.contains_payload(r['model_input_audit']['rollback_prefix']),
                new_neural_Z_has_payload=self.contains_payload(r['token_ids']),P_has_payload=self.contains_payload(r['state_tokens']),
                Y_has_payload=self.contains_payload(r['text'])))
            self.install(j,r,p)
        return dict(method=self.method,scope='prepared-input real operator if backend is GPU; no deployed SLO/Goodput claim',
            candidate_tokens=list(rp['token_ids']),actual_private_descendant_prompt_has_payload=self.contains_payload(jf['prompt_tokens']),
            actual_private_descendant_processed_prefix_has_payload=self.contains_payload(rf['model_input_audit']['rollback_prefix']),
            actual_private_descendant_new_Z_has_payload=self.contains_payload(rf['token_ids']),
            actual_private_descendant_P_has_payload=self.contains_payload(rf['state_tokens']),
            unchecked_candidate_installs=self.unsafe_installs,selected_injection_Z_matches_actual_FP32_oracle=ra['token_ids']==oracle1['token_ids'],
            initial_root_before_injection_frontier=64000,authority_continuations=authority_future,
            final_canonical_P=list(s.state.prompt_tokens),final_text=s.text,final_frontier=s.state.audio_frontier_window,
            actual_operator_requests=len(self.calls),metadata_only_shadow_on_same_coherent_candidate=self.method=='renderer_only',
            metadata_shadow_accepts_current_context=metadata_shadow,renderer_consistency_shadow_accepts=render_shadow,
            metadata_shadow_cost_claim=False,all_raw_calls=self.calls)
