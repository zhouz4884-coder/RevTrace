"""CPU protocol fixtures. These prove no model/GPU service speedup."""
from dataclasses import FrozenInstanceError,replace
import pickle

import pytest

from revtrace.row_lifecycle import (
    BatchDrained,CancelRequest,RowBinding,RowCancelled,RowComplete,RowInbox,
)
from revtrace.row_stream import CompleteRowStream


def binding(job='p',role='proposal'):
    return RowBinding('w','inc','batch',job,0,role,2,1,'contract','runtime',0,32000,'audio','input')


def request(b=None,request_id='cancel-1'):
    return CancelRequest(b or binding(),request_id,'trusted-covered',1.)


def cancelled(req=None):
    return RowCancelled.seal(req or request(),acknowledged=2.,emitted=3.,decoded_tokens=7)


def complete(b=None):
    b=b or binding()
    return RowComplete.seal(b,{'job_id':b.job_id,'runtime_digest':b.runtime_digest,'token_ids':[9]},
      terminal=2.,rendered=3.,emitted=4.)


def inbox():
    value=RowInbox('w','inc')
    value.begin('batch',[binding(),binding('a','authority')])
    return value


def drain(value,when=5.):
    return BatchDrained('w','inc','batch',tuple(value.completed_digests.items()),when,
      tuple(value.cancelled_digests.items()))


def mixed_terminals():
    value=inbox();value.request_cancel(request())
    value.receive(cancelled());value.receive(complete(binding('a','authority')))
    return value


def test_request_and_cancellation_receipt_immutable_and_pickleable():
    for message in [request(),cancelled()]:
        with pytest.raises(FrozenInstanceError):message.reason='changed'
        assert pickle.loads(pickle.dumps(message))==message


def test_cancel_request_is_not_completion_or_physical_release():
    value=inbox()
    assert value.request_cancel(request())=='new-request'
    assert not value.seen and not value.worker_reusable
    with pytest.raises(ValueError,match='missing terminal'):value.drain(drain(value))


def test_cancelled_receipt_has_no_partial_usable_output():
    result=cancelled().decode()
    assert result['decoded_tokens']==7 and result['row_terminal_kind']=='cancelled'
    assert not {'token_ids','state_tokens','text'}&result.keys()


def test_mixed_full_and_cancelled_rows_require_real_drain():
    value=mixed_terminals()
    assert set(value.completed_digests)=={'a'} and set(value.cancelled_digests)=={'p'}
    assert not value.worker_reusable
    value.drain(drain(value));assert value.worker_reusable


def test_cancelled_receipt_without_requested_binding_rejected():
    value=inbox()
    with pytest.raises(ValueError,match='matching owner request'):value.receive(cancelled())
    assert value.poisoned


def test_cancelled_receipt_request_identity_and_reason_bound():
    value=inbox();value.request_cancel(request())
    wrong=cancelled(replace(request(),reason='other-policy'))
    with pytest.raises(ValueError,match='matching owner request'):value.receive(wrong)


@pytest.mark.parametrize('change',[
    {'worker':'other'},{'worker_incarnation':'prior'},{'batch_id':'prior'},
    {'job_id':'other'},{'session_id':2},{'parent':1},{'input_identity':'other'},
    {'runtime_digest':'other'},{'contract_digest':'other'},
])
def test_cancel_request_requires_entire_active_binding(change):
    value=inbox()
    with pytest.raises(ValueError,match='stale cancellation'):
        value.request_cancel(request(replace(binding(),**change)))
    assert not value.seen and not value.worker_reusable


def test_cannot_cancel_authority_even_with_well_formed_request():
    req=request(binding('a','authority'))
    with pytest.raises(ValueError,match='private proposal'):req.validate()
    with pytest.raises(ValueError,match='private proposal'):cancelled(req)


def test_duplicate_request_is_idempotent_and_identity_reuse_conflicts():
    value=inbox()
    assert value.request_cancel(request())=='new-request'
    assert value.request_cancel(request())=='duplicate-request'
    with pytest.raises(ValueError,match='conflicting cancellation'):
        value.request_cancel(replace(request(),reason='new reason'))


def test_completion_can_win_after_cancel_request():
    value=inbox();value.request_cancel(request())
    assert value.receive(complete())[0]=='new-complete'
    assert value.request_cancel(request(request_id='late-request'))=='already-terminal'
    assert not value.cancelled_digests
    value.receive(complete(binding('a','authority')))
    value.drain(drain(value));assert value.worker_reusable


def test_request_after_complete_is_noop_and_does_not_authorize_cancel_terminal():
    value=inbox();value.receive(complete())
    assert value.request_cancel(request())=='already-terminal'
    assert not value.cancel_requests
    with pytest.raises(ValueError):value.receive(cancelled())


def test_completed_row_cannot_be_overwritten_by_cancellation():
    value=inbox();value.request_cancel(request());value.receive(complete())
    with pytest.raises(ValueError,match='conflicting row terminal'):value.receive(cancelled())


