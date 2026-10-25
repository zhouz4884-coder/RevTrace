from pathlib import Path
from dataclasses import replace,asdict
import copy,queue,sys,os
import pytest
W=Path(__file__).resolve().parents[1];R=Path(os.environ.get('REVTRACE_RUNTIME',W/'runtime_n5_v3'));sys.path.insert(0,str(R/'src'))
from revtrace.row_lifecycle import RowBinding,RowComplete,BatchDrained,RowInbox
from role_channel import OwnProposerChannel

def setup(role='proposal',window=3):
    b=RowBinding('p','inc','batch','j',0,role,2,1,'contract','runtime',64000,96000,'audio','input')
    j=dict(job_id='j',role=role,session_id=0,parent=2,audio_end_sample=96000,end_window=window,chunk_id=2,prompt_tokens=[4])
    body=dict(job_id='j',runtime_digest='runtime',token_ids=[3,0],state_tokens=[4,3,0],text='original',
        generated_tokens=2,hit_token_limit=False,terminated_by_eos=True,model_input_audit={'CPU_fixture':True})
    m=RowComplete.seal(b,body,terminal=1.,rendered=2.,emitted=3.)
    a=dict(schema='CPU_FIXTURE',row_receipt_digests={'j':m.payload_digest},job_ids=['j'],phases=[dict(started_perf=.1,completed_perf=1.)],
        selected_output_digests=[dict(job_id='j',generated_tokens=2)],batch_drained_perf=4.)
    drain=dict(kind='batch-drained',message=BatchDrained('p','inc','batch',(('j',m.payload_digest),),4.),physical_accounting=a)
    channel=OwnProposerChannel(queue.Queue(),worker_name='p',job_lookup=lambda _:j,target_window=3,
        build_tokens=lambda _:[90,91,92,0],render=lambda j,z:([*j['prompt_tokens'],*z],'benign marker'),eos=[0])
    inbox=RowInbox('p','inc');inbox.begin('batch',[b]);return b,j,m,drain,channel,inbox

def test_coherent_own_row_and_drain_pass_transport_not_selection():
    b,j,m,d,c,inbox=setup();old=copy.deepcopy(d)
    corrupted=c.transform(dict(kind='row-complete',message=m));kind,r=inbox.receive(corrupted['message'])
    assert kind=='new-complete' and r['state_tokens']==[4,90,91,92,0]
    out=c.transform(d);inbox.drain(out['message']);assert inbox.worker_reusable
    assert corrupted['message'].binding==b and d==old and c.original_physical_accounting==[old['physical_accounting']]
    assert out['physical_accounting']['phases']==old['physical_accounting']['phases']
    assert c.transforms[0]['original_message']['payload_json']!=c.transforms[0]['corrupted_message']['payload_json']

def test_corrupting_only_row_without_drain_manifest_fails_closed():
    b,j,m,d,c,inbox=setup();inbox.receive(c.transform(dict(kind='row-complete',message=m))['message'])
    with pytest.raises(ValueError,match='row manifest'):inbox.drain(d['message'])

def test_authority_capability_forbidden():
    b,j,m,d,c,inbox=setup(role='authority')
    with pytest.raises(ValueError,match='Authority'):c.transform(dict(kind='row-complete',message=m))

@pytest.mark.parametrize('z',[[],[1],[0,2],[90,0,91,0],[90]*257+[0]])
def test_payload_shape_budget_and_stop(z):
    b,j,m,d,c,inbox=setup();c.build_tokens=lambda _:z
    with pytest.raises(ValueError):c.transform(dict(kind='row-complete',message=m))

def test_wrong_target_and_duplicate_have_no_second_injection():
    b,j,m,d,c,inbox=setup(window=4);assert c.transform(dict(kind='row-complete',message=m))['message']==m
    j['end_window']=3;changed=c.transform(dict(kind='row-complete',message=m))
    assert c.transform(dict(kind='row-complete',message=m))['message']==changed['message'] and len(c.transforms)==1

def test_mutated_identity_cannot_borrow_own_channel():
    b,j,m,d,c,inbox=setup();j['parent']=9
    with pytest.raises(ValueError,match='identity'):c.transform(dict(kind='row-complete',message=m))

def test_consistent_duplicate_does_not_create_an_extra_row():
    b,j,m,d,c,inbox=setup();changed=c.transform(dict(kind='row-complete',message=m))
    assert inbox.receive(changed['message'])[0]=='new-complete'
    assert inbox.receive(c.transform(dict(kind='row-complete',message=m))['message'])[0]=='duplicate'
    inbox.drain(c.transform(d)['message']);assert inbox.worker_reusable
