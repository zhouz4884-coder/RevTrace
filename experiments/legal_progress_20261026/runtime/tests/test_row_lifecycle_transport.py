from dataclasses import FrozenInstanceError,replace
import pytest
from revtrace.row_lifecycle import RowBinding,RowComplete,BatchDrained,RowInbox,owner_action

def binding(job='a',role='authority'):
    return RowBinding('w','inc1','batch1',job,0,role,0,1,'chi','rt',0,32000,'audio','input')
def row(b=None,token=9):
    b=b or binding();return RowComplete.seal(b,{'job_id':b.job_id,'runtime_digest':b.runtime_digest,'token_ids':[token]},terminal=1,rendered=2,emitted=3)
def inbox():
    x=RowInbox('w','inc1');x.begin('batch1',[binding(),binding('b')]);return x
def drain(x):return BatchDrained('w','inc1','batch1',tuple(x.seen.items()),5)

def test_immutable_binding():
    with pytest.raises(FrozenInstanceError):binding().parent=1
def test_immutable_payload_snapshot():
    p={'job_id':'a','runtime_digest':'rt','token_ids':[9]};r=RowComplete.seal(binding(),p,terminal=1,rendered=2,emitted=3)
    p['token_ids'][0]=4;assert r.decode()['token_ids']==[9]
def test_first_row_never_frees_worker():
    x=inbox();assert x.receive(row())[0]=='new-complete';assert not x.worker_reusable
def test_all_rows_still_do_not_free_worker():
    x=inbox();x.receive(row());x.receive(row(binding('b')));assert not x.worker_reusable
    x.drain(drain(x));assert x.worker_reusable
def test_duplicate_exact_does_not_reinstall():
    x=inbox();assert x.receive(row())[0]=='new-complete';assert x.receive(row())==('duplicate',None)
def test_duplicate_conflict_poisoned():
    x=inbox();x.receive(row())
    with pytest.raises(ValueError):x.receive(row(token=4))
    assert not x.worker_reusable
@pytest.mark.parametrize('change',[{'batch_id':'wrong'},{'job_id':'wrong'},{'session_id':1},{'parent':1},{'role':'proposal'},{'runtime_digest':'other'},{'worker_incarnation':'old'}])
def test_wrong_transport_binding_fail_closed(change):
    x=inbox()
    with pytest.raises(ValueError):x.receive(row(replace(binding(),**change)))
    assert not x.worker_reusable
def test_missing_rows_no_drain():
    x=inbox();x.receive(row())
    with pytest.raises(ValueError):x.drain(drain(x))
def test_no_double_worker_dispatch():
    x=inbox()
    with pytest.raises(ValueError):x.begin('batch2',[replace(binding(),batch_id='batch2')])
def test_old_drained_rejected_during_new_batch():
    x=inbox();x.receive(row());x.receive(row(binding('b')));old=drain(x);x.drain(old)
    x.begin('batch2',[replace(binding(),batch_id='batch2')])
    with pytest.raises(ValueError):x.drain(old)
def test_parent_update_rejects_authority():
    assert owner_action(binding(),current_parent=1,contract_epoch=1,contract_digest='chi',runtime_digest='rt')=='reject-stale-authority'
def test_private_never_gets_write_authority():
    b=binding(role='proposal')
    assert owner_action(b,current_parent=0,contract_epoch=1,contract_digest='chi',runtime_digest='rt')=='validate-provisional-only'
def test_compatible_old_private_is_not_blanket_rejected():
    b=binding(role='proposal')
    assert owner_action(b,current_parent=1,contract_epoch=1,contract_digest='chi',runtime_digest='rt',provisional_compatible=True)=='validate-provisional-only'
def test_incompatible_old_private_rejected():
    assert owner_action(binding(role='proposal'),current_parent=1,contract_epoch=1,contract_digest='chi',runtime_digest='rt')=='reject-incompatible-private'
def test_contract_update_rejected():
    assert owner_action(binding(),current_parent=0,contract_epoch=2,contract_digest='chi',runtime_digest='rt')=='reject-contract'
def test_mutated_serialized_payload_rejected():
    x=inbox()
    with pytest.raises(ValueError):x.receive(replace(row(),payload_json='{}'))
def test_noncausal_completion_clock_rejected():
    with pytest.raises(ValueError):replace(row(),rendered_perf=0).decode()
def test_nonfinite_score_metadata_can_still_take_valid_fallback():
    import math
    p={'job_id':'a','runtime_digest':'rt','online_verification':{'candidate_margins':[float('nan')],'fallback_used':True}}
    r=RowComplete.seal(binding(),p,terminal=1,rendered=2,emitted=3)
    assert math.isnan(r.decode()['online_verification']['candidate_margins'][0])
def test_nonfinite_clocks_fail_closed():
    with pytest.raises(ValueError):replace(row(),terminal_perf=float('inf'),rendered_perf=float('inf'),emitted_perf=float('inf')).decode()
def test_nonfinite_result_clock_rejected():
    p={'job_id':'a','runtime_digest':'rt','completed_perf':float('nan')}
    with pytest.raises(ValueError):RowComplete.seal(binding(),p,terminal=1,rendered=2,emitted=3).decode()
def test_drain_before_earlier_row_emission_rejected():
    x=inbox();x.receive(row());x.receive(row(binding('b')))
    with pytest.raises(ValueError):x.drain(replace(drain(x),completed_perf=2))
def test_spawn_pickle_retains_immutable_binding_and_payload():
    import pickle
    x=row();y=pickle.loads(pickle.dumps(x));assert x==y and x.decode()==y.decode()