def test_cancelled_row_cannot_be_overwritten_by_completed_prefix():
    value=inbox();value.request_cancel(request());value.receive(cancelled())
    with pytest.raises(ValueError,match='conflicting row terminal'):value.receive(complete())


def test_cancelled_duplicate_exact_only():
    value=inbox();value.request_cancel(request())
    assert value.receive(cancelled())[0]=='new-cancelled'
    assert value.receive(cancelled())==('duplicate',None)
    wrong=RowCancelled.seal(request(),acknowledged=2.,emitted=3.,decoded_tokens=8)
    with pytest.raises(ValueError,match='conflicting row terminal'):value.receive(wrong)


def test_cancellation_digest_binds_actual_terminal_clocks_and_counts():
    for changed in [replace(cancelled(),decoded_tokens=6),replace(cancelled(),emitted_perf=4.)]:
        with pytest.raises(ValueError,match='mutated cancellation'):changed.decode()


@pytest.mark.parametrize('kwargs',[
    {'acknowledged':.5,'emitted':3.,'decoded_tokens':1},
    {'acknowledged':2.,'emitted':1.,'decoded_tokens':1},
    {'acknowledged':float('nan'),'emitted':3.,'decoded_tokens':1},
    {'acknowledged':2.,'emitted':float('inf'),'decoded_tokens':1},
    {'acknowledged':2.,'emitted':3.,'decoded_tokens':-1},
    {'acknowledged':2.,'emitted':3.,'decoded_tokens':True},
])
def test_noncausal_or_invalid_cancellation_never_seals(kwargs):
    with pytest.raises(ValueError):RowCancelled.seal(request(),**kwargs)


@pytest.mark.parametrize('change',[
    {'cancelled_digests':()},
    {'cancelled_digests':(('p','wrong'),)},
    {'cancelled_digests':(('p','wrong'),('p','wrong'))},
    {'cancelled_digests':(('unknown','wrong'),)},
    {'row_digests':()},
])
def test_physical_drain_requires_exact_disjoint_terminal_manifest(change):
    value=mixed_terminals()
    with pytest.raises(ValueError):value.drain(replace(drain(value),**change))
    assert value.poisoned and not value.worker_reusable


def test_drain_cannot_label_cancelled_digest_as_complete():
    value=mixed_terminals()
    wrong=BatchDrained('w','inc','batch',tuple(value.seen.items()),5.)
    with pytest.raises(ValueError,match='complete manifest'):value.drain(wrong)


def test_drain_cannot_precede_last_row_emission():
    value=mixed_terminals()
    with pytest.raises(ValueError,match='drain precedes'):value.drain(drain(value,when=3.))


def test_cancelled_payload_cannot_be_sealed_into_complete_result():
    b=binding();payload=cancelled().decode();payload['token_ids']=[4]
    message=RowComplete.seal(b,payload,terminal=2.,rendered=3.,emitted=4.)
    with pytest.raises(ValueError,match='cancelled prefix'):message.decode()


class TokenEvent:
    def __init__(self,value):self.value=value
    def tolist(self):return self.value


def stream(indices=(0,1),budget=4):
    calls=[]
    value=CompleteRowStream(indices,eos=[9],budget=budget,
      on_complete=lambda index,tokens,when:calls.append((index,tokens,when)))
    value.put(TokenEvent([[1] for _ in indices]))
    return value,calls


def test_cancel_drops_prefix_and_emits_no_completion():
    value,calls=stream();value.put(TokenEvent([2,3]))
    assert value.cancel([0])=={0:1}
    assert value.done==[False,False] and value.cancelled==[True,False]
    value.put(TokenEvent([9,9]));value.end()
    assert [(index,tokens) for index,tokens,_ in calls]==[(1,(3,9))]
    assert value.rows[0]==[2] and value.all_terminal


def test_stream_completion_wins_cancellation_at_same_boundary():
    value,calls=stream();value.put(TokenEvent([9,3]))
    assert value.cancel([0])=={} and len(calls)==1
    assert value.done[0] and not value.cancelled[0]
    value.cancel([1]);value.end()


def test_stream_all_cancelled_after_prompt_has_no_completed_output():
    value,calls=stream()
    assert value.cancel([0,1])=={0:0,1:0}
    assert value.all_terminal and not calls
    value.end()


def test_stream_cancellation_idempotent_and_keeps_fallback_original_indices():
    value,calls=stream((1,3));value.put(TokenEvent([5,6]))
    assert value.cancel([3])=={3:1} and value.cancel([3])=={}
    value.put(TokenEvent([9,8]));value.end()
    assert [(i,Z) for i,Z,_ in calls]==[(1,(5,9))]


@pytest.mark.parametrize('indices',[[2],[0,0]])
def test_stream_cancel_rejects_wrong_indices_before_any_mutation(indices):
    value,calls=stream()
    with pytest.raises(ValueError):value.cancel(indices)
    assert value.cancelled==[False,False] and not calls


def test_early_stop_still_rejects_undeclared_remaining_prefix():
    value,calls=stream();value.put(TokenEvent([2,3]));value.cancel([0])
    with pytest.raises(ValueError,match='incomplete row terminal'):value.end()
    assert not calls
