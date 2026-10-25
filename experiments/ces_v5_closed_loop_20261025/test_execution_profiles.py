"""Explicit CPU extraction fixtures, not GPU measurements."""
from copy import deepcopy
import unittest
from fit_execution_profiles import (audio_bin,root_probability,proposal_features,
    collect_cell,build_profiles,validate_cell_result)


def fixture(*,node=True,obsolete=False,received=1.,published=1.1,fallback=False,same=True,match=True):
    records=[]
    events=[{'kind':'run-start','t0_perf':0.}]
    if node:
        j={'job_id':'p1','session_id':0,'source_id':'source','role':'proposal',
            'parent':0 if same else 5,'prompt_tokens':[1] if same else [9],
            'audio_start_sample':0,'audio_end_sample':32000,'contract_digest':'c'}
        r={'received_perf':received,'token_ids':[2,3],'state_tokens':[1,2],
            '_row_receipt':{'terminal_perf':.5,'binding':{'batch_id':'batch-p','job_id':'p1'}}}
        records.append({'job':j,'result':r})
        if obsolete:events.append({'kind':'proposal-obsolete','job_id':'p1'})
        else:events.append({'kind':'display','job_id':'p1','displayed':published})
    aj={'job_id':'a1','session_id':0,'source_id':'source','role':'authority',
        'parent':0,'prompt_tokens':[1],'audio_start_sample':0,'audio_end_sample':32000,
        'enqueue_perf':2.,'contract_digest':'c','ces_operation':'verify' if fallback else 'generate',
        'candidate_origin_job_id':'p1'}
    ar={'state_tokens':[1,2] if match else [3], 'online_verification':{'fallback_used':fallback}}
    records.append({'job':aj,'result':ar});events.append({'kind':'commit','job_id':'a1'})
    accounts=[{'batch_id':'batch-p','job_ids':['p1'],'worker_started_perf':0.,
               'batch_drained_perf':1.,'phases':[{'phase':'generate'}]}] if node else []
    return records,events,accounts


class ProfileTests(unittest.TestCase):
    def test_sparse_probability_remains_unknown(self):
        self.assertIsNone(root_probability(0,0)['probability'])
        self.assertIsNone(root_probability(7,7)['probability'])
        r=root_probability(8,8)
        self.assertEqual(r['probability'],8.5/9.)
        self.assertLess(r['lower'],1.);self.assertLessEqual(r['upper'],1.)

    def test_no_node_not_counted_as_incompatibility(self):
        p,b,c,ex=collect_cell('fixture',*fixture(node=False))
        self.assertEqual(c[0]['birth_group'],'')
        self.assertEqual(c[0]['root_equal'],'')
        self.assertEqual(ex['direct_no_completed_same_boundary_node'],1)

    def test_obsolete_completed_node_not_available(self):
        p,b,c,ex=collect_cell('fixture',*fixture(obsolete=True))
        self.assertEqual(c[0]['available_nodes_at_enqueue'],0)
        self.assertEqual(c[0]['same_boundary_completed_nodes'],1)
        self.assertEqual(c[0]['no_node_reason'],'completed_but_not_available_private_node')

    def test_future_owner_completion_or_publication_not_used(self):
        for kwargs in ({'received':3.},{'published':3.}):
            _,_,c,_=collect_cell('fixture',*fixture(**kwargs))
            self.assertEqual(c[0]['birth_group'],'')

    def test_actual_same_root_match_counted(self):
        p,b,c,_=collect_cell('fixture',*fixture())
        self.assertEqual(c[0]['birth_group'],'same');self.assertTrue(c[0]['root_equal'])
        self.assertEqual(p[0]['row_fraction'],.5)
        self.assertEqual(b[0]['physical_lease_s'],1.)
        profile,_=build_profiles(p,b,c)
        self.assertEqual(profile['compatibility']['direct']['same']['support'],1)
        self.assertIsNone(profile['compatibility']['direct']['same']['probability'])

    def test_fallback_birth_mismatch_is_observed_not_hard_failure(self):
        _,_,c,_=collect_cell('fixture',*fixture(fallback=True,same=False,match=True))
        self.assertEqual(c[0]['operation'],'fallback')
        self.assertEqual(c[0]['birth_group'],'mismatch')
        self.assertTrue(c[0]['root_equal'])

    def test_fault_override_not_a_predictor_feature(self):
        records,_,_=fixture();j=records[0]['job'];before=proposal_features([j])
        j['fault_actual_prompt_tokens']=list(range(1000));j['future_generated_tokens']=200
        self.assertEqual(proposal_features([j]),before)
        self.assertEqual(before[-1],0.)

    def test_bad_row_clock_is_not_clipped(self):
        records,events,accounts=fixture();records[0]['result']['_row_receipt']['terminal_perf']=2.
        with self.assertRaisesRegex(AssertionError,'outside actual physical lease'):
            collect_cell('fixture',records,events,accounts)

    def test_audio_bins_are_disjoint(self):
        self.assertEqual([audio_bin(x) for x in [0,8,8.001,16,16.001]],
                         ['0-8','0-8','8-16','8-16','16+'])

    def test_complete_token_limit_boundary_keeps_all_actual_cost(self):
        result={'decision':'TOKEN_LIMIT_BOUNDARY','fine_window_accounting_complete':True,'token_limit_events':1}
        self.assertEqual(validate_cell_result(result),'TOKEN_LIMIT_BOUNDARY')
        records,events,accounts=fixture()
        records[0]['result'].update(hit_token_limit=True,terminated_by_eos=False,token_ids=list(range(256)))
        p,b,c,_=collect_cell('capped-fixture',records,events,accounts)
        self.assertEqual(len(p),1);self.assertTrue(p[0]['hit_token_limit'])
        self.assertEqual(p[0]['generated_tokens'],256)
        self.assertEqual(b[0]['physical_lease_s'],1.)
        self.assertTrue(c[0]['root_equal'])
        profile,_=build_profiles(p,b,c)
        self.assertEqual(profile['proposal']['median_generated_tokens_by_audio_bin']['0-8']['median_generated_tokens'],256)

    def test_incomplete_run_cannot_pass_by_relabeling_as_boundary(self):
        with self.assertRaises(AssertionError):
            validate_cell_result({'decision':'TOKEN_LIMIT_BOUNDARY','fine_window_accounting_complete':False})
        with self.assertRaises(AssertionError):
            validate_cell_result({'decision':'ERROR','fine_window_accounting_complete':True})


if __name__=='__main__':unittest.main()
