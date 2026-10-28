"""CPU actuator/protocol controls; no CUDA or measured model-speedup claim."""
from dataclasses import asdict,replace
from pathlib import Path
from types import SimpleNamespace
import queue
import sys
import time

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import tc_live_worker
from row_delivery_worker import RowDeliveryTap
from row_delivery_executor import RowGPUExecutor
from revtrace.row_lifecycle import BatchDrained,CancelRequest,RowBinding,RowCancelled,RowComplete,RowInbox


class Tokenizer:
    def decode(self,tokens,**kwargs):return ' '.join(map(str,tokens))
    def encode(self,text):return [int(x) for x in text.split()] if text else []


class TokenEvent:
    def __init__(self,value):self.value=value
    def tolist(self):return self.value


def binding(job='p',role='proposal'):
    return RowBinding('w','inc','batch',job,0,role,2,1,'contract','runtime',0,32000,'audio','input')


def tap_fixture(*,enabled=True,roles=('proposal','proposal')):
    sink=queue.Queue();commands=queue.Queue()
    cfg={'runtime_digest':'runtime','max_new_tokens':8,'physical_retirement':enabled}
    tap=RowDeliveryTap(sink,SimpleNamespace(tokenizer=Tokenizer()),
      lambda text,**kw:('English',text),cfg,[9],commands)
    jobs=[]
    for i,role in enumerate(roles):
        b=binding('p'+str(i),role)
        jobs.append({'job_id':b.job_id,'role':role,'language':'English','prompt_tokens':[],
          'chunk_id':0,'_delivery':{'worker':'w','incarnation':'inc','batch_id':'batch','binding':asdict(b)}})
    tap.prepare(jobs,prefixes=['']*len(jobs),contexts=[{'actual_audio_sha256':'audio'}]*len(jobs),
      audits=[{'CPU_fixture_only':True}]*len(jobs),started=0.)
    tap.set_phase('independent-generate',.1,range(len(jobs)))
    stream=tap.stream();stream.put(TokenEvent([[1] for _ in jobs]))
    return tap,stream,sink,commands


def cancellation(tap,index=0,**kwargs):
    return CancelRequest(tap.bindings[index],kwargs.get('request_id','cancel-1'),
      kwargs.get('reason','trusted-covered'),kwargs.get('requested_perf',time.perf_counter()))


def events(sink):
    result=[]
    while not sink.empty():result.append(sink.get_nowait())
    return result


def fake_torch(monkeypatch):
    monkeypatch.setitem(sys.modules,'torch',SimpleNamespace(bool='bool',
      tensor=lambda values,**kwargs:list(values)))


def test_request_waits_for_decode_boundary_and_does_not_free_worker():
    tap,stream,sink,commands=tap_fixture()
    commands.put(cancellation(tap));stream.put(TokenEvent([3,4]))
    assert not tap.cancelled and not stream.cancelled[0]
    tap.poll_cancellations(stream)
    message=events(sink)[0]['message']
    assert isinstance(message,RowCancelled) and message.decoded_tokens==1
    assert not stream.all_terminal and 0 not in tap.rows


def test_safe_point_mask_stops_whole_generation_only_when_all_terminal(monkeypatch):
    fake_torch(monkeypatch)
    tap,stream,sink,commands=tap_fixture();criterion=tap.stopping_criterion(stream)
    stream.put(TokenEvent([4,5]));commands.put(cancellation(tap))
    assert criterion(SimpleNamespace(device='cpu'),None)==[True,False]
    stream.put(TokenEvent([0,9]))
    assert criterion(SimpleNamespace(device='cpu'),None)==[True,True]
    stream.end()
    assert len(tap.rows)==1 and tap.rows[1]['token_ids']==[5,9]


def test_cancelled_prefix_never_rendered_and_fixed_layout_cost_runs_to_actual_end():
    tap,stream,sink,commands=tap_fixture();stream.put(TokenEvent([4,9]))
    commands.put(cancellation(tap));tap.poll_cancellations(stream);stream.end()
    physical_end=time.perf_counter();tap.record_physical_completion(started=.1,completed=physical_end,indices=[0,1])
    tap.finish([None,tap.rows[1]])
    result=events(sink)
    assert [x['kind'] for x in result]==['row-complete','row-cancelled','batch-drained']
    accounting=result[-1]['physical_accounting']
    assert accounting['job_ids']==['p0','p1']
    assert [x['job_id'] for x in accounting['selected_output_digests']]==['p1']
    assert set(accounting['row_receipt_digests'])=={'p1'}
    assert set(accounting['cancelled_row_receipt_digests'])=={'p0'}
    assert accounting['phases'][0]['completed_perf']==physical_end
    assert accounting['phases'][0]['physical_batch_rows']==2
    assert accounting['phases'][0]['executed_job_ids']==['p0','p1']
    assert accounting['masked_row_compute_charged_until_batch_drain'] is True
    assert accounting['batch_drained_perf']>=physical_end


