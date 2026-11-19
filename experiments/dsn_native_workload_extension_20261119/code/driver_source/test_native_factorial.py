"""Pure controller contract/arithmetic controls; no neural or GPU imports."""
import copy,unittest
from run_native_factorial import CONDITIONS,CONDITION_SETTINGS,validate_matrix,aggregate,terminal_times,power_ownership
from confirmation_common import GateError


def sources(n=2):return[dict(source_id='source'+str(i),speaker_id='speaker'+str(i),frames=160000)for i in range(n)]


def cells(ss):
    result=[]
    for repeat in (0,1):
        for source in(ss if repeat==0 else ss[::-1]):
            for condition in(CONDITIONS if repeat==0 else CONDITIONS[::-1]):
                arm,retain=CONDITION_SETTINGS[condition];n=len(result)
                result.append(dict(cell_id='cell'+str(n),source_id=source['source_id'],speaker_id=source['speaker_id'],condition=condition,strategy=arm,consumer_retain_views=retain,repeat=repeat,primary_gpu=repeat,position=n,config='config'+str(n),out='out'+str(n),log='log'+str(n),external_power='power'+str(n)))
    return result


def results(ss):
    credits=dict(r0s0=2.,r0s1=3.,r1s0=7.,r1s1=9.,conservative_s1=4.)
    out=[]
    for c in cells(ss):
        out.append(dict(cell_id=c['cell_id'],source_id=c['source_id'],speaker_id=c['speaker_id'],condition=c['condition'],strategy=c['strategy'],repeat=c['repeat'],primary=dict(offered_audio_seconds=10.,dual_deadline_audio_credit_seconds=credits[c['condition']],complete_coverage_and_original_quantile_pass=False),worker_ledger=dict(worker_seconds=12.),common_external_energy=dict(origin_to_confirmed_physical_model_drain=dict(total_joules=100.)),view_audit=dict(status='PASS_SYNTHETIC_FIXTURE',continuity=dict(compatible_ahead_applications=0,avoidable_withdrawals=0,total_gap_audio_seconds_x_wall_seconds=0.))))
    return out


