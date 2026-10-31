"""Launch-stopping counterexamples and deterministic four-cell plan controls."""
import copy,os,pathlib,tempfile,unittest
from unittest.mock import patch
from common import put,sha,read,GateError,B
from interference_prerequisites import validate_prior_scopes,useful_resident_scope
from build_interference_plan import build,remote_disk_path,RULE
from interference_contract import ORDER,CLIENTS
from test_interference_identity import SCRATCH

class PrerequisiteControls(unittest.TestCase):
    def make(self,folder):
        prior={};items={}
        def save(key,value):
            path=folder/(key+'.json');put(path,value);item=dict(path=str(path),sha256=sha(path));items[key]=value;return item
        prior['paired32_summary']=save('paired',dict(status='COMPLETE_PAIRED32_ACTUAL_SERVICE_AND_REFERENCE_AUDIT',completed_cells=32,planned_cells=32))
        evidence=pathlib.Path(os.environ.get('REVTRACE_STRENGTHENING_EVIDENCE',str(pathlib.Path(__file__).resolve().parent.parent)))
        resident_path=evidence/'RESIDENT4_V2_RESULTS'/'SUMMARY.json'
        if not resident_path.exists():resident_path=pathlib.Path(B)/'results/revtrace/dsn_strengthening_20261031/resident4_v2/SUMMARY.json'
        prior['resident4_summary']=save('resident',read(resident_path))
        prior['buffer4_reaudit']={'schema_test_only':'real wrapper negatives are in test_buffer_reaudit_prerequisite'}
        return prior,items
    def test_all_prior_real_scopes_required(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder,patch('interference_prerequisites.disk_path',side_effect=pathlib.Path),patch('interference_prerequisites.validate_buffer_reaudit',return_value={'status':'PASS_REAL_SCHEMA_TESTED_SEPARATELY'}):
            prior,_=self.make(pathlib.Path(folder));self.assertTrue(validate_prior_scopes(prior)['status'].startswith('PASS_EXISTING'))
    def test_changed_receipt_or_partial_queue_rejected(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder,patch('interference_prerequisites.disk_path',side_effect=pathlib.Path):
            prior,_=self.make(pathlib.Path(folder));prior['paired32_summary']['sha256']='0'*64
            with self.assertRaises(GateError):validate_prior_scopes(prior)
    def test_resident_reference_failure_blocks_despite_useful_credit(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder,patch('interference_prerequisites.disk_path',side_effect=pathlib.Path):
            prior,items=self.make(pathlib.Path(folder));items['resident']['cells'][1]['summary']['integrity']['original_reference']['status']='FAIL_COMPLETE_SELECTED_TRACE_REFERENCE';path=pathlib.Path(prior['resident4_summary']['path']);put(path,items['resident'],replace=True);prior['resident4_summary']['sha256']=sha(path)
            with self.assertRaises(GateError):validate_prior_scopes(prior)
    def test_actual_7_of_8_is_retained_and_not_relabelled_8_of_8(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            prior,items=self.make(pathlib.Path(folder));gate=useful_resident_scope(items['resident']);self.assertEqual(sum(r['Fullcall_original_request_gate_passes'] for r in gate['per_repeat']),7);self.assertTrue(gate['actual_misses_retained'])
    def test_complete_resident_without_real_service_opportunity_blocks(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            prior,items=self.make(pathlib.Path(folder));resident=items['resident'];controls={r['repeat']:r for r in resident['cells'] if r['arm']=='conservative'}
            for result in resident['cells']:
                if result['arm']=='fullcall':result['summary']['primary']=copy.deepcopy(controls[result['repeat']]['summary']['primary'])
            with self.assertRaises(GateError):useful_resident_scope(resident)
    def test_legacy_four_top_level_gates_cannot_replace_wrapper(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder,patch('interference_prerequisites.disk_path',side_effect=pathlib.Path):
            prior,_=self.make(pathlib.Path(folder));prior.pop('buffer4_reaudit');prior['buffer4_gates']=[{'status':'PASS_CONTROLLED_REAL_NN_BUFFER_POST_PRODUCER_DEATH_MATCH'}]*4
            with self.assertRaises(GateError):validate_prior_scopes(prior)
    def test_remote_path_cannot_escape_B(self):
        self.assertEqual(remote_disk_path(B+'/results/x'),B+'/results/x')
        for path in ('D:/wrong','/tmp/raw',B+'/../wrong'):
            with self.assertRaises(GateError):remote_disk_path(path)

class ProspectivePlanControls(unittest.TestCase):
    def test_all_four_cells_phase_partition_and_root_rule_frozen(self):
        parent=pathlib.Path(os.environ.get('REVTRACE_RESIDENT_PLAN',str(pathlib.Path(__file__).resolve().parent.parent/'paired_resident_inputs_v2'/'RESIDENT4_v2_FROZEN.json')))
        self.assertTrue(parent.exists(),'set REVTRACE_RESIDENT_PLAN to current resident plan with its sibling config directory')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            folder=pathlib.Path(folder);manifest=folder/'source.json';put(manifest,{'synthetic_CPU_source_identity_only':True})
            with patch('build_interference_plan.verify_checkout',return_value={'source_commit':'1'*40}):
                plan=build(parent,manifest,folder/'inputs',B+'/projects/interference_source_v1',B+'/projects/INTERFERENCE_SOURCE_v1.json',B+'/projects/interference_inputs_v1',B+'/results/interference_v1')
            self.assertEqual([(r['arm'],r['repeat']) for r in plan['cells']],[('conservative',0),('fullcall',0),('fullcall',1),('conservative',1)])
            self.assertEqual(plan['opportunity_rule'],RULE);self.assertFalse(RULE['shared_credit_gain_required'])
            for path in (folder/'inputs'/'interference_opportunity_v1_configs').glob('*.json'):
                cfg=read(path);self.assertEqual([r['source_id'] for r in cfg['settings']['sources']],list(ORDER));self.assertEqual(cfg['clients'],CLIENTS);self.assertEqual(cfg['client_first_offsets'],{'A':0.,'B':2.});self.assertEqual(cfg['maximum_owner_restarts'],0);self.assertEqual(cfg['settings']['source_commit'],'4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47')

if __name__=='__main__':unittest.main(verbosity=2)