def test_cancel_mask_without_synchronized_physical_completion_cannot_drain():
    tap,stream,sink,commands=tap_fixture();commands.put(cancellation(tap));tap.poll_cancellations(stream)
    with pytest.raises(ValueError,match='synchronized physical'):tap.finish([None,None])
    assert all(x['kind']!='batch-drained' for x in events(sink))


def test_all_cancelled_batch_has_empty_selected_manifest_and_real_full_phase():
    tap,stream,sink,commands=tap_fixture()
    for i in range(2):commands.put(cancellation(tap,i,request_id='c'+str(i)))
    stream.put(TokenEvent([4,5]));tap.poll_cancellations(stream);stream.end()
    tap.record_physical_completion(started=.1,completed=time.perf_counter(),indices=[0,1])
    tap.finish([None,None]);drained=events(sink)[-1]
    assert drained['message'].row_digests==()
    assert len(drained['message'].cancelled_digests)==2
    assert drained['physical_accounting']['selected_output_digests']==[]
    assert drained['physical_accounting']['phases'][0]['physical_batch_rows']==2


def test_final_complete_object_for_cancelled_index_is_rejected():
    tap,stream,sink,commands=tap_fixture()
    commands.put(cancellation(tap));tap.poll_cancellations(stream)
    tap.record_physical_completion(started=.1,completed=time.perf_counter(),indices=[0,1])
    with pytest.raises(ValueError,match='must not carry a complete'):tap.finish([{'token_ids':[4]},None])


def test_eos_completion_wins_request_race():
    tap,stream,sink,commands=tap_fixture();stream.put(TokenEvent([9,5]))
    commands.put(cancellation(tap));tap.poll_cancellations(stream)
    assert not tap.cancelled and stream.done[0] and not stream.cancelled[0]
    result=events(sink)
    assert [x['kind'] for x in result]==['row-complete','cancel-completion-win']


@pytest.mark.parametrize('change',[{'worker_incarnation':'old'},{'batch_id':'old'},{'parent':7},{'input_identity':'wrong'}])
def test_stale_worker_request_does_not_change_decode_state(change):
    tap,stream,sink,commands=tap_fixture()
    commands.put(replace(cancellation(tap),binding=replace(tap.bindings[0],**change)))
    tap.poll_cancellations(stream)
    assert stream.cancelled==[False,False] and not tap.cancelled
    assert events(sink)[0]['kind']=='cancel-rejected'


def test_authority_and_future_clock_requests_rejected_before_stream_mutation():
    for authority in [False,True]:
        tap,stream,sink,commands=tap_fixture(roles=('authority' if authority else 'proposal','proposal'))
        when=time.perf_counter()+100 if not authority else time.perf_counter()
        commands.put(cancellation(tap,requested_perf=when));tap.poll_cancellations(stream)
        assert not tap.cancelled and stream.cancelled==[False,False]
        assert events(sink)[0]['kind']=='cancel-rejected'


def test_no_cancel_complete_receipts_byte_identical_with_actuator_enabled(monkeypatch):
    monkeypatch.setattr(time,'perf_counter',lambda:10.)
    messages=[]
    for enabled in [False,True]:
        tap,stream,sink,commands=tap_fixture(enabled=enabled)
        stream.put(TokenEvent([4,5]));stream.put(TokenEvent([9,9]));stream.end()
        tap.finish([tap.rows[0],tap.rows[1]])
        messages.append([asdict(x['message']) for x in events(sink)])
    assert messages[0]==messages[1]


def test_prepare_drops_previous_batch_physical_phases():
    tap,stream,sink,commands=tap_fixture();tap.explicit_phases=[{'old':True}]
    tap.prepare(tap.jobs,prefixes=tap.prefixes,contexts=tap.contexts,audits=tap.audits,started=1.)
    assert not hasattr(tap,'explicit_phases') and tap.physical_completion is None


