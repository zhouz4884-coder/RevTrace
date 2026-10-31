"""Use actual downloaded b867 wrappers for positive and hostile-schema controls.

The local mirror is bounded and contains no complete raw tree. These tests check
the real wrapper/task/config schema, not a new NN run or a remote raw-byte audit.
Runtime validate_buffer_reaudit additionally rehashes both complete original
raw/watchdog trees on B; its changed-file refusal has a tiny synthetic control.
"""
import copy,os,pathlib,tempfile,unittest
from unittest.mock import patch
from common import read,put,sha,GateError,B
import buffer_reaudit_prerequisite as audit
from test_interference_identity import SCRATCH

def real_documents():
    root=pathlib.Path(os.environ.get('REVTRACE_STRENGTHENING_EVIDENCE',str(pathlib.Path(__file__).resolve().parent.parent)))
    mirrored=(root/'FINAL_CPU_AND_POSTHOC_RESULTS'/'posthoc_v2').is_dir()
    if mirrored:
        cfg=read(root/'buffer_fixture_reaudit_inputs_v2'/'BUFFER4_POSTHOC_REAUDIT_v2_FROZEN.json');index=read(root/'buffer_fixture_reaudit_inputs_v2'/'INPUT_INDEX_v2.json');posthoc=root/'FINAL_CPU_AND_POSTHOC_RESULTS'/'posthoc_v2';plan=read(root/'buffer_fixture_inputs_v1'/'BUFFER4_v1_FROZEN.json');oldroot=root/'BUFFER4_V1_RESULTS';cpu=read(root/'FINAL_CPU_AND_POSTHOC_RESULTS'/'reader_cpu31_v2'/'GATE.json')
    else:
        project=pathlib.Path(B)/'projects/revtrace_dsn_strengthening_20261031';cfg=read(project/'BUFFER4_POSTHOC_REAUDIT_v2_FROZEN.json');index=read(project/'INPUT_INDEX_v2.json');posthoc=pathlib.Path(cfg['raw_result_location']);plan=read(cfg['original_execution_plan']);oldroot=pathlib.Path(plan['raw_result_location']);cpu=read(oldroot.parent/'reader_linux_cpu_v2'/'GATE.json')
    doc=dict(config=cfg,input_index=index,cpu_gate=cpu,gate=read(posthoc/'GATE.json'),summary=read(posthoc/'SUMMARY.json'),run_record=read(posthoc/'RUN_RECORD.json'),execution_plan=plan,original_compound_gate=read(oldroot/'GATE.json'),original_compound_summary=read(oldroot/'SUMMARY.json'),cases=[])
    for cell in plan['cells']:
        cid=cell['cell_id'];execution=read(root/'buffer_fixture_inputs_v1'/'buffer4_v1_configs'/(cid+'.json')) if mirrored else read(cell['config']);doc['cases'].append(dict(row=read(posthoc/(cid+'_REAUDIT.json')),before=read(posthoc/(cid+'_RAW_BEFORE.json')),after=read(posthoc/(cid+'_RAW_AFTER.json')),execution_config=execution,resident_summary=read(oldroot/'cells'/cid/'SUMMARY.json')))
    return doc

def sync(doc,index=0):
    row=doc['cases'][index]['row'];doc['summary']['cases']=[copy.deepcopy(row) if r['cell_id']==row['cell_id'] else r for r in doc['summary']['cases']]

