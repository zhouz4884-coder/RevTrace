"""CPU verification of delayed-result delivery instrumentation, no CUDA."""
import importlib.util
from pathlib import Path
import queue
import pytest

spec=importlib.util.spec_from_file_location('worker_hold',Path(__file__).resolve().parents[1]/'scripts/tc_live_worker.py')
worker=importlib.util.module_from_spec(spec); spec.loader.exec_module(worker)

def test_hold_preserves_inference_clock_and_eventual_result(monkeypatch):
    now=[100.]
    monkeypatch.setattr(worker.time,'perf_counter',lambda:now[0])
    obj=object.__new__(worker.GPUExecutor)
    obj.results=queue.Queue(); obj._held_result=None; obj._deliver_after=0.
    obj.result_delay_seconds=6.
    row={'job_id':'p1','started_perf':98.,'completed_perf':99.}
    obj.results.put({'kind':'result','rows':[row]})
    assert obj.poll() is None
    now[0]=105.99
    assert obj.poll() is None
    now[0]=106.
    assert obj.poll()==[row]
    assert row['completed_perf']==99.

def test_negative_hold_rejected_before_process_creation():
    with pytest.raises(ValueError,match='nonnegative'):
        worker.GPUExecutor('unused',{'result_delay_seconds':-1})
