"""CPU interleavings only; no neural output or GPU timing evidence."""
import importlib.util
from pathlib import Path
import pytest
from revtrace.live_qwen import LiveQwenScheduler
from revtrace.late_delivery import LateDeliveryScheduler
from revtrace.certified_display import ContinuityView

spec=importlib.util.spec_from_file_location('order_fixture',Path(__file__).with_name('test_live_qwen.py'))
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)


def case(*,p=1,a=3,order='authority_first',omit=False,standard=False,view='two_lane',same=False,base=False):
    clock=f.Clock(); events=[]; consumer=ContinuityView(view,fine_samples=160,strict_bound=True)
    config={'policy':'coarse','rho':3,'fine_seconds':.01,'sample_rate':16000,
        'authority_runtime':{'dtype':'float32'},'proposal_runtime':{'dtype':'float16'},
        'microbatch':2,'timeout_seconds':3,'proposal_barrier':'decoupled',
        'proposal_reconciliation':'lazy','capture_worker_records':True,
        'display_protocol':'canonical-snapshot-v1','trusted_text_binding':True,
        'retain_verified_private_prefix':True,'evidence_type':'cpu_simulated_orchestration_only',
        'async_implementation':'standard' if standard else 'revtrace',
        'diagnostic_omit_receive_freshness':omit,'result_delivery':'batch'}
    if order:config['post_compute_order']={'proposal_window':p,'authority_window':a,
        'sessions':[0,1],'order':order,'timeout_seconds':1}
    workers={'proposal':[f.Fake('p',clock)],'authority':[f.Fake('a',clock)]}
    workers['proposal'][0].same_projection=same
    def render(j,Z):return [Z[0]+(999 if j['role']=='proposal' and not same else 0)],str(Z[0])
    def emit(e):events.append(e);consumer.consume(e,clock())
    scheduler=(LiveQwenScheduler if base else LateDeliveryScheduler)(
        sessions=[{'session_id':sid,'audio':bytes(1920*4),'source_id':str(sid),
            'language':'English','offset':0} for sid in [0,1]],
        contract=config,executors=workers,emit=emit,trusted_render=render,
        clock=clock,sleep=clock.sleep)
    result=scheduler.run()
    return scheduler,result,consumer


@pytest.mark.parametrize('p,a',[(1,3),(7,6)])
@pytest.mark.parametrize('order',['proposal_first','authority_first'])
@pytest.mark.parametrize('method',['full','omit','standard'])
@pytest.mark.parametrize('same',[False,True])
def test_complete_order_preserves_actual_authority_and_payload(p,a,order,method,same):
    s,r,c=case(p=p,a=a,order=order,omit=method=='omit',standard=method=='standard',same=same)
    assert r['post_compute_order_completed'] and r['fine_window_accounting_complete']
    commits=[e for e in s.events if e['kind']=='commit']
    assert len(commits)==8
    assert all(e['next_prompt_tokens']==[round(e['audio_end_sample']/160)] for e in commits)
    captured=[e for e in s.events if e['kind']=='ipc-complete-captured']
    delivered=[e for e in s.events if e['kind']=='ipc-complete-delivered']
    assert len(captured)==len(delivered)==4
    assert {e['job_id']:e['payload_sha256'] for e in captured}=={e['job_id']:e['payload_sha256'] for e in delivered}
    assert all(e['physically_drained'] for e in captured)
    if order=='authority_first':
        assert all(e['committed_frontier']>=a*160 for e in delivered if e['role']=='proposal')
    assert all(e['certified_frontier']<=e['valid_visible_frontier'] for e in c.records)


def test_omitting_owner_freshness_does_not_defeat_consumer_covered_target_fence():
    full,_,_=case(); weak,_,c=case(omit=True)
    def late(s):return [e for e in s.events if e['kind']=='display' and e['window']==1]
    assert late(full)==[] and len(late(weak))==2
    assert not any(e['source_kind']=='display' and e['valid_visible_frontier']==160 for e in c.records)


def test_ahead_metadata_only_and_exact_chain_views_have_distinct_guarantees():
    s,_,snapshot=case(p=7,a=6,view='snapshot')
    guarded,_,exact=case(p=7,a=6,view='two_lane')
    assert any(e['kind']=='display' and e['window']==7 and e['parent_superseded'] for e in s.events)
    assert any(e['source_kind']=='display' and e['valid_visible_frontier']==1120 for e in snapshot.records)
    assert any(e['source_kind']=='display' and e['tentative_invalidated'] for e in exact.records)
    assert not any(e['source_kind']=='display' and e['valid_visible_frontier']==1120 for e in exact.records)


def test_no_intervention_refactor_and_subclass_match_every_semantic_event():
    old,ro,co=case(order=None,base=True);new,rn,cn=case(order=None)
    assert old.jobs==new.jobs
    assert ro['final_states']==rn['final_states']
    kinds=['enqueue','display','commit','canonical-display','proposal-obsolete','proposal-skip']
    assert [e for e in old.events if e['kind'] in kinds]==[e for e in new.events if e['kind'] in kinds]
    assert co.records==cn.records


def test_unreachable_target_fails_before_any_dispatch():
    with pytest.raises(ValueError,match='outside'):
        case(p=20,a=3)
