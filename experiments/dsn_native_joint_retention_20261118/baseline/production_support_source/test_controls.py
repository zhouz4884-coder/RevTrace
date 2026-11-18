"""Development CPU counterexamples; no Torch/CUDA/model launch."""
import copy,hashlib,json,os,pathlib,struct,subprocess,tempfile,unittest
from unittest.mock import patch
from common import GateError,canonical,put,read,sha,verify_checkout,mapped_state,verified_facts,OLD,FINAL
from endpoints import recount,smoke_decision
from resident_analysis import audit_request_clocks
from run_resident_campaign import resident_smoke
from external_power import energy
SCRATCH=pathlib.Path(os.environ.get('REVTRACE_CPU_SCRATCH',str(pathlib.Path(__file__).parent/'.cpu_scratch')));SCRATCH.mkdir(parents=True,exist_ok=True)

class ClockControls(unittest.TestCase):
    def setUp(self):
        self.sources={'A':dict(source_id='A',frames=9000,audio_sha256='a'),'B':dict(source_id='B',frames=8000,audio_sha256='b')};self.origins={'A':100.,'B':110.};self.config={'settings':{'sources':list(self.sources.values())},'request_order':['A','B']}
        self.rows=[dict(source_id='A',observed=101.,visible_frontier=9000,certified_frontier=9000),dict(source_id='B',observed=111.,visible_frontier=8000,certified_frontier=8000)]
        self.ledger=[dict(kind='request_admitted',source_id='A',request_index=0,observed=100.,request_origin_perf=100.,previous_source_id=None,previous_complete_perf=None),dict(kind='request_complete',source_id='A',observed=101.,EOS_frontier=9000,certified_frontier=9000,consumer_observed_perf=101.),dict(kind='request_admitted',source_id='B',request_index=1,observed=110.,request_origin_perf=110.,previous_source_id='A',previous_complete_perf=101.),dict(kind='request_complete',source_id='B',observed=111.,EOS_frontier=8000,certified_frontier=8000,consumer_observed_perf=111.)]
        self.ingress=[dict(source_id=sid,frontier=f,original_offer=self.origins[sid]+f/16000,observed=self.origins[sid]+f/16000+.001,audio_sha256=s['audio_sha256']) for sid,s in self.sources.items() for f in list(range(8000,s['frames'],8000))+[s['frames']]]
    def test_request_offset_does_not_become_service_wait(self):
        result=recount(self.rows,self.sources,self.origins);self.assertEqual(result['offered_frontiers'],3);self.assertTrue(result['original_quantile_test_pass']);self.assertLess(result['primary_linear_all_offered_D99'],1.)
        wrong=recount(self.rows,self.sources,{'A':100.,'B':100.});self.assertFalse(wrong['original_quantile_test_pass'])
    def test_short_EOS_is_in_original_denominator(self):
        result=recount(self.rows,self.sources,self.origins);self.assertEqual(sum(r['is_EOS'] for r in result['frontiers']),2);self.assertAlmostEqual(result['offered_audio_seconds'],17000/16000)
    def test_valid_ledger_has_real_consumer_EOS(self):self.assertEqual(audit_request_clocks(self.config,self.origins,self.ledger,self.ingress,self.rows)['accepted_frontiers_checked'],3)
    def test_next_request_cannot_be_released_before_consumer_EOS(self):
        bad=copy.deepcopy(self.ledger);bad[2]['previous_complete_perf']=100.9
        with self.assertRaises(GateError):audit_request_clocks(self.config,self.origins,bad,self.ingress,self.rows)
    def test_offset_hindsight_rewrite_is_rejected(self):
        bad=copy.deepcopy(self.ingress);bad[-1]['original_offer']+=.25
        with self.assertRaises(GateError):audit_request_clocks(self.config,self.origins,self.ledger,bad,self.rows)
    def test_missing_EOS_is_not_silently_dropped(self):
        with self.assertRaises(GateError):audit_request_clocks(self.config,self.origins,self.ledger,self.ingress[:-1],self.rows)
    def test_other_source_consumer_cannot_release_next(self):
        bad=copy.deepcopy(self.rows);bad[0]['source_id']='B'
        with self.assertRaises(GateError):audit_request_clocks(self.config,self.origins,self.ledger,self.ingress,bad)

