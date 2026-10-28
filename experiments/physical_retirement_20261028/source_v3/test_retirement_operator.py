"""CPU provenance/operator decision controls; no GPU work is performed."""
import copy
import json
from pathlib import Path
import time

import pytest

import retirement_operator as op


def probe():
    jobs=[]
    for i in range(3):
        jobs.append({'job_id':'p'+str(i),'role':'proposal','session_id':i,'parent':2,
          'source_id':'source'+str(i),'language':'English','prompt_tokens':[i,7],
          'chunk_id':2,'audio_start_sample':0,'audio_end_sample':32000,
          'prefix_audio_sha256':'audio'+str(i),'interval_audio_sha256':'interval'+str(i),
          'runtime_digest':'old-runtime','contract_digest':'old-contract',
          'audio_ready_perf':1000.,'enqueue_perf':1001.,'_delivery':{'old':True}})
    jobs[1]['fault_actual_prompt_tokens']=[11]
    return {'probe_id':'cpu-fixture','jobs':jobs,
      'cancel_schedule':[{'job_id':'p1','delay_from_phase_start_seconds':.5,'reason':'trusted-coverage'}],
      'original_proposal_runtime':{'dtype':'float16','microbatch':3,'max_new_tokens':8,
        'code_commit':'a'*40,'software':{'transformers':'test-version'},'render_contract':{'CPU_fixture':True},
        'ces_evidence_choice':True,'allow_execution_context_override':True},
      'model_path':'/fixture/model','manifest_path':'/fixture/manifest'}


def config(q=None):
    return op.build_execution_config(q or probe(),{'source_commit':'b'*40,'manifest_sha256':'new-source'},
      {'transformers':'test-version'},gpu=1)


def row(token=9):
    return {'token_ids':[token],'state_tokens':[1,token],'text':'text'+str(token),
      'terminated_by_eos':True,'hit_token_limit':False,'model_input_audit':{}}


def trial(policy,repeat=0,omit=()):
    complete={j['job_id']:row() for j in probe()['jobs'] if j['job_id'] not in omit}
    return {'trial_id':str(repeat)+'-'+policy,'policy':policy,'repeat':repeat,
      'complete_results':complete,'cancelled_results':{jid:{'CPU_fixture':True} for jid in omit},
      'physical_interval_seconds':10. if policy=='no_cancel' else 3.,
      'model_phase_seconds':9. if policy=='no_cancel' else 2.,
      'both_board_joules':100. if policy=='no_cancel' else 30.}


def test_execution_runtime_reidentifies_new_code_and_does_not_relabel_old_inputs():
    q=probe();original=copy.deepcopy(q);c=config(q)
    assert c['runtime']['code_commit']=='b'*40
    assert c['runtime']['source_manifest_sha256']=='new-source'
    assert 'code_commit' not in c['runtime']['original_numerical_contract']
    assert c['worker']['runtime_digest']==c['runtime_digest']
    assert c['runtime_digest']!='old-runtime' and c['contract_digest']!='old-contract'
    jobs=op.execution_jobs(q,c,20.)
    assert all(j['runtime_digest']==c['runtime_digest'] and j['contract_digest']==c['contract_digest'] for j in jobs)
    assert all(j['audio_ready_perf']==20. and j['enqueue_perf']==20. and '_delivery' not in j for j in jobs)
    assert op.neural_inputs(jobs)==op.neural_inputs(q['jobs'])
    assert [j['job_id'] for j in jobs]==[j['job_id'] for j in q['jobs']]
    assert jobs[1]['fault_actual_prompt_tokens']==[11]
    assert q==original


def test_original_numerical_environment_drift_closes_gate():
    with pytest.raises(ValueError,match='environment drift'):
        op.build_execution_config(probe(),{'source_commit':'b'*40,'manifest_sha256':'x'},
          {'transformers':'other'})


def test_config_keeps_actuator_shared_and_drops_archived_scheduler_policy():
    c=config();assert c['worker']['physical_retirement'] is True
    assert 'ces_evidence_choice' not in c['worker'] and 'verification_policy' not in c['worker']
    assert 'current_prefix_mode' not in c['worker'] and 'online_selection_mode' not in c['worker']
    assert c['contract']['shared_actuator_in_both_arms'] is True
    assert c['worker']['allow_execution_context_override'] is True


@pytest.mark.parametrize('change',[
    {'job_id':'missing'},{'delay_from_phase_start_seconds':-1},
    {'delay_from_phase_start_seconds':float('nan')},
])
def test_invalid_fixed_schedule_rejected(change):
    q=probe();q['cancel_schedule'][0].update(change)
    with pytest.raises(ValueError):op.validate_probe(q)


def test_duplicate_peer_and_authority_rejected():
    q=probe();q['jobs'][1]['job_id']=q['jobs'][0]['job_id']
    with pytest.raises(ValueError):op.validate_probe(q)
    q=probe();q['jobs'][0]['role']='authority'
    with pytest.raises(ValueError):op.validate_probe(q)


def test_terminal_gate_requires_full_legitimate_completion_and_cancel_targets_only():
    q=probe();assert op.terminal_gate(q,'covered',{'p0':{},'p2':{}},{'p1':{}})['all_unscheduled_rows_complete']
    with pytest.raises(ValueError):op.terminal_gate(q,'covered',{'p0':{}},{'p1':{}})
    with pytest.raises(ValueError):op.terminal_gate(q,'covered',{'p0':{},'p1':{}},{'p2':{}})
    with pytest.raises(ValueError):op.terminal_gate(q,'covered',{'p0':{},'p1':{},'p2':{}},{'p1':{}})
    with pytest.raises(ValueError):op.terminal_gate(q,'no_cancel',{'p0':{},'p2':{}},{'p1':{}})