class Controls(unittest.TestCase):
    def test_exact_pilot_and_confirmation_matrices(self):
        for n in(2,6,8):self.assertTrue(validate_matrix(cells(sources(n)),sources(n)))
    def test_missing_s0_rejected(self):
        ss=sources();cc=cells(ss);cc=[c for c in cc if c['condition']!='r1s0']
        with self.assertRaises(GateError):validate_matrix(cc,ss)
    def test_condition_not_underlying_arm_is_unique_axis(self):
        ss=sources();cc=cells(ss);self.assertEqual(sum(c['strategy']=='fullcall'for c in cc),8);self.assertTrue(validate_matrix(cc,ss))
    def test_wrong_s_mapping_rejected(self):
        ss=sources();cc=cells(ss);next(c for c in cc if c['condition']=='r1s0')['consumer_retain_views']=True
        with self.assertRaises(GateError):validate_matrix(cc,ss)
    def test_string_s_flag_rejected(self):
        ss=sources();cc=cells(ss);cc[0]['consumer_retain_views']='false'
        with self.assertRaises(GateError):validate_matrix(cc,ss)
    def test_conservative_anchor_is_required(self):
        ss=sources();cc=[c for c in cells(ss)if c['condition']!='conservative_s1']
        with self.assertRaises(GateError):validate_matrix(cc,ss)
    def test_no_repeat_order_reversal_rejected(self):
        ss=sources();cc=cells(ss);own=[c for c in cc if c['source_id']==ss[0]['source_id']and c['repeat']==1]
        for c,condition in zip(own,CONDITIONS):c.update(condition=condition,strategy=CONDITION_SETTINGS[condition][0],consumer_retain_views=CONDITION_SETTINGS[condition][1])
        with self.assertRaises(GateError):validate_matrix(cc,ss)
    def test_wrong_primary_rotation_rejected(self):
        ss=sources();cc=cells(ss);cc[-1]['primary_gpu']=0
        with self.assertRaises(GateError):validate_matrix(cc,ss)
    def test_duplicate_path_or_speaker_rejected(self):
        ss=sources();cc=cells(ss);cc[-1]['out']=cc[0]['out']
        with self.assertRaises(GateError):validate_matrix(cc,ss)
        ss=sources();ss[1]['speaker_id']=ss[0]['speaker_id']
        with self.assertRaises(GateError):validate_matrix(cells(ss),ss)
    def test_ties_and_no_opportunity_are_successful_outcomes(self):
        ss=sources();rr=results(ss)
        for r in rr:r['primary']['dual_deadline_audio_credit_seconds']=2.
        a=aggregate(rr,dict(sources=ss,expected_trials=20,actual_NN=dict(source_commit='n'*40)))
        self.assertTrue(a['status'].startswith('COMPLETE'));self.assertFalse(a['no_opportunity_or_tie_is_failure'])
        self.assertTrue(all(p['factorial_interaction_audio_s']==0 for p in a['repeat_pairs']))
        self.assertEqual(a['condition_totals']['conservative_s1']['whole_run_passes'],0)
        self.assertEqual(a['condition_totals']['r1s1']['continuity_totals']['avoidable_withdrawals'],0)
    def test_paired_factorial_and_resource_totals(self):
        ss=sources();a=aggregate(results(ss),dict(sources=ss,expected_trials=20,actual_NN=dict(source_commit='n'*40)))
        self.assertEqual(len(a['source_level_pairs']),2);self.assertEqual(len(a['repeat_pairs']),4)
        self.assertTrue(all(p['factorial_interaction_audio_s']==1. and p['S_at_R1_audio_s']==2. and p['joint_minus_conservative_audio_s']==5. for p in a['repeat_pairs']))
        row=a['condition_totals']['r1s1'];self.assertEqual(row['planned_offered_audio_s'],40.);self.assertEqual(row['coverage_percent'],90.);self.assertEqual(row['both_board_J'],400.);self.assertEqual(row['worker_seconds'],48.)
    def test_incomplete_or_failed_condition_has_no_full_plan_point_estimate(self):
        ss=sources();rr=results(ss);failure=rr.pop();a=aggregate(rr,dict(sources=ss,expected_trials=20,actual_NN=dict(source_commit='n'*40)),[dict(cell_id=failure['cell_id'],original_offered_audio_s=10.)])
        row=a['condition_totals'][failure['condition']];self.assertEqual(row['planned_offered_audio_s'],40.);self.assertEqual(row['unobserved_planned_audio_s'],10.);self.assertIsNone(row['coverage_percent']);self.assertEqual(len(a['failed_attempts']),1);self.assertTrue(a['status'].startswith('INCOMPLETE'))
    def test_abort_infer_is_missing_not_zero(self):
        rows,_=terminal_times([dict(kind='abandoned',job_id='j',source_id='s',worker_job_begin_perf=10.,worker_job_end_perf=12.)]);self.assertEqual(rows[0]['worker_wall_seconds'],2.);self.assertIsNone(rows[0]['observed_infer_wall_seconds'])
    def test_duplicate_terminal_not_double_charged(self):
        event=dict(kind='completed',job_id='j',source_id='s',record=dict(worker_job_wall_seconds=2.,model_seconds=1.5));rows,n=terminal_times([event,copy.deepcopy(event)]);self.assertEqual(len(rows),1);self.assertEqual(n,1)
        changed=copy.deepcopy(event);changed['record']['model_seconds']=1.
        with self.assertRaises(GateError):terminal_times([event,changed])
    def test_power_scope_requires_owned_physical_workers(self):
        ready=[dict(pid=101,gpu=0),dict(pid=102,gpu=1)];boards={'0':dict(uuid='a'),'1':dict(uuid='b')}
        rows=[dict(time=t,boards=copy.deepcopy(boards),compute_processes=[dict(pid=101,gpu_uuid='a')])for t in(0.,1.,2.)]
        self.assertTrue(power_ownership(rows,ready,boards,.5,1.5)['status'].startswith('PASS'))
        contaminated=copy.deepcopy(rows);contaminated[1]['compute_processes'].append(dict(pid=999,gpu_uuid='b'))
        with self.assertRaises(GateError):power_ownership(contaminated,ready,boards,.5,1.5)
        moved=copy.deepcopy(rows);moved[1]['compute_processes'][0]['gpu_uuid']='b'
        with self.assertRaises(GateError):power_ownership(moved,ready,boards,.5,1.5)
    def test_gap_scopes_are_preserved_not_arithmetically_merged(self):
        ss=sources();rr=results(ss)
        for r in rr:r['view_audit']['continuity'].update(avoidable_gap_scope='same-root observed union',right_censored_windows=1,max_observed_gap_seconds=4.)
        a=aggregate(rr,dict(sources=ss,expected_trials=20,actual_NN=dict(source_commit='n'*40)))
        c=a['condition_totals']['r1s0'];self.assertEqual(c['continuity_scope_values']['avoidable_gap_scope'],['same-root observed union']);self.assertEqual(c['continuity_totals']['right_censored_windows'],4);self.assertNotIn('max_observed_gap_seconds',c['continuity_totals'])


if __name__=='__main__':unittest.main()
