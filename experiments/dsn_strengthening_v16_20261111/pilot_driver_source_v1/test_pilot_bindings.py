"""Frozen CPU plan/reference/accounting integration, never neural results."""
import copy,importlib.metadata,json,pathlib,tempfile,unittest
from confirmation_common import (RUNTIME,PARENT_RUNTIME,MAIN_ARMS,AUXILIARY_ARMS,SEED,GateError,sha,
    abba_blocks,validate_matrix,reference_binding,validate_prelaunch,validate_phase_selection)
from test_reference_controls import source,receipt
from prepare_pilot import choose_existing_sources,new_environment
from run_confirmation import aggregate
from job_accounting import audit_trial

def cells(sources,aux=True):
    result=[]
    for block in abba_blocks(sources,aux)[0]:
        for arm in block['strategies']:
            result.append(dict(cell_id=str(len(result)),source_id=block['source']['source_id'],strategy=arm,repeat=block['repeat'],primary_gpu=block['primary_gpu'],position=len(result)))
    return result

class PilotMatrixControls(unittest.TestCase):
    def test_pilot24_has20_main4_aux_and_exact_six_arm_reverse(self):
        ss=[source('a','p0'),source('b','p1')];cs=cells(ss);validate_matrix(cs,ss,True)
        self.assertEqual(len(cs),24);self.assertEqual(sum(c['strategy'] in MAIN_ARMS for c in cs),20)
        self.assertEqual(sum(c['strategy'] in AUXILIARY_ARMS for c in cs),4)
    def test_new_bank_main_five_only_remains_complete_and_no_aliasing_ties(self):
        ss=[source('a','p0')];cs=cells(ss,False);validate_matrix(cs,ss,False)
        self.assertEqual(len(cs),10);self.assertEqual({c['strategy'] for c in cs},set(MAIN_ARMS))
    def test_missing_main_or_extra_unknown_arm_rejected(self):
        ss=[source('a','p0')];cs=cells(ss);cs[0]['strategy']='UseAll'
        with self.assertRaises(GateError):validate_matrix(cs,ss)
    def test_metadata_choice_cannot_read_outcomes_and_is_reused_bank(self):
        ss=[source('s'+str(i),'p'+str(i)) for i in range(8)];bank=receipt(ss)
        picked=choose_existing_sources(bank);bank['model_outcomes']={'s0':-999,'s7':999};bank['sources'].reverse()
        self.assertEqual(choose_existing_sources(bank),picked);self.assertEqual([s['speaker_id'] for s in picked],['p0','p1'])
    def test_reused_bank_never_becomes_new_independent_confirmation(self):
        ss=[source('a','p0'),source('b','p1')];r=receipt(ss);r['selection_use']='existing_bank_pilot_reuse'
        with self.assertRaises(GateError):validate_phase_selection(r,'new_confirmatory',ss)
    def test_all_lengths_keep500ms_and_original_partial_EOS(self):
        from ref_common import expected_frontiers
        for n in (96000,191999,192000,320000):
            fs=expected_frontiers(n);self.assertEqual(fs[-1],n)
            self.assertTrue(all(b-a==8000 for a,b in zip([0]+fs[:-2],fs[:-1])))
            self.assertLessEqual(fs[-1]-(fs[-2] if len(fs)>1 else 0),8000)
    def test_ties_and_resource_drift_retain_all_main_and_auxiliary_results(self):
        ss=[source('a','p0'),source('b','p1')];rows=[]
        for c in cells(ss):
            rows.append(dict(c,primary=dict(offered_audio_seconds=8.,dual_deadline_audio_credit_seconds=7.,complete_coverage_and_original_quantile_pass=False),common_external_energy={'origin_to_confirmed_physical_model_drain':{'total_joules':100}},resource_observations={'bytes':100+4*c['repeat']}))
        plan=dict(sources=ss,include_auxiliary=True,expected_trials=24,expected_source_count=2,expected_main_trials=20,expected_auxiliary_trials=4,new_independent_speakers=0)
        r=aggregate(rows,plan);self.assertEqual(len(r['main_cells']),20);self.assertEqual(len(r['auxiliary_cells']),4)
        self.assertEqual(r['completed_trials'],24);self.assertTrue(all(d['diagnostic_required'] for d in r['resource_diagnostics']))

