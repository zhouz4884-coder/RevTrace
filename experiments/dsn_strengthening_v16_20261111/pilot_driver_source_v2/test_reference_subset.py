"""Prespecified source-scope derivation controls; no neural inference."""
import copy,json,pathlib,tempfile,unittest
from confirmation_common import RUNTIME,REFERENCE_SUCCESS,BOUND_REFERENCE_SUCCESS,sha,reference_binding,GateError
from bind_reference_subset import derive_subset
from test_reference_controls import source,receipt

class SubsetControls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=pathlib.Path(self.tmp.name);self.gen='d'*40
        self.bank_sources=[source('s'+str(i),'p'+str(i),96000) for i in range(8)]
        self.bank=self.p/'bank.json';self.write(self.bank,receipt(self.bank_sources))
        bank=dict(path=str(self.bank),sha256=sha(self.bank))
        self.parent_sel=self.p/'parent_selection.json';ps=receipt(self.bank_sources[:4]);ps.update(selection_use='existing_bank_reference_first_four',parent_bank_receipt=bank);self.write(self.parent_sel,ps)
        self.child_sel=self.p/'child_selection.json';cs=receipt(self.bank_sources[:2]);cs.update(selection_use='existing_bank_pilot_reuse',parent_bank_receipt=bank);self.write(self.child_sel,cs)
        self.details=[];genesis={}
        for s in self.bank_sources[:4]:
            previous=dict(frontier=0,transcript='',contract=dict(source_sha=s['audio_sha256'],stage_execution={'source_commit':RUNTIME}));genesis[s['source_id']]=copy.deepcopy(previous)
            for end in range(8000,96001,8000):
                current=copy.deepcopy(previous);current['frontier']=end;current['transcript']+='x'
                self.details.append(dict(source_id=s['source_id'],end=end,original_full_start_cut=previous,original_full_cut=current,original_full_result=dict(token_ids=[end],selected_correction={}),continuous_original_no_between_step_restore=True));previous=current
        self.dp=self.p/'details.json';self.gp=self.p/'genesis.json';self.gate=self.p/'gate.json';self.parent=self.p/'parent_reference.json'
        self.write(self.dp,self.details);self.write(self.gp,genesis)
        self.write(self.gate,dict(status=REFERENCE_SUCCESS,actual_NN_source_commit=RUNTIME,generator_source_commit=self.gen,all_original_full_state_C_IDs_equal=True,expected_original_steps=48,expected_sources=4,completed_sources=4))
        self.ref=dict(status=REFERENCE_SUCCESS,actual_NN_source_commit=RUNTIME,generator_source_commit=self.gen,reference_origin='measured_continuous_and_restored',selection_receipt={'sha256':sha(self.parent_sel)},sources=self.bank_sources[:4],source_ids=[s['source_id'] for s in self.bank_sources[:4]],speaker_ids=[s['speaker_id'] for s in self.bank_sources[:4]],reference_only=True,actual_serving_runs=0,original_continuous_no_between_step_restore=True,restored_repeats_per_edge=2)
        self.refresh_parent()
    def write(self,p,obj):p.write_text(json.dumps(obj),encoding='utf8')
    def refresh_parent(self):
        for key,path in [('reference_details',self.dp),('genesis',self.gp),('reference_gate',self.gate)]:self.ref[key]=dict(path=str(path),sha256=sha(path))
        self.ref['reference_details']['expected_steps']=48;self.write(self.parent,self.ref)
    def derive(self,name='child'):
        return derive_subset(self.parent,self.parent_sel,self.child_sel,self.p/name,self.gen)
    def check_child(self,name='child'):
        return reference_binding(self.p/name/'REFERENCE_RECEIPT.json',self.child_sel,self.bank_sources[:2],self.gen)
    def test_measured_four_to_prespecified_two_preserves_full_rows_and_cost_origin(self):
        r=self.derive();self.assertEqual(r['status'],BOUND_REFERENCE_SUCCESS);self.assertEqual(r['reference_details']['expected_steps'],24)
        self.assertEqual(json.loads(pathlib.Path(r['reference_details']['path']).read_bytes()),self.details[:24])
        self.assertEqual(r['new_model_calls'],0);self.assertIn('parent_reference_receipt',r['reference_cost_source']);self.check_child()
    def test_other_two_sources_cannot_be_chosen_after_reference(self):
        cs=json.loads(self.child_sel.read_bytes());cs['sources']=self.bank_sources[1:3];self.write(self.child_sel,cs)
        with self.assertRaises(GateError):self.derive()
    def test_child_full_result_or_genesis_cannot_change_despite_fresh_hashes(self):
        self.derive();rp=self.p/'child/REFERENCE_RECEIPT.json';r=json.loads(rp.read_bytes());dp=pathlib.Path(r['reference_details']['path'])
        rows=json.loads(dp.read_bytes());rows[0]['original_full_result']['token_ids']=[999];self.write(dp,rows);r['reference_details']['sha256']=sha(dp);r['reference_details']['bytes']=dp.stat().st_size;self.write(rp,r)
        with self.assertRaisesRegex(GateError,'parent row'):self.check_child()
        # Independent valid local-chain mutation must still fail parent equality.
        self.derive('child2');rp=self.p/'child2/REFERENCE_RECEIPT.json';r=json.loads(rp.read_bytes());dp=pathlib.Path(r['reference_details']['path']);gp=pathlib.Path(r['genesis']['path'])
        rows=json.loads(dp.read_bytes());gen=json.loads(gp.read_bytes());rows[0]['original_full_start_cut']['transcript']='invented';gen['s0']['transcript']='invented';self.write(dp,rows);self.write(gp,gen)
        r['reference_details']['sha256']=sha(dp);r['reference_details']['bytes']=dp.stat().st_size;r['genesis']['sha256']=sha(gp);self.write(rp,r)
        with self.assertRaises(GateError):self.check_child('child2')
    def test_failed_or_old_runtime_parent_cannot_authorize_subset(self):
        gate=json.loads(self.gate.read_bytes());gate['all_original_full_state_C_IDs_equal']=False;self.write(self.gate,gate);self.refresh_parent()
        with self.assertRaises(GateError):self.derive()
        gate['all_original_full_state_C_IDs_equal']=True;self.write(self.gate,gate)
        self.details[0]['original_full_start_cut']['contract']['stage_execution']['source_commit']='14ae77ee2f1f0c324be3f40b89fb6011972c35b9';self.write(self.dp,self.details);self.refresh_parent()
        with self.assertRaisesRegex(GateError,'relabelled'):self.derive()
    def test_parent_selection_and_bank_drift_rejected(self):
        bank=json.loads(self.bank.read_bytes());bank['sources'].reverse();self.write(self.bank,bank)
        with self.assertRaisesRegex(GateError,'bank changed'):self.derive()
    def test_derived_subset_cannot_masquerade_as_new_inference(self):
        self.derive();rp=self.p/'child/REFERENCE_RECEIPT.json';r=json.loads(rp.read_bytes());gp=pathlib.Path(r['reference_gate']['path']);g=json.loads(gp.read_bytes());g['new_neural_verification']=True;self.write(gp,g);r['reference_gate']['sha256']=sha(gp);self.write(rp,r)
        with self.assertRaisesRegex(GateError,'mislabeled'):self.check_child()

if __name__=='__main__':unittest.main()
