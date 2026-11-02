"""Formal analysis contract controls. No benchmark/model/GPU work."""
from __future__ import annotations
import pathlib,tempfile,unittest
from analysis_common import quantile,AnalysisError,canonical
from calibrate_clock_floor import batch,bracket_call,null_target
from aggregate_cost import family_row

class Controls(unittest.TestCase):
    def test_quantiles_do_not_invent_samples(self):
        self.assertIsNone(quantile([],.5));self.assertEqual(quantile([3],.95),3)
        self.assertEqual(quantile([1,3],.5),2)
    def test_null_target_checksum_preserved(self):
        # Small control invocation only; the formal4096x8 calibration is separate.
        result=batch(null_target,5);self.assertEqual(result['checksum'],10)
        self.assertGreaterEqual(result['batch_wall_ns'],0)
    def test_clock_bracket_preserves_original_result(self):
        value,row=bracket_call(null_target,19);self.assertEqual(value,19)
        self.assertEqual(set(row),{'wall_ns','thread_cpu_ns','process_cpu_ns'})
    def test_floor_annotation_never_subtracts(self):
        c=dict(cell_id='control',source_id='S',arm='conservative',repeat=0)
        row=family_row('cpu',c,'cpu','IDENTITY.bind',2,100,200,200,dict(wall_ns=100,thread_cpu_ns=100))
        self.assertEqual(row['observed_mean_wall_ms'],.00005)
        self.assertEqual(row['observed_mean_thread_cpu_ms'],.0001)
        self.assertFalse(row['floor_subtracted']);self.assertIsNone(row['independent_lock_wait'])
        self.assertTrue(row['near_null_wall_floor'])
    def test_probe_and_full_replay_accounts_distinct(self):
        c=dict(cell_id='control',source_id='S',arm='fullcall',repeat=0)
        floor=dict(wall_ns=1,thread_cpu_ns=1)
        p=family_row('cpu',c,'cpu','REPLAY_COMPONENT.equal',1,100,100,100,floor)
        w=family_row('cpu',c,'cpu','WAL.complete_fact_commit',1,100,100,100,floor)
        self.assertNotEqual(p['account'],w['account'])
    def test_canonical_selected_digest_sensitive_to_original_C(self):
        import hashlib
        a=dict(parent_state={'full':'input'},next_state={'full':'output'},token_ids=[8],selected_correction={'selected':'x'})
        b=dict(a,selected_correction={'selected':'y'})
        self.assertNotEqual(hashlib.sha256(canonical(a)).hexdigest(),hashlib.sha256(canonical(b)).hexdigest())

if __name__=='__main__':unittest.main()

