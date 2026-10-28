"""Targeted CPU owner/queue integration; synthetic clocks, no GPU/WAL claim."""
from dataclasses import asdict,replace
from pathlib import Path
from types import SimpleNamespace
import copy
import hashlib
import queue
import sys

import pytest

W=Path(__file__).resolve().parent
for p in [W/'runtime/src',W/'runtime/scripts']:sys.path.insert(0,str(p))
from revtrace.composed_kernel import Kernel,Denied,sha
from revtrace.degradation_state import CreditBook
from revtrace.dgft import FeedbackTransactionState,digest_tokens
from revtrace.live_qwen import Session
from revtrace.retirement_runtime import RetirementScheduler
from revtrace.row_lifecycle import RowBinding,RowInbox,RowComplete,RowCancelled,BatchDrained
from row_delivery_executor import RowGPUExecutor


def fixture(incremental=False):
    owner=object.__new__(RetirementScheduler)
    owner.now=10.;owner.clock=lambda:owner.now;owner.t0=0.;owner.origin=0.
    owner.contract={'capture_worker_records':True,'async_implementation':'standard',
      'proposal_barrier':'decoupled','display_protocol':'canonical-snapshot-v1'}
    owner.contract_digest='contract';owner.runtime_digest='runtime'
    owner.retirement_policy='covered';owner.watchdog_seconds=1.
    owner._retirement_requested=set();owner._cancelled_jobs=set()
    owner.reconciliation='lazy';owner.fine=2.;owner.sample_rate=16000
    owner._proposal_results={};owner.window_outcomes={};owner.events=[];owner.emit=lambda event:None
    owner.text_binding=True;owner.trusted_render=lambda job,tokens:([3,9],'fixture text')
    owner.sessions={};owner.jobs={};owner.executors={'proposal':[],'authority':[]}
    owner.book=CreditBook(192000,epoch=1)
    owner.kernel=Kernel('contract',1,0.,incremental=incremental)
    k=owner.kernel.state
    for sid in range(2):
        state=FeedbackTransactionState(sid,1,'fine_certified',contract_digest='contract',
          canonical_runtime_digest='runtime')
        session=Session(sid,6.,0.,'English',b'\0'*384000,'source'+str(sid),state,
          fine_busy=True,auth_busy=True,branch_generation=2,segment_end=3)
        owner.sessions[sid]=session
        b=owner.book.session(sid);b.accepted=b.offered=b.reserved=96000
        b.accepted_prefix_sha256='f'*64
        k.C[sid]={'v':0,'F':0,'P':digest_tokens(()),'Z':'','textsha':hashlib.sha256(b'').hexdigest(),'txn':''}
        k.D[sid]={};k.V[sid]={'v':0,'F':0,'visible':0,'revision':0}
        k.I[sid]={'accepted':96000,'offered':96000,'reserved':96000}
        job={'job_id':'p'+str(sid),'session_id':sid,'role':'proposal','contract_epoch':1,
          'contract_digest':'contract','runtime_digest':'runtime','parent':0,
          'prompt_tokens':[],'parent_prompt_digest':digest_tokens(()),'chunk_id':0,
          'end_window':1,'audio_start_sample':0,'audio_end_sample':32000,
          'audio_ready_perf':1.,'enqueue_perf':2.,'source_id':session.source_id,
          'language':'English','prefix_audio_sha256':'prefix'+str(sid),
          'interval_audio_sha256':'interval'+str(sid),'branch_generation':2}
        owner.jobs[job['job_id']]=job
    k.ready={'w'};k.restored_input=True
    worker=object.__new__(RowGPUExecutor)
    worker.name='w';worker.incarnation='inc';worker._physical_retirement=True
    worker._cancellations=[];worker.cancel_request_history=[];worker._telemetry=[]
    worker.execution_phase='model-executing';worker.batch_drained=False
    worker.process=SimpleNamespace(is_alive=lambda:True)
    worker.results=queue.Queue();worker.cancel_commands=queue.Queue()
    worker.inbox=RowInbox('w','inc');bindings=[]
    for job in owner.jobs.values():
        b=RowBinding('w','inc','batch',job['job_id'],job['session_id'],'proposal',0,1,
          'contract','runtime',0,32000,job['interval_audio_sha256'],sha(job))
        bindings.append(b);job['_delivery']={'binding':asdict(b)}
    worker.inbox.begin('batch',bindings)
    owner.protocol_dispatch(worker,list(owner.jobs.values()))
    owner.inflight={'w':(worker,list(owner.jobs))};owner.executors['proposal']=[worker]
    # A trusted installation fixture while the old proposer batch is running.
    s=owner.sessions[0]
    s.state=replace(s.state,checkpoint_id=1,audio_frontier_window=64000,prompt_tokens=(8,))
    fact={'v':1,'F':64000,'P':digest_tokens((8,)),'Z':digest_tokens((8,)),
      'textsha':hashlib.sha256(b'canonical').hexdigest(),'txn':'fixture-txn'}
    k=owner.kernel.state;k.C[0]=fact;k.D[0]={1:fact}
    b=owner.book.session(0);b.certified=64000;b.version=1
    owner.events.append({'kind':'commit','time':7.,'installed':7.,'session_id':0,
      'audio_end_sample':64000,'version':1})
    return owner,worker


