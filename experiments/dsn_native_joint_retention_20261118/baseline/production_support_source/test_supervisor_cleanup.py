"""CPU counterexamples for registered dead leaders and failed release proofs."""
import hashlib,json,os,pathlib,subprocess,sys,tempfile,types,unittest
from unittest.mock import patch,Mock
from common import B,sha,read
import process_cleanup as pc
local=pathlib.Path(__file__).resolve().parents[3]/'experiments/dsn_native_resilience_20261030/source_v2'
CORE=pathlib.Path(os.environ.get('REVTRACE_CORE_SOURCE',str(local if local.exists() else pathlib.Path(B)/'projects/revtrace_dsn_native_resilience_20261030/source_v2')))
sys.path.insert(0,str(CORE));import resident_supervisor as rs
SCRATCH=pathlib.Path(os.environ.get('REVTRACE_CPU_SCRATCH',str(pathlib.Path(__file__).parent/'.cpu_scratch')));SCRATCH.mkdir(parents=True,exist_ok=True)

class Conn:
    def close(self):pass
class Owner:
    pid=24680;exitcode=-9
    def start(self):pass
    def is_alive(self):return False
    def join(self,*args):pass
    def kill(self):raise AssertionError('leader-only fallback must not hide failed cleanup')
class Ctx:
    def Value(self,kind,value):return types.SimpleNamespace(value=value)
    def Process(self,**kwargs):return Owner()
    def Pipe(self,**kwargs):return Conn(),Conn()
class Reader:
    def __init__(self,connection,slot,incarnation,inbox,*args):inbox.put(dict(type='control',incarnation=0,payload=dict(kind='owner_group_started',owner_epoch=0,pid=24680,pgid=24680)))
class Power:
    def __init__(self,*args):self.recent=[dict(time=0)];self.error=None;self.t=types.SimpleNamespace(is_alive=lambda:False)
    def close(self):pass
def identity(pid=24680,ticks=123,state='S',pgid=24680,session=24680):return dict(pid=pid,start_ticks=ticks,state=state,pgid=pgid,session=session,ppid=1)

class SupervisorFailureControls(unittest.TestCase):
    def exercise(self,cleanup_side_effect=None):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            root=pathlib.Path(folder);audio=root/'audio';audio.write_bytes(b'a');manifest=root/'manifest';manifest.write_bytes(b'{}');config=dict(cell_id='CPU_REGISTERED_DEAD_OWNER_ONLY',settings=dict(source_commit='test',sources=[dict(source_id='s',frames=8000,path=str(audio),audio_sha256=hashlib.sha256(b'a').hexdigest())]),harness_source=dict(source_root=str(pathlib.Path(rs.__file__).parent),source_manifest=str(manifest),source_manifest_sha256=sha(manifest),source_commit='test'),execution_dependencies=[],request_contract='closed_loop_single_outstanding_independent_EOS_v1',request_order=['s'],maximum_service_seconds=10);cfg=root/'config';cfg.write_text(json.dumps(config));out=root/'out'
            with (patch.object(rs,'verify_source',return_value={'source_commit':'test'}),patch('common.verify_checkout',return_value={'source_commit':'test'}),patch.object(rs.mp,'get_context',return_value=Ctx()),patch.object(rs,'FramedReader',Reader),patch.object(rs,'BoundedPower',Power),patch.object(rs,'start_ticks',return_value=123),patch.object(rs,'process_identity',return_value=None),patch.object(rs,'kill_owner_group',return_value={'all_CUDA_owners_released':True},side_effect=cleanup_side_effect) as cleanup):
                with self.assertRaises(RuntimeError) as caught:rs.run_resident(cfg,manifest,out)
                return cleanup.call_count,str(caught.exception),read(out/'GATE.json'),read(out/'OWNER_CLEANUP.json')
    def test_registered_dead_leader_before_READY_still_cleans_group(self):
        count,error,gate,cleanup=self.exercise();self.assertEqual(count,1);self.assertEqual(error,'Owner failed before initial neural readiness');self.assertTrue(gate['status'].startswith('FAIL'));self.assertEqual(cleanup['status'],'PASS_ACTUAL_FAILED_TRIAL_GROUP_AND_CUDA_RELEASE')
    def test_cleanup_exception_is_not_swallowed_or_certified(self):
        count,error,gate,cleanup=self.exercise(pc.CleanupError('simulated release query failure'));self.assertEqual(count,1);self.assertIn('cleanup failed',error);self.assertFalse(gate['confirmed_physical_release']);self.assertFalse(cleanup['confirmed_physical_release'])

