"""Focused controls for cancellation-safe original input/Consumer metrics."""
import copy
import hashlib

import pytest

import x_service_metrics as metrics
from test_retirement_audit import fixture, full_result


def input_evidence(job):
    context = dict(executed_prompt_tokens=copy.deepcopy(job['prompt_tokens']),fault_override=False,
        declared_prompt_digest=metrics.tokens(job['prompt_tokens']),executed_prompt_digest=metrics.tokens(job['prompt_tokens']),
        actual_audio_sha256=job['prefix_audio_sha256'])
    model = dict(declared_prompt_tokens=copy.deepcopy(job['prompt_tokens']),waveform_sha256=job['prefix_audio_sha256'],
        dtype='float16',source_id=job['source_id'],chunk_id=job['chunk_id'],audio_end_sample=job['audio_end_sample'])
    return context,model


def fault_fixture():
    job=copy.deepcopy(fixture()['jobs']['p0'])
    job.update(chunk_id=4,end_window=5,language='English',prompt_tokens=[1,2,3,4,5,6],fault_actual_prompt_tokens=[20,21,22,23,24,25])
    cfg=dict(retirement_fault_fixture=dict(schema='physical-retirement-f2-input-fixture-v1',fault_plan={'0:5':0},
        targets={'0:5':dict(source_id=job['source_id'],chunk_id=4,donor_index=0)},
        donors=[dict(id='frozen-donor',tokens=[20,21,22,23,24,25])]),retirement_fault_fixture_sha256='a'*64)
    context,model=input_evidence(job)
    context.update(executed_prompt_tokens=copy.deepcopy(job['fault_actual_prompt_tokens']),fault_override=True,
        executed_prompt_digest=metrics.tokens(job['fault_actual_prompt_tokens']))
    result=dict(token_ids=[7,9],state_tokens=[4,7,9],text='declared-parent render',
        F2_raw_execution_state_tokens=[24,7,9],F2_raw_execution_text='raw wrong-context output',
        F2_normalization_scope='declared-parent fields of actual wrong-context Z, not regeneration')
    result['text_binding']=dict(render_inputs=dict(prompt_tokens=job['prompt_tokens'],chunk_id=4,
        language='English',token_ids=result['token_ids'],state_tokens=result['state_tokens']),
        rendered_text=result['text'],text_sha256=hashlib.sha256(result['text'].encode()).hexdigest())
    return job,context,model,cfg,result


def test_cancelled_jobs_remain_issued_without_creating_full_results():
    data=fixture()
    records=[dict(job=data['jobs'][jid],result=result) for jid,result in data['results'].items()]
    jobs,results,cancelled=metrics.terminal_records(records,data['cancelled_records'])
    assert set(jobs)=={'p0','p1','a0'} and set(results)=={'p1','a0'} and set(cancelled)=={'p0'}
    assert 'p0' not in results


def test_complete_and_cancelled_record_overlap_fails_closed():
    data=fixture();record=dict(job=data['jobs']['p0'],result=full_result(data['jobs']['p0'],106.0))
    with pytest.raises(AssertionError,match='terminal overlap'):
        metrics.terminal_records([record],data['cancelled_records'])


def test_cancelled_manifest_keeps_all_physical_work_and_actual_input_records():
    data=fixture();batch=data['accounting'][0]
    message=data['cancelled_records'][0]['cancellation']['message']
    context,model=input_evidence(data['jobs']['p0'])
    batch['cancelled_row_inputs']={'p0':dict(execution_context_audit=context,model_input_audit=model)}
    assert metrics.audit_batch_terminals(batch,data['jobs'],data['results'],{'p0':message},{})==(1,1)
    batch['phases'][0]['executed_job_ids']=['p1']
    with pytest.raises(AssertionError,match='hidden from billing'):
        metrics.audit_batch_terminals(batch,data['jobs'],data['results'],{'p0':message},{})


def test_missing_actual_cancelled_input_evidence_is_not_waived():
    data=fixture();batch=data['accounting'][0];batch['cancelled_row_inputs']={}
    message=data['cancelled_records'][0]['cancellation']['message']
    with pytest.raises(AssertionError,match='actual model input evidence missing'):
        metrics.audit_batch_terminals(batch,data['jobs'],data['results'],{'p0':message},{})


def test_old_clean_input_and_no_cancelled_records_retain_strict_behavior():
    data=fixture();job=data['jobs']['p1'];context,model=input_evidence(job)
    assert metrics.audit_execution_input(job,context,model,{}) is False
    context['executed_prompt_tokens']=[999]
    with pytest.raises(AssertionError):metrics.audit_execution_input(job,context,model,{})
    assert metrics.terminal_records([],[])==({},{},{})


def test_exact_frozen_input_fixture_preserves_raw_and_declared_parent_fields_separately():
    job,context,model,cfg,result=fault_fixture()
    assert metrics.audit_execution_input(job,context,model,cfg,result) is True
    assert result['F2_raw_execution_state_tokens']!=result['state_tokens']
    # A cancelled row has input evidence only; no output is synthesized.
    assert metrics.audit_execution_input(job,context,model,cfg) is True


@pytest.mark.parametrize('field,value',[('source_id','different-source'),('chunk_id',3),('donor_index',1)])
def test_fault_target_cannot_change_source_chunk_or_donor(field,value):
    job,context,model,cfg,result=fault_fixture()
    cfg['retirement_fault_fixture']['targets']['0:5'][field]=value
    with pytest.raises(AssertionError,match='target changed'):
        metrics.audit_execution_input(job,context,model,cfg,result)


def test_unplanned_or_undeclared_fault_override_fails_closed():
    job,context,model,cfg,result=fault_fixture()
    with pytest.raises(AssertionError,match='undeclared execution-context'):
        metrics.audit_execution_input(job,context,model,{},result)
    job['end_window']=6
    with pytest.raises(AssertionError,match='unplanned F2 target'):
        metrics.audit_execution_input(job,context,model,cfg,result)


def test_fault_context_must_match_actual_frozen_donor_not_only_declared_prompt():
    job,context,model,cfg,result=fault_fixture();context['executed_prompt_tokens']=[99]
    with pytest.raises(AssertionError,match='consumed prompt'):
        metrics.audit_execution_input(job,context,model,cfg,result)
    job,context,model,cfg,result=fault_fixture();context['fault_override']=False
    with pytest.raises(AssertionError,match='consumed prompt'):
        metrics.audit_execution_input(job,context,model,cfg,result)


def test_fault_does_not_relax_audio_model_input_or_D1_render_binding():
    job,context,model,cfg,result=fault_fixture();model['waveform_sha256']='different audio'
    with pytest.raises(AssertionError):metrics.audit_execution_input(job,context,model,cfg,result)
    job,context,model,cfg,result=fault_fixture();result['text_binding']['render_inputs']['prompt_tokens']=[99]
    with pytest.raises(AssertionError):metrics.audit_execution_input(job,context,model,cfg,result)
    job,context,model,cfg,result=fault_fixture();result.pop('F2_raw_execution_text')
    with pytest.raises(KeyError):metrics.audit_execution_input(job,context,model,cfg,result)


def test_fault_fixture_cannot_change_authority_or_hide_an_early_chunk():
    job,context,model,cfg,result=fault_fixture();job['role']='authority'
    with pytest.raises(AssertionError,match='Authority'):
        metrics.audit_execution_input(job,context,model,cfg,result)
    job,context,model,cfg,result=fault_fixture();job['chunk_id']=1
    with pytest.raises(AssertionError,match='feedback consumption'):
        metrics.audit_execution_input(job,context,model,cfg,result)