def completed(owner,worker,jid):
    job=owner.jobs[jid]
    row={'job_id':jid,'runtime_digest':'runtime','prefix_audio_sha256':job['prefix_audio_sha256'],
      'started_perf':3.,'completed_perf':14.,'token_ids':[9],'state_tokens':[3,9],
      'text':'fixture text','language':'English','generated_tokens':1,
      'terminated_by_eos':True,'hit_token_limit':False}
    return RowComplete.seal(worker.inbox.bindings[jid],row,terminal=13.,rendered=14.,emitted=14.5)


def actual_drain(worker):
    message=BatchDrained('w','inc','batch',tuple(worker.inbox.completed_digests.items()),16.,
      tuple(worker.inbox.cancelled_digests.items()))
    worker.results.put({'kind':'batch-drained','message':message,'physical_accounting':{
      'job_ids':['p0','p1'],'phases':[{'started_perf':3.,'completed_perf':15.5}]}})


@pytest.mark.parametrize('incremental',[False,True])
def test_cancel_complete_and_physical_drain_are_three_distinct_owner_steps(incremental):
    owner,worker=fixture(incremental)
    book_before=copy.deepcopy(owner.book.snapshot(owner.origin));debt_before=owner.book.debt
    canonical_before=copy.deepcopy(owner.kernel.state.C)
    owner._request_retirement();request=worker.cancel_commands.get_nowait()
    assert request.binding.job_id=='p0' and request.reason=='trusted-coverage'
    assert set(owner._retirement_requested)=={'p0'}
    assert 'w' in owner.inflight and 'w' in owner.kernel.state.leases
    cancelled=RowCancelled.seal(request,acknowledged=11.,emitted=12.,decoded_tokens=7)
    worker.results.put({'kind':'row-cancelled','message':cancelled});owner.now=13.;owner._receive()
    assert not owner.sessions[0].fine_busy and owner.sessions[0].auth_busy
    assert owner.window_outcomes[0,1]=='cancelled-private-inflight'
    assert owner.window_outcomes[0,2]=='covered-without-dispatch'
    assert owner.sessions[0].fine_window==3
    assert owner.book.snapshot(owner.origin)==book_before and owner.book.debt==debt_before
    assert owner.kernel.state.C==canonical_before
    assert (0,1) not in owner._proposal_results
    assert owner.kernel.state.J['p0']['result'] is None
    assert owner.kernel.state.J['p0']['cancelled']['terminal_digest']==cancelled.terminal_digest
    assert 'w' in owner.inflight and 'w' in owner.kernel.state.leases
    assert not worker.inbox.worker_reusable and not worker.batch_drained
    records=[e for e in owner.events if e['kind']=='worker-cancelled-record']
    assert len(records)==1 and records[0]['job']==owner.jobs['p0']
    assert records[0]['cancellation']['message']==asdict(cancelled)
    assert not any(e['kind'] in ['executor-complete','display','worker-record'] and
      (e.get('job_id')=='p0' or e.get('job',{}).get('job_id')=='p0') for e in owner.events)
    worker.results.put({'kind':'row-complete','message':completed(owner,worker,'p1')})
    owner.now=15.;owner._receive()
    assert (1,1) in owner._proposal_results and not owner.sessions[1].fine_busy
    assert owner.window_outcomes[1,1]=='provisional-display'
    assert owner.kernel.state.J['p1']['result'] is not None
    assert 'w' in owner.inflight and 'w' in owner.kernel.state.leases
    assert not worker.inbox.worker_reusable and not worker.batch_drained
    assert [w for w in owner.executors['proposal'] if w.name not in owner.inflight]==[]
    actual_drain(worker);owner.now=17.;owner._receive()
    assert 'w' not in owner.inflight and 'w' not in owner.kernel.state.leases
    assert worker.inbox.worker_reusable and worker.batch_drained
    assert owner.book.debt==debt_before and owner.kernel.state.C==canonical_before


