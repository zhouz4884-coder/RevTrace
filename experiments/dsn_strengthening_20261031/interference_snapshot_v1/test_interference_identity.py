"""Real original4f coordinator CPU differential and complete trace counterexamples."""
import copy,hashlib,json,os,pathlib,struct,sys,tempfile,unittest
from common import canonical,put,GateError,FINAL,OLD,read,verify_checkout,sha
from interference_contract import ORDER
from interference_observer import attach_observer
from interference_analysis import audit_continuity
from audit_results import selected_trace
from test_interference import config

SCRATCH=pathlib.Path(os.environ.get('REVTRACE_CPU_SCRATCH',str(pathlib.Path(__file__).parent/'.cpu_scratch')));SCRATCH.mkdir(parents=True,exist_ok=True)

def trace(folder):
    cfg=config();roots={sid:dict(frontier=0,transcript='',context={'tokens':[0]},contract=dict(source_sha=sid,stage_execution={'source_commit':FINAL})) for sid in ORDER};facts=[dict(kind='genesis',body={'initials':copy.deepcopy(roots)})];refs=[];consumer=[]
    for sid in ORDER:
        for end in (8000,9000):
            start=copy.deepcopy(roots[sid]);state=copy.deepcopy(start);state.update(frontier=end,transcript=str(end));record=dict(start_state=hashlib.sha256(canonical(start)).hexdigest(),end_state=hashlib.sha256(canonical(state)).hexdigest(),role='authority',candidate_handoff=False,token_ids=[end],selected_correction={'actual':'C'})
            job=dict(source_id=sid,start=start,end=end);facts.append(dict(kind='canonical',body=dict(source_id=sid,parent_state=start,next_state=state,job=job,record=record)))
            oldstart=copy.deepcopy(start);oldstate=copy.deepcopy(state)
            for value in (oldstart,oldstate):value['contract']['stage_execution']['source_commit']=OLD
            refs.append(dict(source_id=sid,end=end,original_full_start_cut=oldstart,original_full_cut=oldstate,original_full_result=dict(token_ids=[end],selected_correction={'actual':'C'})));roots[sid]=state
        consumer.append(dict(source_id=sid,certified_frontier=9000,canonical_sha=hashlib.sha256(canonical(roots[sid])).hexdigest()))
    previous='0'*64
    with (folder/'facts.wal').open('xb') as stream:
        for index,value in enumerate(facts,1):
            value.update(sequence=index,previous=previous);payload=canonical(value);digest=hashlib.sha256(payload).digest();stream.write(b'RVN1'+struct.pack('>I',len(payload))+payload+digest);previous=digest.hex()
    (folder/'consumer.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in consumer),encoding='utf8');return cfg,refs

class CompleteReferenceControls(unittest.TestCase):
    def test_all_four_requests_complete_state_C_and_ID_match(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as name:
            folder=pathlib.Path(name);cfg,refs=trace(folder);self.assertEqual(selected_trace(folder,cfg,refs,FINAL)['checked_steps'],8)
    def test_same_state_but_other_C_or_ID_is_rejected(self):
        for field,value in [('token_ids',[99]),('selected_correction',{'other':'C'})]:
            with tempfile.TemporaryDirectory(dir=SCRATCH) as name:
                folder=pathlib.Path(name);cfg,refs=trace(folder);refs[0]['original_full_result'][field]=value
                with self.assertRaises(GateError):selected_trace(folder,cfg,refs,FINAL)
    def test_entire_input_context_compared_not_just_frontier(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as name:
            folder=pathlib.Path(name);cfg,refs=trace(folder);refs[0]['original_full_start_cut']['context']['tokens']=[9]
            with self.assertRaises(GateError):selected_trace(folder,cfg,refs,FINAL)
    def test_missing_actual_EOS_consumer_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as name:
            folder=pathlib.Path(name);cfg,refs=trace(folder);(folder/'consumer.jsonl').write_text('',encoding='utf8')
            with self.assertRaises(GateError):selected_trace(folder,cfg,refs,FINAL)

class ContinuousPIDControls(unittest.TestCase):
    def fixture(self):
        ready=[dict(worker='full0',pid=10,gpu=0),dict(worker='full1',pid=11,gpu=1)];events=[dict(kind='worker_started',slot=r['worker'],incarnation=0,pid=r['pid']) for r in ready];dispatch=[dict(owner_epoch=0,physical_incarnation=0,physical_slot='full0' if index%2==0 else 'full1',pid=10+index%2,job={'source_id':sid}) for index,sid in enumerate(ORDER)];return config(),ready,events,dispatch
    def test_two_persistent_model_PIDs_cover_every_request(self):self.assertEqual(audit_continuity(*self.fixture())['model_loads'],2)
    def test_new_PID_or_reload_cannot_hide_between_requests(self):
        data=self.fixture();data[3][-1]['pid']=99
        with self.assertRaises(GateError):audit_continuity(*data)
        data=self.fixture();data[2].append(dict(kind='worker_started',slot='full0',incarnation=1,pid=99))
        with self.assertRaises(GateError):audit_continuity(*data)
    def test_an_unexecuted_future_request_does_not_pass(self):
        data=self.fixture();data[3].pop()
        with self.assertRaises(GateError):audit_continuity(*data)

class OriginalCoordinatorDifferential(unittest.TestCase):
    def test_actual_original_policy_state_and_proposals_unchanged(self):
        source=pathlib.Path(os.environ.get('REVTRACE_NN_SOURCE',str(pathlib.Path(__file__).resolve().parents[2]/'dsn_native_resilience_20261030'/'source_v2')))
        self.assertTrue(source.is_dir(),'set REVTRACE_NN_SOURCE to exact original4f checkout for required CPU differential')
        sys.path.insert(0,str(source))
        from test_resilience_policy import cut
        from resilience_policy import ResilientFullSpecCoordinator as Policy
        from resilience_inbound import audit_value
        import numpy as np
        import types
        def exercise(observe):
            root=cut(0);logs=[];policy=Policy(initials={'s':root.state},audio={'s':np.zeros(40000,dtype=np.float32)},runtime_identity={'source':'CPU_control'},source_frames={'s':40000},authority_workers=('f0','f1'),owner_epoch=0,worker_incarnations={'f0':0,'f1':0},before_commit=lambda tx:None)
            restore=attach_observer(Policy,{'s':types.SimpleNamespace(value=24000)},{'s':{'frames':40000}},logs.append) if observe else lambda:None
            try:
                first=policy.next_full_start('s',24000);self.assertTrue(first.same(root));job=policy.register(job_id='e0-j000000001',worker='f0',worker_incarnation=0,kind='full',source_id='s',start=first,end=8000,dispatched_perf=1.)
                predicted=cut(8000,'prediction');projection=dict(kind='typed_ASR_stage_identity_feedback_projection',learned_C_executed=False,original_full_infer_completed=False,token_ids=[8000],end=predicted.state,end_state_sha=predicted.sha256)
                event=dict(kind='asr_early',worker='f0',worker_incarnation=0,job_id=job['job_id'],dispatch_epoch=0,source_id='s',start_state=first.state,start_state_sha=first.sha256,end_frontier=8000,producer_role='authority',produced_perf=2.,projection=projection,candidate_wire=None)
                result=policy.receive_event('f0',0,event,received_perf=2.1);second=policy.next_full_start('s',24000);self.assertTrue(second.same(predicted));policy.register(job_id='e0-j000000002',worker='f1',worker_incarnation=0,kind='full',source_id='s',start=second,end=16000,dispatched_perf=3.)
                snapshot=dict(canonical=policy.canonical('s').state,tail=policy.tail('s').state,jobs=audit_value(policy.jobs),active=dict(policy.active_authority),promotions=copy.deepcopy(list(policy.promotions)),invalidations=policy.invalidations(),epochs=dict(policy.epochs),seen=dict(vars(policy._seen_jobs)),inbound_active=audit_value(policy.inbound.active))
                return snapshot,result,logs
            finally:restore()
        plain=exercise(False);observed=exercise(True);self.assertEqual(plain[:2],observed[:2]);self.assertEqual(len(observed[2]),2);self.assertFalse(plain[2])

if __name__=='__main__':unittest.main(verbosity=2)
