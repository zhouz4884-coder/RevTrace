"""CPU fixtures only: scheduling predictions cannot weaken owner predicates."""
from copy import deepcopy
from dataclasses import replace
import pytest
from revtrace.ces_policy import Target,choose,cost
from revtrace.ces_runtime import CESScheduler,validate_evidence
from revtrace.online_admission import target_identity
from test_live_qwen import Clock,Fake
import numpy as np

CAL={'global_reject':.2,'causal_reject':{'same-prev-ok':{'p':.04},'mismatch-prev-reject':{'p':.8}},
 'cost_seconds':{k:{str(b):v*(1+b/8) for b in [1,2,4,8,16]} for k,v in [('generate',.8),('verify',.1),('fallback',.9),('proposal',.5)]}}
T=Target(0,5,10,18,True,True,False,30,0,0,None)

@pytest.mark.parametrize('mode',['fine','standard','strict','readiness','ready_any','cost_gate','cost','causal_only','ces'])
def test_never_verify_absent_candidate(mode):
    t=replace(T,candidate_ready=False,candidate_eta=None)
    d=choose([t],now=11,mode=mode,cal=CAL,limit=16)
    assert d['operation']!='verify'

def test_no_fault_or_future_field_in_features():
    assert set(T.__dataclass_fields__)=={'sid','window','ready','deadline','candidate_ready','same_birth','previous_reject','candidate_tokens','descendant_count','descendant_seconds','candidate_eta','projection_compatible','audio_seconds','interval_seconds','prompt_tokens'}

def test_contextual_cost_uses_only_available_inputs_and_shared_model():
    c=deepcopy(CAL);c['contextual_cost_models']={'generate':{'coefficients':[.1,.1,0,0,0,.05,0],'prediction_floor_s':.05,'prediction_ceiling_s':4.}}
    short=replace(T,audio_seconds=10,interval_seconds=2,prompt_tokens=30)
    long=replace(short,interval_seconds=6)
    assert cost(c,'generate',1,[long])>cost(c,'generate',1,[short])
    assert cost(c,'generate',1,[replace(short,candidate_tokens=250)])==cost(c,'generate',1,[short])
    with pytest.raises(TypeError):Target(**dict(vars(T),fault_label=True))

def test_causal_history_changes_prediction_not_permission():
    c=deepcopy(CAL);c['cost_seconds']['verify']={str(b):.6 for b in [1,2,4,8,16]}
    good=choose([T],now=11,mode='ces',cal=c,limit=16)
    bad=choose([replace(T,same_birth=False,previous_reject=True)],now=11,mode='ces',cal=c,limit=16)
    assert good['operation']=='verify' and bad['operation']=='generate'

def job_result(op='generate'):
    j={'job_id':'a','session_id':0,'parent':2,'prompt_tokens':[4],'chunk_id':2,
       'audio_start_sample':32000,'audio_end_sample':64000,'prefix_audio_sha256':'audio',
       'contract_digest':'contract','runtime_digest':'runtime','ces_operation':op,
       'candidate_token_ids':[7,9]}
    r={'ces_operation':op,'token_ids':[7,9],
       'execution_context_audit':{'executed_prompt_tokens':[4],'actual_audio_sha256':'audio','fault_override':False}}
    if op=='verify':r['online_verification']={'mode':'strict','target_identity':target_identity(j),
       'dtype':'float32','context_override_used':False,'executed_prompt_tokens':[4],'actual_audio_sha256':'audio',
       'fallback_used':False,'predicted_token_ids':[7,9],'candidate_margins':[0,0],'eos_token_ids':[9]}
    return j,r,{'authority_runtime':{'max_new_tokens':4}}

@pytest.mark.parametrize('mutation',['mode','context','audio','dtype','token','stop','target','fallback'])
def test_invalid_verifier_fail_closed(mutation):
    j,r,c=job_result('verify');p=r['online_verification']
    if mutation=='mode':r['ces_operation']='generate'
    if mutation=='context':p['executed_prompt_tokens']=[99]
    if mutation=='audio':p['actual_audio_sha256']='other'
    if mutation=='dtype':p['dtype']='float16'
    if mutation=='token':p['predicted_token_ids']=[8,9]
    if mutation=='stop':p['predicted_token_ids']=[7,8]
    if mutation=='target':j['parent']=3
    if mutation=='fallback':p.update(fallback_used=True,fallback_generated=False,fallback_batch_seconds=0.)
    with pytest.raises(ValueError):validate_evidence(j,r,c)