def test_operator_positive_gate_still_does_not_claim_service_value():
    result=op.compare_trials(probe(),[trial('covered',omit=['p1']),trial('no_cancel')])
    assert result['safe_equivalence_gate']
    assert result['gate']=='GO_TO_SERVICE_OPPORTUNITY_CHECK'
    assert result['service_value_proven'] is False
    assert result['paired_operator_effects'][0]['model_phase_saved_seconds']==7.


def test_surviving_output_difference_closes_even_fast_operator_gate():
    target=trial('covered',omit=['p1']);target['complete_results']['p0']=row(8)
    result=op.compare_trials(probe(),[trial('no_cancel'),target])
    assert not result['safe_equivalence_gate']
    assert result['gate']=='NO_GO_OPERATOR_OR_NO_PHYSICAL_OPPORTUNITY'


def test_no_cancel_repeat_disagreement_closes_gate():
    second=trial('no_cancel',repeat=1);second['complete_results']['p0']=row(8)
    result=op.compare_trials(probe(),[trial('no_cancel'),trial('covered',omit=['p1']),second,
      trial('covered',repeat=1,omit=['p1'])])
    assert not result['safe_equivalence_gate']


def test_archived_output_drift_is_recorded_separately_from_paired_output_equivalence():
    q=probe();q['original_row_expectations']=[dict(row(7),job_id='p0')]
    result=op.compare_trials(q,[trial('no_cancel'),trial('covered',omit=['p1'])])
    assert result['safe_equivalence_gate']
    assert result['comparisons'][0]['rows'][0]['archived_output_equal'] is False


def test_archived_processed_tensor_difference_closes_input_frozen_gate():
    q=probe();q['original_row_expectations']=[dict(row(),job_id='p0',model_input_audit={'input_ids':[99]})]
    result=op.compare_trials(q,[trial('no_cancel'),trial('covered',omit=['p1'])])
    assert not result['safe_equivalence_gate']


def test_source_verifier_checks_bytes_and_full_new_commit(tmp_path):
    names=['retirement_operator.py','runtime/scripts/row_delivery_worker.py',
      'runtime/scripts/row_delivery_executor.py','runtime/scripts/tc_live_worker.py',
      'runtime/src/revtrace/row_lifecycle.py','runtime/src/revtrace/row_stream.py']
    files=[]
    for name in names:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text('fixture')
        files.append({'path':name,'sha256':op.file_sha(target)})
    manifest=tmp_path/'MANIFEST.json';manifest.write_text(json.dumps({'source_commit':'b'*40,'files':files}))
    identity=op.verify_source(manifest,'b'*40,tmp_path)
    assert identity['source_commit']=='b'*40 and identity['git_checked_here'] is False
    (tmp_path/names[1]).write_text('changed')
    with pytest.raises(ValueError,match='source byte mismatch'):op.verify_source(manifest,'b'*40,tmp_path)
    with pytest.raises(ValueError,match='full execution source commit'):op.verify_source(manifest,'short',tmp_path)


def test_operator_loop_records_intervention_after_start_and_exclusive_terminals(tmp_path):
    """A fake transport verifies controller sequencing, not model performance."""
    q=probe();q['cancel_schedule'][0]['delay_from_phase_start_seconds']=0.
    class FixtureWorker:
        batch_drained=False
        def submit(self,jobs):self.jobs=jobs;self.steps=0;self.requests=[];self._events=[];self._cancels=[]
        def poll(self):
            self.steps+=1
            if self.steps==1:
                self.start=time.perf_counter()
                self._events=[{'kind':'model-started','started_perf':self.start}]
                return None
            self.batch_drained=True;end=time.perf_counter()
            self._events=[{'kind':'batch-accounting','phases':[{'started_perf':self.start,'completed_perf':end}]}]
            self._cancels=[{'kind':'cancel-applied','job_id':jid,'message':{'CPU_fixture_only':True}} for jid in self.requests]
            return [dict(row(),job_id=j['job_id']) for j in self.jobs if j['job_id'] not in self.requests]
        def drain_telemetry(self):value,self._events=self._events,[];return value
        def drain_cancellations(self):value,self._cancels=self._cancels,[];return value
        def cancel_job(self,jid,reason,requested_perf):
            assert self.steps==1
            self.requests.append(jid)
            return {'kind':'cancel-request','job_id':jid,'reason':reason,'requested_perf':requested_perf,'status':'new-request'}
    class FixturePower:
        def joules(self,start,end):assert end>=start;return 0. # CPU fixture, not sampled energy.
    result=op.run_trial(FixtureWorker(),q,config(q),'covered',0,FixturePower(),tmp_path,2.)
    assert set(result['complete_results'])=={'p0','p2'}
    assert set(result['cancelled_results'])=={'p1'}
    assert len(result['requests'])==1
    assert result['requests'][0]['intervention_is_archival_not_current_owner_proof'] is True
    assert result['terminal_gate']['full_terminal_partition'] is True
    assert (tmp_path/'r0-covered-events.jsonl').is_file()