def test_complete_can_win_after_owner_cancel_intent_without_cancellation_accounting():
    owner,worker=fixture();owner._request_retirement()
    worker.results.put({'kind':'row-complete','message':completed(owner,worker,'p0')})
    worker.results.put({'kind':'row-complete','message':completed(owner,worker,'p1')})
    owner.now=15.;owner._receive()
    assert not owner._cancelled_jobs
    assert owner.window_outcomes[0,1]=='obsolete-completion'
    assert owner.kernel.state.J['p0']['result'] is not None
    assert not owner.kernel.state.J['p0'].get('cancelled')
    assert 'w' in owner.inflight and not worker.batch_drained
    assert any(e['kind']=='worker-status' and e['status']=='cancel-completion-win' for e in owner.events)
    actual_drain(worker);owner.now=17.;owner._receive()
    assert worker.batch_drained and 'w' not in owner.kernel.state.leases


def test_cancel_terminal_does_not_waive_another_rows_terminal_obligation():
    owner,worker=fixture();owner._request_retirement();request=worker.cancel_commands.get_nowait()
    worker.results.put({'kind':'row-cancelled','message':RowCancelled.seal(request,
      acknowledged=11.,emitted=12.,decoded_tokens=4)})
    owner.now=13.;owner._receive()
    actual_drain(worker);owner.now=17.
    with pytest.raises(ValueError,match='missing terminal'):owner._receive()
    assert 'w' in owner.inflight and 'w' in owner.kernel.state.leases
    assert not worker.inbox.worker_reusable


def test_old_batch_clock_does_not_trigger_watchdog_for_new_enqueued_job():
    owner,worker=fixture();owner.retirement_policy='watchdog'
    worker._retirement_started_perf=1. # Predates this batch's enqueue at 2.
    owner._request_retirement()
    assert worker.cancel_commands.empty() and not owner._retirement_requested


def test_generation_invalidation_clock_uses_transition_after_job_birth():
    owner,worker=fixture();owner.retirement_policy='causal'
    # This proposal remains ahead of its certified frontier; only generation
    # invalidation may cancel it. An earlier retirement is unrelated history.
    owner.sessions[0].state=replace(owner.sessions[0].state,audio_frontier_window=0)
    owner.kernel.state.C[0]['F']=0;owner.kernel.state.D[0][1]['F']=0
    owner.sessions[0].branch_generation=3
    owner.events=[{'kind':'private-generation-retired','time':1.,'session_id':0,'generation':1},
      {'kind':'private-generation-retired','time':8.,'session_id':0,'generation':3}]
    owner._request_retirement()
    event=next(e for e in owner.events if e['kind']=='cancel-request' and e['job_id']=='p0')
    assert event['invalidation_kind']=='retired-generation'
    assert event['invalidated_perf']==8.