def test_valid_paid_fallback_not_confused_with_candidate():
    j,r,c=job_result('verify');r['token_ids']=[8,9]
    r['online_verification'].update(fallback_used=True,fallback_generated=True,
      fallback_batch_seconds=.2,fallback_executed_job_ids=['a'])
    validate_evidence(j,r,c)

def test_direct_path_rejects_wrong_context_and_spurious_proof():
    j,r,c=job_result();validate_evidence(j,r,c)
    r['online_verification']={}
    with pytest.raises(ValueError):validate_evidence(j,r,c)

class EvidenceFake(Fake):
    def poll(self):
        jobs=self.jobs;rows=super().poll()
        if rows:
            for j,r in zip(jobs,rows):
                if j['role']=='authority':
                    r.update(ces_operation=j['ces_operation'],execution_context_audit={
                       'executed_prompt_tokens':j['prompt_tokens'],'actual_audio_sha256':j['prefix_audio_sha256'],'fault_override':False})
                    if j['ces_operation']=='verify':
                        r['token_ids']=list(j['candidate_token_ids'])
                        r['online_verification']={'mode':'strict','target_identity':target_identity(j),'dtype':'float32',
                          'context_override_used':False,'executed_prompt_tokens':j['prompt_tokens'],'actual_audio_sha256':j['prefix_audio_sha256'],
                          'fallback_used':False,'candidate_accepted':True,'predicted_token_ids':list(j['candidate_token_ids']),
                          'candidate_margins':[0.]*len(j['candidate_token_ids']),'eos_token_ids':[999]}
        return rows

def owner(mode,path=None):
    clk=Clock();cfg={'policy':'fine_certified','rho':1,'fine_seconds':2,'sample_rate':16000,
      'authority_runtime':{'dtype':'float32','max_new_tokens':1},'proposal_runtime':{'dtype':'float16'},
      'microbatch':2,'timeout_seconds':20,'proposal_barrier':'decoupled','proposal_reconciliation':'lazy',
      'verification_policy':'causal_evidence_choice','journal_sync_mode':'group_ready',
      'evidence_type':'cpu_fixture_only','ces_study':{'method':mode,'calibration':CAL,'fault_plan':{},'donors':[],
       'display_slo':2.,'commit_slo':8.,'wait_cap':.15}}
    return CESScheduler(sessions=[{'session_id':i,'source_id':str(i),'audio':np.zeros(96000,dtype='<f4').tobytes(),'offset':i*.05,'language':'English'} for i in range(2)],
      contract=cfg,executors={'proposal':[EvidenceFake('p',clk)],'authority':[EvidenceFake('a',clk)]},
      clock=clk,sleep=clk.sleep,emit=lambda x:None,durable_journal_path=path)

@pytest.mark.parametrize('mode',['fine','standard','strict','readiness','ready_any','cost_gate','cost','causal_only','ces'])
def test_actual_owner_installs_complete_history_and_wal_resume(mode,tmp_path):
    wal=tmp_path/'state.wal';s=owner(mode,wal);r=s.run();s.close()
    assert r['certified_commits']==6 and r['fine_window_accounting_complete']
    resumed=owner(mode,wal);assert all(v.done for v in resumed.sessions.values())
    assert not resumed.jobs;resumed.close()

def test_stale_parent_rejected_before_canonical_install():
    s=owner('fine');s.clock.sleep(2.1);s._dispatch();s.clock.sleep(.01)
    original=s.executors['authority'][0].poll
    def corrupt():
        rr=original()
        for r in rr or []:s.jobs[r['job_id']]['parent']=-1
        return rr
    s.executors['authority'][0].poll=corrupt
    with pytest.raises(AssertionError,match='stale result'):s._receive()
    assert all(v.state.checkpoint_id==0 for v in s.sessions.values())

def test_wrong_declared_policy_cannot_resume_same_wal(tmp_path):
    from revtrace.durable_journal import JournalError
    wal=tmp_path/'state.wal';s=owner('strict',wal);s.run();s.close()
    with pytest.raises(JournalError,match='contract mismatch'):owner('ces',wal)