class ReferenceBindingControls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=pathlib.Path(self.tmp.name)
        self.sources=[source('a','p',96000)];self.generator='d'*40;self.selection=self.p/'selection.json'
        self.write(self.selection,receipt(self.sources));s=self.sources[0]
        first=dict(frontier=0,transcript='',contract=dict(source_sha=s['audio_sha256'],stage_execution={'source_commit':RUNTIME}));previous=first;self.details=[]
        for end in range(8000,96001,8000):
            current=copy.deepcopy(previous);current['frontier']=end;current['transcript']+='x'
            self.details.append(dict(source_id='a',end=end,original_full_start_cut=previous,original_full_cut=current,original_full_result=dict(token_ids=[end],selected_correction={}),continuous_original_no_between_step_restore=True));previous=current
        self.detail=self.p/'details.json';self.genesis=self.p/'genesis.json';self.gate=self.p/'gate.json';self.ref=self.p/'receipt.json'
        self.write(self.detail,self.details);self.write(self.genesis,{'a':first})
        self.write(self.gate,dict(status='PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES',actual_NN_source_commit=RUNTIME,generator_source_commit=self.generator,all_original_full_state_C_IDs_equal=True,expected_original_steps=12,expected_sources=1,completed_sources=1))
        self.record=dict(status='PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES',actual_NN_source_commit=RUNTIME,generator_source_commit=self.generator,selection_receipt={'sha256':sha(self.selection)},sources=self.sources,source_ids=['a'],speaker_ids=['p'],reference_only=True,actual_serving_runs=0,original_continuous_no_between_step_restore=True,restored_repeats_per_edge=2)
        self.refresh()
    def write(self,path,obj):path.write_text(json.dumps(obj),encoding='utf8')
    def refresh(self):
        for key,path in [('reference_details',self.detail),('genesis',self.genesis),('reference_gate',self.gate)]:self.record[key]=dict(path=str(path),sha256=sha(path))
        self.record['reference_details']['expected_steps']=12;self.write(self.ref,self.record)
    def check(self):return reference_binding(self.ref,self.selection,self.sources,self.generator)
    def test_complete_new_actual_runtime_reference_accepted(self):self.assertEqual(self.check()['actual_NN_source_commit'],RUNTIME)
    def test_old_outer_source_receipt_cannot_be_relabelled(self):
        self.record['actual_NN_source_commit']=PARENT_RUNTIME;self.refresh()
        with self.assertRaises(GateError):self.check()
    def test_outer_new_label_cannot_hide_old_complete_state_markers(self):
        for row in self.details:
            for key in ('original_full_start_cut','original_full_cut'):row[key]['contract']['stage_execution']['source_commit']=PARENT_RUNTIME
        self.write(self.detail,self.details);self.refresh()
        with self.assertRaisesRegex(GateError,'relabelled'):self.check()
    def test_wrong_generator_rejected(self):
        self.record['generator_source_commit']='e'*40;self.refresh()
        with self.assertRaises(GateError):self.check()
    def test_missing_EOS_or_broken_complete_chain_rejected(self):
        self.details[1]['original_full_start_cut']=copy.deepcopy(self.details[1]['original_full_start_cut']);self.details[1]['original_full_start_cut']['transcript']='wrong';self.write(self.detail,self.details);self.refresh()
        with self.assertRaisesRegex(GateError,'chain'):self.check()
    def test_wrong_final_EOS_cannot_preserve_count_and_pass(self):
        self.details[-1]['end']-=1;self.details[-1]['original_full_cut']['frontier']-=1
        self.write(self.detail,self.details);self.refresh()
        with self.assertRaisesRegex(GateError,'EOS'):self.check()
    def test_failed_reference_gate_never_authorizes_service_plan(self):
        gate=json.loads(self.gate.read_bytes());gate['all_original_full_state_C_IDs_equal']=False;self.write(self.gate,gate);self.refresh()
        with self.assertRaises(GateError):self.check()
    def test_prelaunch_requires_current_actual_runtime_and_explicit_driver(self):
        driver=dict(source_commit=self.generator,source_manifest_sha256='1'*64);base=dict(source_commit=RUNTIME,source_manifest_sha256='2'*64)
        rp=self.p/'root.json';dp=self.p/'driver.json';plan=self.p/'plan.json';self.write(plan,{})
        self.write(rp,dict(gate='SOURCE_IDENTITY_PASS',code_commit=RUNTIME,manifest_sha256='2'*64,setup_pointer='CURRENT.json',setup_pointer_sha256='3'*64))
        self.write(dp,dict(gate='SOURCE_IDENTITY_PASS',code_commit=self.generator,manifest_sha256='1'*64))
        pre=dict(plan_sha256=sha(plan),root_noarg_preflight=str(rp),root_noarg_preflight_sha256=sha(rp),driver_explicit_preflight=str(dp),driver_explicit_preflight_sha256=sha(dp),exclusive_GPU_window_authorized_by_root=True)
        validate_prelaunch(pre,plan,driver,base)
        old=json.loads(rp.read_bytes());old['code_commit']=PARENT_RUNTIME;self.write(rp,old);pre['root_noarg_preflight_sha256']=sha(rp)
        with self.assertRaises(GateError):validate_prelaunch(pre,plan,driver,base)
    def test_environment_is_new_metadata_not_relabelled_old_neural_observation(self):
        version=importlib.metadata.version('numpy');old=dict(packages={'numpy':version},worker_packages={'numpy':version},assets_manifest_path='/assets',assets_manifest_sha256='f'*64,asr_parameter_dtypes={'torch.float32':1},corrector_parameter_dtypes={'torch.float32':2})
        oldp=self.p/'oldenv.json';ready=self.p/'ready.json';self.write(oldp,old)
        r=dict(status='PASS_FROZEN_CPU_BYTE_AND_ENVIRONMENT_READINESS',new_model_calls=0,environment={'packages':{'numpy':version}},asset_manifest_sha256='f'*64,source_commit='c'*40);self.write(ready,r)
        env=new_environment(old,str(oldp),r,str(ready),{'source_commit':self.generator},{'source_commit':RUNTIME})
        self.assertEqual(env['actual_NN_source_commit'],RUNTIME);self.assertFalse(env['new_runtime_model_READY_observed'])

class RawAccountingIntegrationControls(unittest.TestCase):
    def check_owner_fixture(self,arm,parent_first):
        from test_resilience_owner_integration import Harness
        from resilience_storage import scan
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d);h=Harness(p,arm=arm,future_first=True,parent_first=parent_first)
            try:
                h.run();(p/'CONFIG.json').write_text(json.dumps(h.config));r=audit_trial(p,scan,closed=True)
                self.assertEqual(r['status'],'PASS_DISJOINT_JOB_ACCOUNTING',r['errors'])
                return r
            finally:h.close()
    def test_actual_owner_UIR_raw_parser_closes_and_keeps_ready_reuse(self):
        r=self.check_owner_fixture('uir',False);self.assertEqual(r['dispatches'],2);self.assertEqual(r['Owner_admitted_ready_reuse'],1)
    def test_actual_owner_ready_only_queued_completion_zero_reuse_still_valid(self):
        r=self.check_owner_fixture('ready_only',True);self.assertEqual(r['dispatches'],3);self.assertEqual(r['counts']['fully_discarded'],1)
        self.assertEqual(r['Owner_admitted_ready_reuse'],0);self.assertTrue(r['status'].startswith('PASS'))

if __name__=='__main__':unittest.main()