def metric(d,credit,passed=True):return dict(primary_linear_all_offered_D99=d,primary_linear_all_offered_C99=d+.2,dual_deadline_audio_credit_seconds=credit,complete_coverage_and_original_quantile_pass=passed)
def smoke_rows():
    return [dict(version=v,strategy=s,repeat=r,semantic={'status':'PASS_COMPLETE_SELECTED_TRACE_REFERENCE'},primary=metric(1.5 if s=='fullcall' else 4.,8. if s=='fullcall' else 4.,s=='fullcall')) for r in (0,1) for v in ('bdfa','final') for s in ('conservative','fullcall')]
class DecisionControls(unittest.TestCase):
    def test_single_EOS_or_repeat_jitter_does_not_become_causal_bug(self):
        rows=smoke_rows();next(r for r in rows if r['version']=='final' and r['strategy']=='fullcall' and r['repeat']==1)['primary']=metric(2.01,7.9,False)
        result=smoke_decision(rows);self.assertEqual(result['status'],'CONTINUE_REMAINING_24_FROZEN_CELLS');self.assertFalse(result['causal_code_defect_established'])
    def test_repeated_matched_gate_regression_requires_diagnosis(self):
        rows=smoke_rows()
        for r in rows:
            if r['version']=='final' and r['strategy']=='fullcall':r['primary']=metric(2.1,7.5,False)
        self.assertEqual(smoke_decision(rows)['status'],'HOLD_REPEATED_PAIRED_TIMING_REGRESSION_REQUIRES_DIAGNOSIS')
    def test_smoke_is_not_four_speaker_completion(self):
        with self.assertRaises(GateError):smoke_decision(smoke_rows()[:4])
    def test_resident_no_go_keeps_bad_request(self):
        full=dict(primary=metric(1.4,31.),per_request=[{'primary':metric(1.4,8.)} for _ in range(4)]);control=dict(primary=metric(4.,16.),per_request=[])
        full['per_request'][2]['primary']=metric(2.01,7.9,False)
        result=resident_smoke([dict(arm='fullcall',summary=full),dict(arm='conservative',summary=control)]);self.assertTrue(result['status'].startswith('NO_GO'))

class IntegrityControls(unittest.TestCase):
    def test_only_known_source_marker_is_mapped(self):
        state={'contract':{'stage_execution':{'source_commit':FINAL}},'tokens':[1]};changed=mapped_state(state,FINAL);self.assertEqual(changed['tokens'],[1]);self.assertEqual(changed['contract']['stage_execution']['source_commit'],OLD)
        state['contract']['stage_execution']['source_commit']='0'*40
        with self.assertRaises(GateError):mapped_state(state,FINAL)
    def test_fact_torn_tail_does_not_pass_complete_audit(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            path=pathlib.Path(folder)/'facts';obj={'kind':'genesis','sequence':1,'previous':'0'*64,'body':{}};payload=canonical(obj);raw=b'RVN1'+struct.pack('>I',len(payload))+payload+hashlib.sha256(payload).digest();path.write_bytes(raw)
            self.assertEqual(len(list(verified_facts(path))),1);path.write_bytes(raw[:-1])
            with self.assertRaises(GateError):list(verified_facts(path))
    def test_complete_manifest_rejects_untracked_and_wrong_bytes(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            root=pathlib.Path(folder)/'source';root.mkdir();subprocess.run(['git','init','-q',str(root)],check=True)
            for key,value in [('user.name','CPU Control'),('user.email','cpu@example.invalid'),('core.autocrlf','false')]:subprocess.run(['git','-C',str(root),'config',key,value],check=True)
            (root/'x.py').write_bytes(b'x=1\n');subprocess.run(['git','-C',str(root),'add','x.py'],check=True);subprocess.run(['git','-C',str(root),'commit','-qm','Synthetic CPU identity control'],check=True);commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip();manifest=pathlib.Path(folder)/'manifest.json';put(manifest,dict(source_commit=commit,code_commit=commit,files=[dict(path='x.py',bytes=4,sha256=sha(root/'x.py'))]));self.assertTrue(verify_checkout(root,manifest)['clean']);(root/'new.py').write_bytes(b'x=2\n')
            with self.assertRaises(GateError):verify_checkout(root,manifest)
    def test_energy_has_shared_explicit_boundaries(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            path=pathlib.Path(folder)/'power';path.write_text('\n'.join(json.dumps(dict(time=t,boards={'0':{'watts':10},'1':{'watts':20}})) for t in (0.,1.,2.))+'\n',encoding='utf8');self.assertEqual(energy(path,.5,1.5)['total_joules'],30.)
            with self.assertRaises(GateError):energy(path,-1.,1.)

if __name__=='__main__':unittest.main(verbosity=2)
