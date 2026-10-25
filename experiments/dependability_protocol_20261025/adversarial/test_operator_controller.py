"""CPU mechanics only; no actual model/FP32 arithmetic or ASR result."""
from pathlib import Path
import sys,time,os
import pytest
W=Path(__file__).resolve().parents[1];R=Path(os.environ.get('REVTRACE_RUNTIME',W/'runtime_n5_v3'));sys.path.insert(0,str(R/'src'))
from operator_controller import PreparedOwner,FeedbackOperator
from revtrace.live_qwen import fingerprint
from revtrace.online_admission import target_identity

@pytest.mark.parametrize('method',['renderer_only','strict','revtrace','standard'])
@pytest.mark.parametrize('attack',[False,True])
def test_cpu_prepared_trace_parent_and_selection(method,attack,tmp_path):
    render=lambda j,Z:([*j['prompt_tokens'],*Z],' '.join(map(str,[*j['prompt_tokens'],*Z])))
    rt=dict(dtype='float32',max_new_tokens=256,CPU_fixture_only=True)
    cfg=dict(policy='fine_certified',rho=1,fine_seconds=2,sample_rate=16000,authority_runtime=rt,
        proposal_runtime=dict(dtype='float16'),trusted_text_binding=True,proposal_reconciliation='lazy',
        proposal_barrier='decoupled',display_protocol='canonical-snapshot-v1',capture_worker_records=True,
        retain_verified_private_prefix=True,durability_mode='wal',journal_sync_mode='single',
        evidence_type='cpu_fixture_prepared_operator_no_neural_GPU')
    events=[]
    owner=PreparedOwner(sessions=[dict(session_id=0,audio=bytes(16000*10*4),source_id='CPU',language='English',offset=0)],
        contract=cfg,executors={'proposal':[object()],'authority':[object()]},emit=events.append,
        durable_journal_path=tmp_path/'canonical.wal',trusted_render=render)
    def execute(j,purpose):
        begin=time.perf_counter();native=[10+j['end_window'],0];Z=native;fallback=True
        if j['role']=='proposal':
            if attack and j['end_window']==3:Z=[90,91,92,0]
        elif j['candidate_token_ids'] and method=='renderer_only':Z=j['candidate_token_ids'];fallback=False
        elif j['candidate_token_ids']==native:Z=native;fallback=False
        P,Y=render(j,Z);end=time.perf_counter()
        r=dict(job_id=j['job_id'],runtime_digest=j['runtime_digest'],prefix_audio_sha256=j['prefix_audio_sha256'],
            started_perf=begin,completed_perf=end,token_ids=Z,state_tokens=P,text=Y,generated_tokens=len(Z),hit_token_limit=False,
            model_input_audit={'rollback_prefix':j['prompt_tokens'],'CPU_fixture_only':True})
        p=dict(phases=[])
        if j['role']=='authority':
            r['online_verification']=dict(mode='unprotected' if method=='renderer_only' else 'strict',target_identity=target_identity(j),
                dtype='float32',context_override_used=False,executed_prompt_tokens=j['prompt_tokens'],actual_audio_sha256=j['prefix_audio_sha256'],
                fallback_used=fallback,fallback_generated=fallback,fallback_executed_job_ids=[j['job_id']] if fallback else [],
                unsafe_no_FP32_selection=method=='renderer_only',predicted_token_ids=native,candidate_margins=[0,0],eos_token_ids=[0])
            if fallback:p['phases']=[dict(phase='fresh-FP32-fallback',executed_job_ids=[j['job_id']],started_perf=begin,completed_perf=end)]
        return r,p
    contains=lambda x:90 in x if isinstance(x,list) else '90' in x
    try:r=FeedbackOperator(owner,execute=execute,method=method,contains_payload=contains).run()
    finally:owner.close()
    assert r['final_frontier']==160000 and r['actual_operator_requests']>0
    assert r['actual_private_descendant_prompt_has_payload']==attack
    assert r['unchecked_candidate_installs']==(1 if method=='renderer_only' else 0)
    assert contains(r['final_canonical_P'])==(attack and method=='renderer_only')
    assert all(not e.get('context_override_used') for e in events)