def executor_fixture():
    executor=object.__new__(RowGPUExecutor)
    executor.name='w';executor.incarnation='inc';executor._physical_retirement=True
    executor._cancellations=[];executor.cancel_request_history=[];executor._telemetry=[]
    executor.execution_phase='model-executing';executor.batch_drained=False
    executor.process=SimpleNamespace(is_alive=lambda:True)
    executor.results=queue.Queue();executor.cancel_commands=queue.Queue()
    executor.inbox=RowInbox('w','inc');executor.inbox.begin('batch',[binding(),binding('a','authority')])
    return executor


def test_executor_registers_request_before_ipc_and_remains_physically_leased():
    executor=executor_fixture()
    class RegisteredQueue:
        def put(self,message):
            assert executor.inbox.cancel_requests[message.request_id]==message
            self.message=message
    executor.cancel_commands=RegisteredQueue()
    audit=executor.cancel_job('p','trusted-covered')
    assert audit['status']=='new-request' and audit['physical_worker_released'] is False
    assert executor.cancel_commands.message.binding==binding()
    assert not executor.batch_drained and not executor.inbox.worker_reusable


def test_executor_unknown_authority_and_disabled_requests_rejected():
    for job,enabled in [('a',True),('missing',True),('p',False)]:
        executor=executor_fixture();executor._physical_retirement=enabled
        audit=executor.cancel_job(job,'watchdog')
        assert audit['status']=='rejected' and executor.cancel_commands.empty()
        assert not executor.inbox.seen and executor.cancel_request_history==[audit]


def test_executor_applied_cancel_delivers_no_complete_result_and_waits_for_drain():
    executor=executor_fixture();audit=executor.cancel_job('p','trusted-covered')
    req=executor.cancel_commands.get_nowait()
    message=RowCancelled.seal(req,acknowledged=time.perf_counter(),emitted=time.perf_counter(),decoded_tokens=3)
    executor.results.put({'kind':'row-cancelled','message':message})
    assert executor.poll() is None
    cancellations=executor.drain_cancellations()
    assert len(cancellations)==1 and cancellations[0]['kind']=='cancel-applied'
    assert cancellations[0]['message']==asdict(message)
    assert cancellations[0]['terminal_digest']==message.terminal_digest
    assert executor.drain_cancellations()==[]
    assert not executor.batch_drained and not executor.inbox.worker_reusable
    b=binding('a','authority')
    done=RowComplete.seal(b,{'job_id':'a','runtime_digest':'runtime'},
      terminal=time.perf_counter(),rendered=time.perf_counter(),emitted=time.perf_counter())
    executor.results.put({'kind':'row-complete','message':done});assert len(executor.poll())==1
    drained=BatchDrained('w','inc','batch',tuple(executor.inbox.completed_digests.items()),time.perf_counter(),
      tuple(executor.inbox.cancelled_digests.items()))
    executor.results.put({'kind':'batch-drained','message':drained,'physical_accounting':{'job_ids':['p','a']}})
    assert executor.poll()==[] and executor.batch_drained and executor.inbox.worker_reusable


def test_executor_completion_win_has_explicit_telemetry_and_no_cancelled_record():
    executor=executor_fixture();executor.cancel_job('p','parent-version')
    done=RowComplete.seal(binding(),{'job_id':'p','runtime_digest':'runtime'},
      terminal=time.perf_counter(),rendered=time.perf_counter(),emitted=time.perf_counter())
    executor.results.put({'kind':'row-complete','message':done});assert len(executor.poll())==1
    assert executor.drain_cancellations()==[]
    assert any(x['kind']=='cancel-completion-win' for x in executor._telemetry)
    audit=executor.cancel_job('p','late-request')
    assert audit['status']=='already-terminal'


def test_base_executor_has_independent_cancellation_queue_and_optional_worker_argument(monkeypatch):
    processes=[]
    class FakeProcess:
        def __init__(self,**kwargs):self.kwargs=kwargs;processes.append(self)
        def start(self):pass
    context=SimpleNamespace(Queue=queue.Queue,Process=FakeProcess)
    monkeypatch.setattr(tc_live_worker.mp,'get_context',lambda name:context)
    executor=tc_live_worker.GPUExecutor('fixture',{})
    assert executor.cancel_commands is not executor.commands
    assert len(processes[0].kwargs['args'])==4
    assert processes[0].kwargs['args'][3] is executor.cancel_commands


def test_unimplemented_adapter_cannot_silently_claim_retirement_support():
    sink=queue.Queue()
    tc_live_worker.worker_main(queue.Queue(),sink,{'model_adapter':'whisper','physical_retirement':True})
    assert sink.get_nowait()['kind']=='error'
