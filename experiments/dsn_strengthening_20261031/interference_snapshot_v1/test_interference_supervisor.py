"""Exercise the new actual Supervisor's failure/finally paths with CPU mocks."""
import hashlib,json,pathlib,tempfile,unittest
from unittest.mock import patch
from common import sha,read
from test_interference import config
from test_supervisor_cleanup import Ctx,Reader,Power,SCRATCH
import process_cleanup as pc
import interference_supervisor as supervisor

class NewSupervisorFailureControls(unittest.TestCase):
    def exercise(self,error=None):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            folder=pathlib.Path(folder);audio=folder/'audio';audio.write_bytes(b'CPU');manifest=folder/'manifest';manifest.write_bytes(b'{}');cfg=config();cfg.update(cell_id='CPU_TWO_CLIENT_DEAD_OWNER',experiment_id='CPU_TWO_CLIENT_DEAD_OWNER',harness_source=dict(source_root=str(pathlib.Path(supervisor.__file__).parent),source_manifest=str(manifest),source_manifest_sha256=sha(manifest),source_commit='test'),execution_dependencies=[]);cfg['settings']['source_commit']='test'
            for source in cfg['settings']['sources']:source.update(path=str(audio),audio_sha256=hashlib.sha256(b'CPU').hexdigest())
            path=folder/'config';path.write_text(json.dumps(cfg));out=folder/'out'
            with (patch.object(supervisor,'verify_source',return_value={'source_commit':'test'}),patch('common.verify_checkout',return_value={'source_commit':'test'}),patch.object(supervisor.mp,'get_context',return_value=Ctx()),patch.object(supervisor,'FramedReader',Reader),patch.object(supervisor,'BoundedPower',Power),patch.object(supervisor,'start_ticks',return_value=123),patch.object(supervisor,'process_identity',return_value=None),patch.object(supervisor,'kill_owner_group',return_value={'all_CUDA_owners_released':True},side_effect=error) as cleanup):
                with self.assertRaises(RuntimeError) as caught:supervisor.run_interference(path,manifest,out)
                return cleanup.call_count,str(caught.exception),read(out/'GATE.json'),read(out/'OWNER_CLEANUP.json')
    def test_registered_dead_owner_cleaned_by_new_Supervisor(self):
        count,error,gate,release=self.exercise();self.assertEqual(count,1);self.assertEqual(error,'Owner failed before initial neural readiness');self.assertTrue(gate['status'].startswith('FAIL'));self.assertTrue(release['status'].startswith('PASS_ACTUAL_FAILED'))
    def test_uncertain_release_remains_FAIL_and_propagates(self):
        count,error,gate,release=self.exercise(pc.CleanupError('CPU uncertain release'));self.assertEqual(count,1);self.assertIn('cleanup failed',error);self.assertFalse(gate['confirmed_physical_release']);self.assertFalse(release['confirmed_physical_release'])

if __name__=='__main__':unittest.main(verbosity=2)