class OwnershipControls(unittest.TestCase):
    def test_dead_leader_group_is_actually_signalled_then_verified(self):
        worker=identity(pid=24681,ticks=150);state={'active':True};proof=dict(pid=24680,start_ticks=123,bound_Owner_registration=True,known_members=[worker])
        def members(group):return [worker] if state['active'] else []
        def killed(group,sig):state['active']=False
        with patch.object(pc,'process_identity',return_value=None),patch.object(pc,'process_group_members',side_effect=members),patch.object(pc.os,'killpg',side_effect=killed,create=True) as kill,patch.object(pc.signal,'SIGKILL',9,create=True),patch.object(pc,'cuda_owners',return_value=[]):
            result=pc.terminate_group(Owner(),proof);self.assertEqual(kill.call_count,1);self.assertTrue(result['group_SIGKILL_sent']);self.assertTrue(result['confirmed_no_executing_members'])
    def test_dead_leader_exact_known_worker_retains_cleanup_authority(self):
        worker=identity(pid=24681,ticks=150)
        with patch.object(pc,'process_identity',return_value=None),patch.object(pc,'process_group_members',return_value=[worker]):
            proof=pc.group_proof(24680,123,bound_event=True,known_members=[worker]);self.assertIn('exact same-run',proof['ownership_route'])
    def test_reused_leader_PID_refuses_any_signal(self):
        with patch.object(pc,'process_identity',return_value=identity(ticks=999)),patch.object(pc,'process_group_members',return_value=[identity(ticks=999)]),patch.object(pc.os,'killpg',create=True) as kill:
            with self.assertRaises(pc.CleanupError):pc.terminate_group(None,dict(pid=24680,start_ticks=123,bound_Owner_registration=True,known_members=[]))
            kill.assert_not_called()
    def test_dead_leader_unknown_worker_generation_cannot_authorize_kill(self):
        with patch.object(pc,'process_identity',return_value=None),patch.object(pc,'process_group_members',return_value=[identity(pid=24681,ticks=999)]),patch.object(pc.os,'killpg',create=True) as kill:
            with self.assertRaises(pc.CleanupError):pc.terminate_group(None,dict(pid=24680,start_ticks=123,known_members=[{'pid':24681,'start_ticks':150}]))
            kill.assert_not_called()
    def test_foreign_session_refuses_signal_even_known_PID(self):
        worker=identity(pid=24681,ticks=150,session=999)
        with patch.object(pc,'process_identity',return_value=None),patch.object(pc,'process_group_members',return_value=[worker]):
            with self.assertRaises(pc.CleanupError):pc.group_proof(24680,123,known_members=[worker])
    def test_unregistered_live_leader_requires_actual_own_session(self):
        with patch.object(pc,'process_identity',return_value=identity(pgid=999,session=999)),patch.object(pc,'process_group_members',return_value=[]):
            with self.assertRaises(pc.CleanupError):pc.group_proof(24680,123,bound_event=False)
    def test_cli_hang_has_explicit_timeout_and_never_returns_release(self):
        with patch.object(pc.subprocess,'check_output',side_effect=subprocess.TimeoutExpired('nvidia-smi',.1)) as query:
            with self.assertRaises(pc.CleanupError):pc.cuda_owners(timeout=.1)
            self.assertEqual(query.call_args.kwargs['timeout'],.1)
    def test_cuda_query_failure_does_not_fall_back_to_empty_owner_set(self):
        with patch.object(pc.subprocess,'check_output',side_effect=subprocess.CalledProcessError(1,'nvidia-smi')):
            with self.assertRaises(pc.CleanupError):pc.cuda_owners(timeout=.1)
    def test_global_deadline_covers_release_confirmation(self):
        proof=dict(pid=24680,pgid=24680,start_ticks=123,known_members=[])
        with patch.object(pc,'refresh_proof',return_value=proof),patch.object(pc,'process_group_members',return_value=[]),patch.object(pc.time,'perf_counter',side_effect=[0.,2.]),patch.object(pc,'cuda_owners') as query:
            with self.assertRaises(pc.CleanupError):pc.terminate_group(None,proof,timeout=1.)
            query.assert_not_called()
    def test_torn_final_diagnostic_row_keeps_exact_prior_worker_proof(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            root=pathlib.Path(folder);path=root/'owner_e0';path.mkdir();(path/'owner_events.jsonl').write_text(json.dumps(dict(kind='worker_started',pid=24681,start_ticks=150))+'\n'+ '{"kind":',encoding='utf8')
            self.assertEqual(pc.owned_worker_identities(root,0),[{'pid':24681,'start_ticks':150}])
    def test_non_tail_identity_metadata_corruption_is_not_accepted(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            root=pathlib.Path(folder);path=root/'owner_e0';path.mkdir();(path/'owner_events.jsonl').write_text('{bad}\n'+json.dumps(dict(kind='worker_started',pid=24681,start_ticks=150))+'\n',encoding='utf8')
            with self.assertRaises(pc.CleanupError):pc.owned_worker_identities(root,0)
if __name__=='__main__':unittest.main(verbosity=2)
