"""Actual coordinator/Owner CPU controls for shared fair resource allocation."""
import copy,json,pathlib,tempfile,time,types,unittest
import numpy as np
from round_robin_dispatch import CanonicalFirstRoundRobin
from resilience_policy import ResilientFullSpecCoordinator
from resilience_inbound import audit_value
from feedback_contract import FeedbackCut
from test_resilience_policy import cut
from test_resilience_owner_integration import Harness
from test_resilience_storage import body,cut as storage_cut


def coordinator(sids=('a','b')):
    return ResilientFullSpecCoordinator(initials={s:cut(0).state for s in sids},
        audio={s:np.zeros(40000,dtype=np.float32) for s in sids},runtime_identity={'CPU':'fixed'},
        source_frames={s:40000 for s in sids},authority_workers=('f0','f1'),owner_epoch=0,
        before_commit=lambda _:dict(transition_id='t',journal_seq=1,record_sha='a'*64))


def register(c,sid,slot,serial,start=None):
    start=c.canonical(sid) if start is None else start
    return c.register(job_id=f'e0-j{serial:09d}',worker=slot,kind='full',source_id=sid,
        start=start,end=start.frontier+8000,dispatched_perf=1.)


def early(c,job,end):
    event=dict(kind='asr_early',worker=job['worker'],worker_incarnation=0,job_id=job['job_id'],
        source_id=job['source_id'],dispatch_epoch=0,start_state=job['start'].state,
        start_state_sha=job['start'].sha256,end_frontier=job['end'],producer_role='authority',
        produced_perf=2.,candidate_wire=None,projection=dict(kind='typed_ASR_stage_identity_feedback_projection',
        learned_C_executed=False,original_full_infer_completed=False,token_ids=[8000],end=end.state,end_state_sha=end.sha256))
    c.receive_event(job['worker'],0,event,received_perf=3.)


class DispatchControls(unittest.TestCase):
    def test_global_canonical_precedes_first_source_conditional(self):
        c=coordinator();j=register(c,'a','f0',1);early(c,j,cut(8000,'prediction'))
        rr=CanonicalFirstRoundRobin(('a','b'));p=rr.peek(c,{'a':16000,'b':8000},allow_speculation=True,max_ahead_frames=32000)
        self.assertEqual((p.source_id,p.layer),('b','canonical'))
        self.assertEqual(p.eligible_conditional_sources,('a',))
    def test_blocked_source_is_skipped_and_no_work_does_not_advance(self):
        c=coordinator();rr=CanonicalFirstRoundRobin(('a','b'))
        self.assertIsNone(rr.peek(c,{'a':7999,'b':7999},allow_speculation=True,max_ahead_frames=32000))
        self.assertEqual((rr.cursor,rr.successful_dispatches),(0,0))
        p=rr.peek(c,{'a':7999,'b':8000},allow_speculation=True,max_ahead_frames=32000)
        self.assertEqual(p.source_id,'b');self.assertEqual(rr.successful_dispatches,0)
    def test_probe_has_no_admission_promotion_or_receipt_side_effect(self):
        c=coordinator();j=register(c,'a','f0',1);early(c,j,cut(8000,'prediction'))
        before=audit_value(dict(jobs=c.jobs,completed=c.completed_full,promotions=list(c.promotions),active=c.active_authority))
        rr=CanonicalFirstRoundRobin(('a','b'))
        for _ in range(3):rr.peek(c,{'a':16000,'b':8000},allow_speculation=True,max_ahead_frames=32000)
        self.assertEqual(audit_value(dict(jobs=c.jobs,completed=c.completed_full,promotions=list(c.promotions),active=c.active_authority)),before)
    def test_second_slot_reprobes_after_register_and_advances_only_confirmed_send(self):
        c=coordinator();rr=CanonicalFirstRoundRobin(('a','b'));accepted={'a':8000,'b':8000}
        p=rr.peek(c,accepted,allow_speculation=True,max_ahead_frames=32000);register(c,p.source_id,'f0',1,p.start)
        self.assertEqual(rr.cursor,0);trace=rr.confirm_dispatch(p,slot='f0');self.assertEqual(trace['cursor_after'],1)
        q=rr.peek(c,accepted,allow_speculation=True,max_ahead_frames=32000)
        self.assertEqual(q.source_id,'b')
        with self.assertRaises(ValueError):rr.confirm_dispatch(p,slot='f0')
    def test_later_ingress_release_cannot_rewrite_decision_snapshot(self):
        c=coordinator();rr=CanonicalFirstRoundRobin(('a','b'));accepted={'a':8000,'b':0}
        p=rr.peek(c,accepted,allow_speculation=True,max_ahead_frames=32000);accepted['b']=8000
        trace=rr.confirm_dispatch(p,slot='f0')
        self.assertEqual(trace['accepted_frontier_snapshot'],{'a':8000,'b':0})
        self.assertEqual(trace['eligible_canonical_sources'],['a'])
    def test_one_source_order_and_max_ahead_match_original_full_start(self):
        c=coordinator(('a',));rr=CanonicalFirstRoundRobin(('a',))
        old=c.next_full_start('a',16000,32000);p=rr.peek(c,{'a':16000},allow_speculation=True,max_ahead_frames=32000)
        self.assertTrue(p.start.same(old));j=register(c,'a','f0',1);early(c,j,cut(8000,'p'))
        self.assertIsNone(rr.peek(c,{'a':16000},allow_speculation=True,max_ahead_frames=8000))
        p=rr.peek(c,{'a':16000},allow_speculation=True,max_ahead_frames=32000)
        self.assertTrue(p.start.same(c.next_full_start('a',16000,32000)));self.assertEqual(p.layer,'conditional')
    def test_empty_sources_and_conservative_never_create_conditional_proposal(self):
        rr=CanonicalFirstRoundRobin(());self.assertIsNone(rr.peek(None,{},allow_speculation=True,max_ahead_frames=32000))
        c=coordinator(('a',));j=register(c,'a','f0',1);early(c,j,cut(8000,'p'))
        rr=CanonicalFirstRoundRobin(('a',));self.assertIsNone(rr.peek(c,{'a':16000},allow_speculation=False,max_ahead_frames=32000))
    def test_dispatcher_does_not_bypass_original_receipt_or_full_target_guard(self):
        c=coordinator(('a',));p=CanonicalFirstRoundRobin(('a',)).peek(c,{'a':8000},allow_speculation=True,max_ahead_frames=32000)
        with self.assertRaises(ValueError):c.register(job_id='e0-j000000001',worker='f0',kind='full',source_id='a',start=p.start,end=p.end,dispatched_perf=1.,receipt=object())
        with self.assertRaises(ValueError):c.register(job_id='e0-j000000001',worker='f0',kind='full',source_id='a',start=p.start,end=16000,dispatched_perf=1.)


