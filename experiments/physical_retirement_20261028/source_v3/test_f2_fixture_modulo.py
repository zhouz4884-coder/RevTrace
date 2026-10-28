"""Regression for frozen logical IDs 12/14 over the actual 12-donor bank.

The v1 hook and fixture explicitly cycle with modulo. No GPU output or input
record is changed by this independent-audit correction.
"""
import copy

import pytest

import x_service_metrics as metrics
from test_retirement_metrics import fault_fixture


def modulo_fixture(logical_index):
    job,context,model,cfg,result=fault_fixture()
    frozen=cfg['retirement_fault_fixture']
    frozen['donors']=[dict(id='donor-'+str(i),tokens=[20+i,21+i,22+i,23+i,24+i,25+i]) for i in range(12)]
    frozen['fault_plan']['0:5']=logical_index
    frozen['targets']['0:5']['donor_index']=logical_index
    actual=frozen['donors'][logical_index%12]['tokens']
    job['fault_actual_prompt_tokens']=copy.deepcopy(actual)
    context['executed_prompt_tokens']=copy.deepcopy(actual)
    context['executed_prompt_digest']=metrics.tokens(actual)
    return job,context,model,cfg,result


@pytest.mark.parametrize('logical_index,actual_index',[(0,0),(10,10),(12,0),(14,2),(26,2)])
def test_logical_plan_identity_and_physical_donor_are_kept_distinct(logical_index,actual_index):
    job,context,model,cfg,result=modulo_fixture(logical_index)
    frozen=cfg['retirement_fault_fixture']
    raw,donor=metrics.frozen_fault_donor(frozen,'0:5')
    assert raw==logical_index and donor['id']=='donor-'+str(actual_index)
    assert frozen['targets']['0:5']['donor_index']==logical_index
    assert metrics.audit_execution_input(job,context,model,cfg,result) is True
    assert metrics.audit_execution_input(job,context,model,cfg) is True


def test_modulo_does_not_relax_actual_consumed_donor_check():
    job,context,model,cfg,result=modulo_fixture(14)
    wrong=cfg['retirement_fault_fixture']['donors'][3]['tokens']
    context['executed_prompt_tokens']=copy.deepcopy(wrong)
    context['executed_prompt_digest']=metrics.tokens(wrong)
    with pytest.raises(AssertionError,match='consumed prompt'):
        metrics.audit_execution_input(job,context,model,cfg,result)


def test_target_must_keep_raw_logical_index_even_when_modulo_donor_is_same():
    job,context,model,cfg,result=modulo_fixture(14)
    cfg['retirement_fault_fixture']['targets']['0:5']['donor_index']=2
    with pytest.raises(AssertionError,match='target changed'):
        metrics.audit_execution_input(job,context,model,cfg,result)


@pytest.mark.parametrize('index',[-1,'14',14.,True])
def test_modulo_fix_does_not_accept_changed_plan_types_or_negative_indices(index):
    job,context,model,cfg,result=modulo_fixture(14)
    cfg['retirement_fault_fixture']['fault_plan']['0:5']=index
    with pytest.raises(AssertionError,match='logical donor index'):
        metrics.audit_execution_input(job,context,model,cfg,result)


def test_empty_frozen_donor_bank_is_invalid():
    job,context,model,cfg,result=modulo_fixture(14)
    cfg['retirement_fault_fixture']['donors']=[]
    with pytest.raises(AssertionError,match='donor bank'):
        metrics.audit_execution_input(job,context,model,cfg,result)
