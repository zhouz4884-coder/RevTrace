"""CPU construction checks, not model or performance evidence."""
import copy,hashlib
import numpy as np
from paid_wait_operator import prepare_jobs,resolve_model_path
import pytest


def fixture():
    x=np.arange(16,dtype='<f4')
    job=dict(job_id='p',source_id='s',role='proposal',prompt_tokens=[3],chunk_id=4,parent=2,audio_start_sample=8,audio_end_sample=16,audio_ready_perf=1.,enqueue_perf=2.,branch_generation=9,_delivery={'old':'binding'})
    case=dict(fixed_physical_batch_order=['p'],members_in_original_order=[dict(job=job)],witness=dict(job_id='p',input_before_wait=dict(prompt_tokens=[1,2],chunk_id=3,parent=1,root_frontier=4,target_frontier=16),actual_frozen_input=dict(prompt_tokens=[3],chunk_id=4,parent=2,root_frontier=8,target_frontier=16)),before_parent_commit=dict(version=1,next_prompt_tokens=[1]),old_branch_generation=8)
    return case,{'s':x}


def test_old_snapshot_remains_old_parent_and_rebinds_only_operator_identity():
    case,audio=fixture();original=copy.deepcopy(case)
    jobs,ids=prepare_jobs(case,'old',0,audio,20.)
    j=jobs[0]
    assert j['parent']==1 and j['prompt_tokens']==[1,2] and j['audio_start_sample']==4
    assert '_delivery' not in j and j['enqueue_perf']==20. and ids[j['job_id']]=='p'
    assert j['interval_audio_sha256']==hashlib.sha256(audio['s'][4:16].tobytes()).hexdigest()
    assert case==original


def test_new_snapshot_retains_actual_input_and_original_member_order():
    case,audio=fixture();jobs,_=prepare_jobs(case,'new',1,audio,20.)
    assert jobs[0]['parent']==2 and jobs[0]['prompt_tokens']==[3] and jobs[0]['audio_start_sample']==8
    assert jobs[0]['audio_end_sample']==16 and jobs[0]['chunk_id']==4


def test_archived_model_basename_uses_the_same_declared_store(tmp_path):
    assert resolve_model_path('Qwen3-ASR-1.7B',tmp_path)==tmp_path/'Qwen3-ASR-1.7B'
    with pytest.raises(ValueError):resolve_model_path('../outside',tmp_path)
    with pytest.raises(ValueError):resolve_model_path(tmp_path.parent/'outside',tmp_path)
