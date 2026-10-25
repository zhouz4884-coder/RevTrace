"""CPU check of real-worker injection placement; no model evidence."""
import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('context_worker',Path(__file__).resolve().parents[1]/'scripts/tc_live_worker.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)

def test_fault_must_be_declared_and_preserves_job_envelope():
    job={'job_id':'frozen','parent':4,'prompt_tokens':[1,2],'fault_actual_prompt_tokens':[7,8]}
    before=dict(job)
    with pytest.raises(ValueError,match='declared'):worker.execution_tokens(job)
    assert worker.execution_tokens(job,True)==(7,8)
    assert job==before

def test_no_fault_uses_original_immutable_conditioning():
    job={'prompt_tokens':[1,2]}
    assert worker.execution_tokens(job)==(1,2)
