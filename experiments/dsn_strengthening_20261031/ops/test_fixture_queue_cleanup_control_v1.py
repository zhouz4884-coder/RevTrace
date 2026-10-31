"""Local synthetic exception controls; no real child, GPU, or remote action."""
import hashlib,importlib.util,json,pathlib,sys,tempfile,types,unittest
from unittest.mock import patch
E=pathlib.Path(__file__).resolve().parents[1];S=E/'paired_resident_source_v2';sys.path.insert(0,str(S));import common,process_cleanup,run_paired_campaign
spec=importlib.util.spec_from_file_location('future_fixture_queue',E/'ops/run_fixture_campaign_v1.py');queue=importlib.util.module_from_spec(spec);spec.loader.exec_module(queue)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
class Child:
    pid=24680;returncode=None
    def wait(self,*args,**kwargs):raise KeyboardInterrupt('synthetic wait interrupt')
    def poll(self):return None
class Controls(unittest.TestCase):
    def exercise(self,cleanup_error=False,first_identity_missing=False):
        scratch=E/'fixture_queue_development_scratch';scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            root=pathlib.Path(folder);project=root/'project';project.mkdir();out=root/'out';env=root/'env';env.write_bytes(b'{}');ref=root/'ref';ref.write_bytes(b'[]');refgate=root/'refgate';refgate.write_bytes(b'{}');receipt=root/'receipt';receipt.write_bytes(b'{}');cfg=root/'cfg';cfg.write_bytes(b'{}');cpu=root/'cpu'
            cpu.write_text(json.dumps(dict(status='PASS_FORMAL_FIXTURE25_LINUX_CPU_ZERO_SKIP',source_commit='fixture',tests=25,skipped=0,errors=0,failures=0,shared_environment_sha256=sha(env))))
            cell=dict(cell_id='CPU_EXCEPTION_CONTROL_ONLY',config=str(cfg),config_sha256=sha(cfg),out=str(root/'cell'),buffer_gate=str(root/'cell/buffer'),position=0,repeat=0,expect_match=True,command=['NO_ACTUAL_COMMAND'])
            plan=dict(source_commit='fixture',actual_NN_source_commit='base',harness_source_commit='harness',dependencies={},raw_result_location=str(out),environment_record=str(env),environment_sha256=sha(env),reference_details=str(ref),reference_details_sha256=sha(ref),reference_gate=str(refgate),reference_gate_sha256=sha(refgate),source_identity={},experiment_id='CPU_EXCEPTION_CONTROL_ONLY',cells=[cell]);(project/'BUFFER4_v1_FROZEN.json').write_text(json.dumps(plan));identity={'source_commit':'harness','source_manifest_sha256':'manifest'}
            side=[None,dict(pid=24680,start_ticks=123)] if first_identity_missing else None
            with (patch.object(common,'verify_checkout',return_value=identity),patch.object(common,'root_preflight_receipt',return_value={}),patch.object(common,'child_environment',return_value={}),patch.object(queue.subprocess,'Popen',return_value=Child()),patch.object(queue.subprocess,'check_output',return_value=''),patch.object(process_cleanup,'process_identity',side_effect=side,return_value=dict(pid=24680,start_ticks=123)),patch.object(run_paired_campaign,'stop_owned_processes',return_value={'status':'PASS_SYNTHETIC_ONLY'},side_effect=process_cleanup.CleanupError('synthetic cleanup failure') if cleanup_error else None) as cleanup):
                with self.assertRaises((KeyboardInterrupt,process_cleanup.CleanupError,common.GateError)):queue.main(types.SimpleNamespace(project=str(project),root_receipt=str(receipt),cpu_gate=str(cpu)))
                gate=common.read(out/'GATE.json');record=common.read(out/'CPU_EXCEPTION_CONTROL_ONLY_OUTER_EXCEPTION_CLEANUP.json');return cleanup.call_count,gate,record
    def test_wait_interrupt_cleans_owned_sessions_once(self):
        calls,gate,record=self.exercise();self.assertEqual(calls,1);self.assertEqual(gate['status'],'FAIL_OR_INCOMPLETE_BUFFER4_PRESERVED');self.assertTrue(record['status'].startswith('PASS_OWNED_EXCEPTION_CLEANUP'));self.assertEqual(gate['incomplete_active_cell'],'CPU_EXCEPTION_CONTROL_ONLY')
    def test_cleanup_failure_is_unverified_and_propagated(self):
        calls,gate,record=self.exercise(cleanup_error=True);self.assertEqual(calls,1);self.assertFalse(record['confirmed_physical_release']);self.assertTrue(record['status'].startswith('FAIL_'));self.assertTrue(gate['status'].startswith('FAIL_'))
    def test_generation_capture_exception_still_reaches_guarded_cleanup(self):
        calls,gate,record=self.exercise(first_identity_missing=True);self.assertEqual(calls,1);self.assertTrue(gate['status'].startswith('FAIL_'))
if __name__=='__main__':unittest.main(verbosity=2)
