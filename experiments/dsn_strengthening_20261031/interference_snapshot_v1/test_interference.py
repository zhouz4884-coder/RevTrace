"""Counterexamples for concurrent request clocks and executed interference.

Synthetic CPU evidence only. No import of Torch, CUDA, models or GPU tools.
"""
from __future__ import annotations
import copy,types,unittest
from common import GateError
from interference_contract import CONTRACT,CLIENTS,ORDER,A,B,TwoClients,due_frontier
from interference_analysis import audit_clocks,audit_dispatch,audit_continuity,opportunity_decision,PASS
from interference_observer import attach_observer
from endpoints import recount

def config(arm='fullcall',frames=9000):
    return dict(request_contract=CONTRACT,clients=copy.deepcopy(CLIENTS),client_first_offsets={'A':0.,'B':2.},fault={'kind':'none'},maximum_owner_restarts=0,maximum_service_seconds=240,arm=arm,settings=dict(corrector_dtype='float32',max_ahead_frames=32000,sources=[dict(source_id=sid,frames=frames,audio_sha256=sid) for sid in ORDER]))

def clocks():
    cfg=config();ledger=[];controller=TwoClients(cfg,ledger.append);controller.start(100.)
    rows=[]
    def finish(sid,stamp,callback):
        row=dict(kind='canonical',source_id=sid,observed=stamp,visible_frontier=9000,certified_frontier=9000);rows.append(row);controller.complete(dict(applied=True,row=row),callback)
    finish(A[0],101.,101.1);controller.poll(102.);finish(A[1],102.5,102.6);finish(B[0],103.,103.1);finish(B[1],104.,104.1)
    origins=controller.snapshot();ingress=[]
    for sid in ORDER:
        for f in (8000,9000):ingress.append(dict(source_id=sid,frontier=f,original_offer=origins[sid]+f/16000,observed=origins[sid]+f/16000+.001,audio_sha256=sid))
    ingress.sort(key=lambda r:r['observed']);return cfg,origins,ledger,ingress,rows

class ConcurrentClockControls(unittest.TestCase):
    def audit(self,data):return audit_clocks(data[0],100.,*data[1:])
    def test_two_clients_advance_on_their_own_EOS(self):
        data=clocks();self.assertEqual(self.audit(data)['requests'],4)
        admits={r['source_id']:r for r in data[2] if r['kind']=='request_admitted'}
        self.assertLess(admits[A[1]]['observed'],admits[B[0]]['observed'])
    def test_B_first_release_independent_of_A_EOS(self):
        ledger=[];c=TwoClients(config(),ledger.append);c.start(100.);c.poll(102.)
        self.assertEqual(c.snapshot(),{A[0]:100.,B[0]:102.});self.assertFalse(c.completed)
    def test_future_sid_accepted_frontier_stays_zero(self):
        c=TwoClients(config(),lambda r:None);c.start(100.);c.poll(101.9)
        self.assertNotIn(B[0],c.snapshot());self.assertNotIn(A[1],c.snapshot());self.assertEqual(due_frontier(9000,102.,101.9),0)
    def test_late_B_poll_keeps_fixed_origin_and_counts_delay(self):
        c=TwoClients(config(),lambda r:None);c.start(100.);c.poll(103.)
        self.assertEqual(c.snapshot()[B[0]],102.);self.assertEqual(c.admitted[B[0]]['observed'],103.)
    def test_provisional_EOS_cannot_release_next_request(self):
        c=TwoClients(config(),lambda r:None);c.start(100.)
        c.complete(dict(applied=True,row=dict(kind='private',source_id=A[0],certified_frontier=8000,visible_frontier=9000,observed=101.)),101.1)
        self.assertNotIn(A[1],c.snapshot())
    def test_private_row_cannot_impersonate_certified_EOS(self):
        c=TwoClients(config(),lambda r:None);c.start(100.)
        with self.assertRaises(GateError):c.complete(dict(applied=True,row=dict(kind='private',source_id=A[0],certified_frontier=9000,observed=101.)),101.1)
    def test_no_global_clock_shortcut(self):
        data=clocks();sources={r['source_id']:r for r in data[0]['settings']['sources']}
        correct=recount(data[4],sources,data[1]);wrong=recount(data[4],sources,{sid:100. for sid in ORDER})
        self.assertTrue(correct['original_quantile_test_pass']);self.assertFalse(wrong['original_quantile_test_pass'])
        self.assertEqual(sum(r['is_EOS'] for r in correct['frontiers']),4)
    def test_cross_client_EOS_release_rejected(self):
        data=clocks();row=next(r for r in data[2] if r['kind']=='request_admitted' and r['source_id']==A[1]);row['previous_source_id']=B[0]
        with self.assertRaises(GateError):self.audit(data)
    def test_dropped_short_EOS_rejected(self):
        data=clocks();data[3].pop()
        with self.assertRaises(GateError):self.audit(data)
    def test_other_request_EOS_does_not_supply_witness(self):
        data=clocks();data[4][0]['source_id']=B[0]
        with self.assertRaises(GateError):self.audit(data)
    def test_future_consumer_work_rejected(self):
        data=clocks();data[4].append(dict(kind='private',source_id=B[1],observed=100.,certified_frontier=0))
        with self.assertRaises(GateError):self.audit(data)
    def test_EOS_cannot_precede_actual_EOS_ingress(self):
        data=clocks();next(r for r in data[3] if r['source_id']==B[1] and r['frontier']==9000)['observed']=105.
        with self.assertRaises(GateError):self.audit(data)
    def test_partition_alias_and_phase_changes_rejected(self):
        for key in ('clients','client_first_offsets'):
            cfg=config();cfg[key]={'A':list(A),'B':list(A)} if key=='clients' else {'A':0.,'B':.25}
            with self.assertRaises(GateError):TwoClients(cfg,lambda r:None)