class MultiHarness(Harness):
    def __init__(self,folder,*,arm='conservative',n=4,dynamic_second=False):
        super().__init__(folder,arm=arm)
        self.sids=tuple(chr(ord('a')+i) for i in range(n));self.dynamic_second=dynamic_second;self.waiting=[]
        self.initials={s:self.root.state for s in self.sids}
        self.accepted={s:types.SimpleNamespace(value=16000 if not dynamic_second or s=='a' else 0) for s in self.sids}
        self.config['settings']['sources']=[dict(source_id=s,path='unused_'+s+'.wav',frames=16000,audio_sha256='immutable') for s in self.sids]
    def send(self,message):
        super().send(message)
        if self.dynamic_second and message['kind']=='publication' and message['event']['source_id']=='a' and message['event']['kind']=='private':self.accepted['b'].value=16000
    def execute(self,slot,incarnation,command):
        self.commands.append(copy.deepcopy(command));sid=command['source_id'];start=FeedbackCut(command['start']);end=storage_cut(command['end'],sid+'-'+str(command['end']))
        projection=dict(kind='typed_ASR_stage_identity_feedback_projection',learned_C_executed=False,original_full_infer_completed=False,token_ids=[end.frontier],end=end.state,end_state_sha=end.sha256)
        event=dict(kind='asr_early',worker=slot,worker_incarnation=incarnation,job_id=command['job_id'],source_id=sid,dispatch_epoch=command['dispatch_epoch'],start_state=start.state,start_state_sha=start.sha256,end_frontier=end.frontier,producer_role='authority',produced_perf=time.perf_counter(),projection=projection,candidate_wire=None)
        record=body(start,end)['record'];record.update(model_start=self.policy.jobs[command['job_id']]['dispatched_perf'],model_end=time.perf_counter())
        complete=dict(kind='completed',worker=slot,worker_incarnation=incarnation,job_id=command['job_id'],source_id=sid,dispatch_epoch=command['dispatch_epoch'],start=start.state,end=end.state,record=record)
        self.enqueue(slot,incarnation,event)
        if self.dynamic_second and sid=='a' and start.frontier==0:self.waiting.append((slot,incarnation,complete))
        else:
            self.enqueue(slot,incarnation,complete)
            for held in self.waiting:self.enqueue(*held)
            self.waiting.clear()


class ActualOwnerDispatchControls(unittest.TestCase):
    def run_case(self,arm,n=4,dynamic=False):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);p=pathlib.Path(tmp.name);h=MultiHarness(p,arm=arm,n=n,dynamic_second=dynamic);self.addCleanup(h.close);h.run()
        self.assertFalse(any(e['kind']=='owner_error' for e in h.events))
        self.assertTrue(all(h.consumer.snapshot(s)['certified_frontier']==16000 for s in h.sids))
        events=[json.loads(line) for line in (p/'owner_e0/owner_events.jsonl').read_text().splitlines()]
        dispatches=[e['dispatch'] for e in events if e['kind']=='shared_dispatcher_successful_dispatch']
        return h,dispatches
    def test_actual_Conservative_uses_both_cards_and_round_robins_four_sources(self):
        h,rows=self.run_case('conservative')
        self.assertEqual([r['source_id'] for r in rows[:4]],['a','b','c','d'])
        self.assertEqual({r['slot'] for r in rows[:2]},{'full0','full1'})
        self.assertTrue(all(r['chosen_layer']=='canonical' for r in rows))
    def test_actual_fullcall_prefers_other_ready_canonical_over_first_chain_tail(self):
        h,rows=self.run_case('fullcall',n=2,dynamic=True)
        self.assertEqual([r['source_id'] for r in rows[:2]],['a','b'])
        self.assertEqual(rows[1]['chosen_layer'],'canonical');self.assertIn('a',rows[1]['eligible_conditional_sources'])
    def test_actual_all_six_arms_share_canonical_first_round_robin(self):
        for arm in ('conservative','fullcall','dependency_versioned','ready_only','uir','safe_versioned'):
            with self.subTest(arm=arm):
                h,rows=self.run_case(arm,n=2)
                self.assertEqual([r['source_id'] for r in rows[:2]],['a','b'])
                self.assertTrue(all(r['policy']=='shared_canonical_first_round_robin_v1' for r in rows))


if __name__=='__main__':unittest.main()