class ActualB867WrapperControls(unittest.TestCase):
    def setUp(self):self.doc=real_documents()
    def rejects(self,pattern=None):
        with self.assertRaisesRegex(GateError,pattern or '.'):
            audit.audit_schema(self.doc)
    def test_actual_four_wrappers_pass_while_old_execution_remains_FAIL(self):
        result=audit.audit_schema(self.doc);self.assertTrue(result['original_execution_failures_retained']);self.assertEqual(result['original_execution_status'],'NO_GO_COMPLETE_BUFFER4_NEGATIVES_PRESERVED');self.assertEqual(result['new_neural_calls'],0)
    def test_wrapper_PASS_cannot_hide_nested_mechanism_FAIL(self):
        self.doc['cases'][0]['row']['mechanism']['status']='FAIL_ACTUAL_PROTOCOL';sync(self.doc);self.rejects('nested actual NN mechanism')
    def test_wrapper_PASS_cannot_hide_original_task_reference_FAIL(self):
        self.doc['cases'][0]['resident_summary']['integrity']['original_reference']['status']='FAIL_COMPLETE_SELECTED_TRACE_REFERENCE';self.rejects('original task/reference failed')
    def test_wrapper_PASS_cannot_hide_missing_original_obligation(self):
        self.doc['cases'][0]['resident_summary']['integrity']['all_original_obligations_eventually_processed']=False;self.rejects('original task/reference failed')
    def test_original_reader_failure_cannot_be_relabelled_PASS(self):
        self.doc['cases'][0]['row']['original_execution_gates']['buffer']['body']['status']='PASS_CONTROLLED_REAL_NN_BUFFER_POST_PRODUCER_DEATH_MATCH';sync(self.doc);self.rejects('known receipt-reader failure')
    def test_other_failure_cause_is_not_whitelisted_by_wrapper(self):
        self.doc['cases'][0]['row']['original_execution_gates']['buffer']['body']['failure']='actual state/C/U mismatch';sync(self.doc);self.rejects('known receipt-reader failure')
    def test_old_compound_FAIL_and_CLI_exit_must_stay_failed(self):
        self.doc['original_compound_gate']['status']='PASS_COMPLETE';self.rejects('old compound execution FAIL')
    def test_original_watchdog_timeout_is_not_a_reader_only_failure(self):
        self.doc['cases'][0]['row']['original_execution_gates']['watchdog']['body']['timed_out']=True;sync(self.doc);self.rejects('CLI/watchdog failure')
    def test_uncertain_original_CUDA_release_blocks(self):
        self.doc['cases'][0]['row']['original_execution_gates']['watchdog']['body']['cleanup']['releases'][0]['all_CUDA_owners_released']=False;sync(self.doc);self.rejects('physical cleanup unresolved')
    def test_negative_old_UID_install_cannot_be_hidden(self):
        index=next(i for i,r in enumerate(self.doc['cases']) if r['row']['mechanism']['actual_parent_full_input_matches'] is False)
        self.doc['cases'][index]['row']['mechanism']['result']['old_uid_post_fence_canonical_install']=1;sync(self.doc,index);self.rejects('install/consume contradicts')
    def test_nested_physical_fence_failure_cannot_be_hidden(self):
        self.doc['cases'][0]['row']['mechanism']['physical_fence']['cuda_release_perf']=0.;sync(self.doc);self.rejects('physical UID/incarnation/fence')
    def test_nested_mechanism_cannot_use_other_execution_dependencies(self):
        self.doc['cases'][0]['row']['mechanism']['fixture_identity'][0]['source_commit']='0'*40;sync(self.doc);self.rejects('original execution dependencies')
    def test_match_expectation_and_case_partition_are_immutable(self):
        self.doc['cases'][0]['row']['mechanism']['actual_parent_full_input_matches']=False;sync(self.doc);self.rejects('nested actual NN mechanism')
    def test_missing_or_duplicate_wrapper_rejected(self):
        self.doc['cases'][-1]=copy.deepcopy(self.doc['cases'][0]);self.rejects('case partition')
    def test_wrong_analysis_source_or_formal31_skip_blocks(self):
        self.doc['cpu_gate']['skipped']=1;self.rejects('formal31')
    def test_wrong_input_index_config_hash_blocks(self):
        self.doc['input_index']['config']['sha256']='0'*64;self.rejects('input-index frozen config hash')
    def test_raw_before_after_change_blocks_despite_boolean_true(self):
        self.doc['cases'][0]['after']['raw'][0]['sha256']='0'*64;self.rejects('before-after differs')
    def test_mechanism_input_hash_must_be_in_complete_raw_index(self):
        self.doc['cases'][0]['row']['mechanism']['inputs'][0]['sha256']='0'*64;sync(self.doc);self.rejects('mechanism raw hash')
    def test_actual_gate_body_hash_must_be_in_unchanged_tree(self):
        self.doc['cases'][0]['row']['original_execution_gates']['buffer']['sha256']='0'*64;sync(self.doc);self.rejects('original gate hash')
    def test_old_top_level_NN_PASS_is_not_a_new_wrapper(self):
        self.doc['cases'][0]['row']['status']=self.doc['cases'][0]['row']['mechanism']['status'];sync(self.doc);self.rejects('wrapper failed')

class CurrentRawBindingControls(unittest.TestCase):
    def test_added_or_changed_current_file_fails_complete_tree_check(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder,patch.object(audit,'disk_path',side_effect=pathlib.Path):
            root=pathlib.Path(folder);path=root/'fact';path.write_bytes(b'original');rows=[dict(path='fact',bytes=path.stat().st_size,sha256=sha(path))];audit.verify_tree(root,rows);path.write_bytes(b'changed')
            with self.assertRaises(GateError):audit.verify_tree(root,rows)
            path.write_bytes(b'original');(root/'extra').write_bytes(b'new')
            with self.assertRaises(GateError):audit.verify_tree(root,rows)
    def test_hashed_wrapper_receipt_cannot_echo_a_wrong_digest(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder,patch.object(audit,'disk_path',side_effect=pathlib.Path):
            path=pathlib.Path(folder)/'wrapper';put(path,{'status':'PASS_ZERO_NN_POSTHOC_MECHANISM_REAUDIT'});item=dict(path=str(path),sha256=sha(path));audit.receipt(item);item['sha256']='0'*64
            with self.assertRaises(GateError):audit.receipt(item)

if __name__=='__main__':unittest.main(verbosity=2)