def dispatch_fixture():
    cfg=config(frames=24000);genesis={sid:dict(frontier=0,sid=sid) for sid in ORDER};dispatch=[];observations=[];worker=[]
    ingress=[dict(source_id=A[0],frontier=8000,observed=100.4),dict(source_id=A[0],frontier=16000,observed=101.),dict(source_id=B[0],frontier=8000,observed=102.6)]
    for index,(frontier,stamp,endstamp,slot) in enumerate([(0,100.5,104.5,'full0'),(8000,103.01,105.,'full1')],1):
        sid=A[0];start=dict(frontier=frontier,sid=sid);jid=f'e0-j{index:09d}';job=dict(job_id=jid,worker=slot,source_id=sid,start=start,end=frontier+8000,dispatch_epoch=0,dispatched_perf=stamp)
        dispatch.append(dict(owner_epoch=0,physical_slot=slot,physical_incarnation=0,pid=1000+index,job=job))
        live=[] if index==1 else [{k:dispatch[0]['job'][k] for k in ('job_id','source_id','start','end','dispatch_epoch')}]
        accepted={s:0 for s in ORDER};accepted[A[0]]=frontier+8000
        if index==2:accepted[B[0]]=8000
        observations.append(dict(owner_epoch=0,job_id=jid,worker=slot,worker_incarnation=0,source_id=sid,start=copy.deepcopy(start),end=frontier+8000,dispatch_epoch=0,original_dispatched_perf=stamp,proposal_id=index,proposal_before_perf=stamp-.02,proposal_after_perf=stamp-.01,registration_before_perf=stamp+.001,registration_after_perf=stamp+.002,decision_snapshot_perf=stamp-.02,accepted_argument=frontier+8000,started_on_current_canonical=index==1,canonical_cuts=copy.deepcopy(genesis),accepted_before=accepted,session_epochs={s:0 for s in ORDER},live_jobs_before=live,completed_jobs_before=[]))
        worker.append(dict(physical_slot=slot,physical_incarnation=0,event=dict(kind='completed',worker=slot,job_id=jid,source_id=sid,dispatch_epoch=0,start=start,record=dict(worker_job_begin_perf=stamp+.01,worker_job_end_perf=endstamp),sent_perf=endstamp+.01)))
    return cfg,observations,dispatch,worker,[],genesis,ingress

class ActualDispatchControls(unittest.TestCase):
    def test_real_UID_worker_and_ready_B_bound(self):self.assertEqual(audit_dispatch(*dispatch_fixture())['B_current_ready_inversions'],1)
    def test_proposal_without_actual_dispatch_does_not_count(self):
        data=dispatch_fixture();data[2].pop()
        with self.assertRaises(GateError):audit_dispatch(*data)
    def test_dispatch_without_actual_worker_terminal_rejected(self):
        data=dispatch_fixture();data[3].pop()
        with self.assertRaises(GateError):audit_dispatch(*data)
    def test_other_UID_or_worker_cannot_supply_execution(self):
        for key,value in [('job_id','foreign'),('worker','full0')]:
            data=dispatch_fixture();data[3][-1]['event'][key]=value
            with self.assertRaises(GateError):audit_dispatch(*data)
    def test_future_B_acceptance_does_not_become_ready_earlier(self):
        data=dispatch_fixture();data[6][-1]['observed']=104.
        with self.assertRaises(GateError):audit_dispatch(*data)
    def test_complete_input_comparison_not_frontier_only(self):
        data=dispatch_fixture();data[1][-1]['canonical_cuts'][B[0]]['other']='different'
        with self.assertRaises(GateError):audit_dispatch(*data)
    def test_no_B_ready_is_nonpreemptive_future_arrival_not_inversion(self):
        data=dispatch_fixture();data[1][-1]['accepted_before'][B[0]]=0
        self.assertEqual(audit_dispatch(*data)['dispatch_boundary_inversions'],0)
    def test_registered_object_must_match_actual_owned_input(self):
        data=dispatch_fixture();data[1][-1]['start']['changed']=True
        with self.assertRaises(GateError):audit_dispatch(*data)

