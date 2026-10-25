"""Actual executor-poll CPU queue controls; no CUDA/model process is started."""
from dataclasses import replace
from pathlib import Path
import queue,sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from row_delivery_executor import RowGPUExecutor
from revtrace.row_lifecycle import RowBinding,RowComplete,BatchDrained,RowInbox
from revtrace.row_lifecycle import digest

class Process:
    def is_alive(self):return True
def binding(j):return RowBinding('w','inc','batch',j,0,'authority',0,1,'chi','rt',0,10,'audio','input')
def message(j):
    b=binding(j);return RowComplete.seal(b,{'job_id':j,'runtime_digest':'rt','started_perf':0.,'completed_perf':2.},terminal=1.,rendered=2.,emitted=3.)
def worker():
    w=object.__new__(RowGPUExecutor);w.name='w';w.incarnation='inc';w.results=queue.Queue()
    w.process=Process();w.batch_drained=False;w._telemetry=[];w.execution_phase='model-executing'
    w.inbox=RowInbox('w','inc');w.inbox.begin('batch',[binding('a'),binding('b')]);return w
def put(w,j):w.results.put({'kind':'row-complete','message':message(j)})
def finish(w):
    m=BatchDrained('w','inc','batch',tuple(w.inbox.seen.items()),5.)
    w.results.put({'kind':'batch-drained','message':m,'physical_accounting':{'batch_id':'batch','job_ids':['a','b']}})

def test_partial_receipt_cannot_reuse_worker():
    w=worker();put(w,'a');assert [r['job_id'] for r in w.poll()]==['a']
    assert not w.batch_drained and not w.inbox.worker_reusable
def test_all_rows_wait_for_drain():
    w=worker();put(w,'a');put(w,'b');assert len(w.poll())==2
    assert not w.batch_drained;finish(w);assert w.poll()==[] and w.batch_drained
def test_duplicate_receipt_not_delivered_twice():
    w=worker();put(w,'a');put(w,'a');assert len(w.poll())==1
def test_wrong_batch_fails_closed():
    w=worker();m=message('a');m=replace(m,binding=replace(m.binding,batch_id='other'))
    w.results.put({'kind':'row-complete','message':m})
    with pytest.raises(ValueError):w.poll()
def test_legacy_worker_response_is_not_silently_accepted():
    w=worker();w.results.put({'kind':'result','rows':[]})
    with pytest.raises(RuntimeError):w.poll()
def test_physical_cost_separate_and_only_after_drain():
    w=worker();put(w,'a');put(w,'b');w.poll();assert not w._telemetry
    finish(w);w.poll();assert w._telemetry[0]['kind']=='batch-accounting'
def test_model_phase_is_not_a_completed_row():
    w=worker();w.results.put({'kind':'model-completed','job_ids':['a','b'],'completed_perf':1.})
    assert w.poll() is None and not w.inbox.seen and not w.batch_drained
def test_drain_missing_a_row_fails_closed():
    w=worker();put(w,'a');w.poll();finish(w)
    with pytest.raises(ValueError):w.poll()
def test_raw_receipt_fingerprint_survives_mutable_owner_annotations():
    w=worker();put(w,'a');r=w.poll()[0];proof=r.pop('_row_receipt')
    assert digest(r)==proof['payload_sha256']
    assert proof['binding']['job_id']=='a' and proof['emitted_perf']==3.