class ObservationNoninterferenceControls(unittest.TestCase):
    def test_original_object_return_and_state_transition_are_preserved(self):
        class Cut:
            def __init__(self,n):self.state={'frontier':n};self.frontier=n
            def same(self,other):return self.state==other.state
        class Policy:
            def __init__(self):self.root=Cut(0);self.proposal=Cut(8000);self.jobs={};self.completed_full={};self.epochs={'s':0};self.owner_epoch=0;self.calls=[]
            def canonical(self,sid):return self.root
            def next_full_start(self,sid,accepted,*a,**k):self.calls.append(('next',sid,accepted));return self.proposal
            def register(self,**kw):
                self.calls.append(('register',kw['job_id']));job=dict(kw,dispatch_epoch=0);self.jobs[kw['job_id']]=job;return job
        normal=Policy();observed=Policy();logs=[];counter=iter(range(1,50));restore=attach_observer(Policy,{'s':types.SimpleNamespace(value=16000)},{'s':dict(frames=24000)},logs.append,clock=lambda:next(counter))
        try:
            proposal=observed.next_full_start('s',16000);self.assertIs(proposal,observed.proposal)
            job=observed.register(job_id='j',worker='full0',worker_incarnation=0,kind='full',source_id='s',start=proposal,end=16000,dispatched_perf=3.)
            self.assertIs(job,observed.jobs['j']);self.assertEqual(observed.calls,[('next','s',16000),('register','j')]);self.assertEqual(len(logs),1)
        finally:restore()
        self.assertIs(normal.next_full_start('s',16000),normal.proposal)
        self.assertEqual(observed.calls,normal.calls+[('register','j')])
    def test_original_exception_is_not_swallowed(self):
        class Policy:
            def next_full_start(self,*a,**k):raise ValueError('original')
            def register(self,**k):raise ValueError('original')
        restore=attach_observer(Policy,{}, {},lambda r:None)
        try:
            with self.assertRaisesRegex(ValueError,'original'):Policy().next_full_start('s',0)
        finally:restore()

def decision_rows(reps=1):
    rows=[]
    for rep in range(reps):
        for arm in ('conservative','fullcall'):
            summary=dict(gate=PASS,per_request=[dict(primary=dict(C8_misses_all_offered=0,missing_C_frontiers=0,missing_D_frontiers=0)) for _ in ORDER],per_client={'B':dict(worst_request_C99=5. if arm=='conservative' else 6.1,C8_misses_all_offered=0)},dispatch_observation={'B_current_ready_inversions':int(arm=='fullcall')})
            rows.append(dict(arm=arm,repeat=rep,summary=summary))
    return rows

class RootGateControls(unittest.TestCase):
    def test_credit_gain_not_required_by_root_revision(self):self.assertEqual(opportunity_decision(decision_rows())['status'],'CONTINUE_PREWRITTEN_SECOND_OPPORTUNITY_PAIR')
    def test_extra_four_C8_frontiers_is_alternative(self):
        rows=decision_rows();rows[1]['summary']['per_client']['B'].update(worst_request_C99=5.5,C8_misses_all_offered=4)
        self.assertTrue(opportunity_decision(rows)['status'].startswith('CONTINUE'))
    def test_relative_and_absolute_latency_threshold_both_needed(self):
        rows=decision_rows();rows[0]['summary']['per_client']['B']['worst_request_C99']=10.;rows[1]['summary']['per_client']['B']['worst_request_C99']=11.5
        self.assertTrue(opportunity_decision(rows)['status'].startswith('NO_GO'))
    def test_one_C8_miss_in_Conservative_blocks_feasibility(self):
        rows=decision_rows();rows[0]['summary']['per_request'][0]['primary']['C8_misses_all_offered']=1
        self.assertTrue(opportunity_decision(rows)['status'].startswith('NO_GO'))
    def test_actual_inversion_required_even_with_bad_B_latency(self):
        rows=decision_rows();rows[1]['summary']['dispatch_observation']['B_current_ready_inversions']=0
        self.assertTrue(opportunity_decision(rows)['status'].startswith('NO_GO'))
    def test_each_repeat_must_pass_not_pooled(self):
        rows=decision_rows(2);rows[-1]['summary']['per_client']['B']['worst_request_C99']=5.1
        self.assertTrue(opportunity_decision(rows,final=True)['status'].startswith('NO_GO'))
    def test_missing_or_duplicate_pair_rejected(self):
        with self.assertRaises(GateError):opportunity_decision(decision_rows()[:1])
        rows=decision_rows();rows[1]=copy.deepcopy(rows[0])
        with self.assertRaises(GateError):opportunity_decision(rows)

if __name__=='__main__':unittest.main(verbosity=2)
