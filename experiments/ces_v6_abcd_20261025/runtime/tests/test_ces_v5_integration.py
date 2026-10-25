"""CPU fixtures for online ACK plumbing; no GPU or service-performance claims."""
from dataclasses import FrozenInstanceError,replace
from copy import deepcopy
import time
import numpy as np
import pytest

from revtrace.certified_display import ConsumerAck,ContinuityView,RealtimeConsumer
from revtrace.ces_runtime import CESScheduler
from test_ces import CAL,EvidenceFake,owner as old_owner
from test_live_qwen import Clock


def ack_for(owner,sequence=1,sid=0,frontier=32000,observed=None,**changes):
    s=owner.sessions[sid]
    return replace(ConsumerAck(sequence,owner.t0,owner.contract_digest,sid,
        s.state.contract_epoch,s.state.checkpoint_id,frontier,0,
        owner.clock() if observed is None else observed),**changes)


def test_ack_is_immutable_and_actual_consumer_application_only(tmp_path):
    consumer=RealtimeConsumer(tmp_path/'consumer.jsonl')
    began=time.perf_counter()
    consumer.put({'kind':'run-start','t0_perf':began,'contract_digest':'c'})
    consumer.put({'kind':'display','job_id':'a','session_id':0,'time':0.,
        'displayed':0.,'text':'x','audio_end_sample':32000,'display_revision':1,
        'version':0,'contract_epoch':1,'contract_digest':'c'})
    consumer.close()
    acks=consumer.drain_acks()
    assert len(acks)==1 and isinstance(acks,tuple)
    assert acks[0].observed_perf==consumer.rows[0]['observed_perf']>=began
    with pytest.raises(FrozenInstanceError):acks[0].valid_visible_frontier=64000
    assert consumer.drain_acks()==()


def test_owner_publication_is_not_actual_display_credit():
    s=old_owner('fine');session=s.sessions[0]
    s.clock.sleep(2.1)
    session.visible_frontier=32000
    session.display_ever_frontier=32000
    s._drain_consumer_acks(s.clock())
    assert s._display_status(session,1,s.clock())==(False,False)
    s.close()


def test_ack_duplicate_epoch_and_retraction_preserve_first_visibility():
    s=old_owner('fine');s.clock.sleep(2.1)
    good=ack_for(s);pending=[good,good,replace(good,sequence=2,canonical_epoch=0),
        replace(good,sequence=3,owner_incarnation=s.t0-1),
        replace(good,sequence=4,contract_digest='other')]
    s.consumer_ack_source=lambda:tuple(pending)
    s._drain_consumer_acks(s.clock());pending.clear()
    assert s._display_status(s.sessions[0],1,s.clock())==(True,False)
    assert s.ack_counts=={'accepted':1,'duplicate':1,'wrong_identity':3}
    pending.append(replace(good,sequence=5,valid_visible_frontier=0,observed_perf=s.clock()+.1))
    s.clock.sleep(.2);s._drain_consumer_acks(s.clock());pending.clear()
    assert s._display_status(s.sessions[0],1,s.clock())==(True,False)
    assert len(s._first_visible)==1
    s.close()


def test_ack_after_decision_cannot_be_read_back_into_earlier_choice():
    s=old_owner('fine');s.clock.sleep(3.9)
    a=ack_for(s,observed=s.t0+4.1)
    pending=[a];s.consumer_ack_source=lambda:tuple(pending)
    s._drain_consumer_acks(s.clock());pending.clear()
    assert not s._first_visible and len(s._pending_acks)==1
    s.clock.sleep(.3);s._drain_consumer_acks(s.clock())
    assert s._display_status(s.sessions[0],1,s.clock())==(False,True)
    # The record stays late even when it is finally observed by the owner.
    assert s._first_visible[0,1]==s.t0+4.1
    s.close()


def test_complete_frontier_required_and_resume_incarnation_isolated():
    s=old_owner('fine');s.clock.sleep(2.1)
    pending=[ack_for(s,frontier=31999)]
    s.consumer_ack_source=lambda:tuple(pending)
    s._drain_consumer_acks(s.clock());pending.clear()
    assert not s._first_visible
    pending.append(ack_for(s,sequence=2,frontier=32000))
    s._drain_consumer_acks(s.clock());pending.clear()
    assert list(s._first_visible)==[(0,1)]
    s.close()


def test_completed_row_not_counted_as_pending_while_worker_still_leased():
    s=old_owner('fine');s.clock.sleep(2.1);s._dispatch()
    name=next(n for n in s.inflight if n=='p');worker,ids=s.inflight[name]
    before=s._features(s.sessions[0],s.clock())
    assert before.candidate_eta is not None
    first=next(i for i in ids if s.jobs[i]['session_id']==0)
    s._event('executor-complete',job_id=first)
    assert s._features(s.sessions[0],s.clock()).candidate_eta is None
    assert name in s.inflight and first in s.inflight[name][1]
    s.close()


def test_deadline_order_shared_and_aged_work_progresses():
    s=old_owner('fine');s.proposer_order='deadline';s.clock.sleep(2.1)
    zero,one=s.sessions[0],s.sessions[1]
    s._first_visible[0,1]=s.clock()
    assert s._order_proposals([zero,one],s.clock())==[one,zero]
    s.clock.sleep(8.)
    assert s._order_proposals([one,zero],s.clock())==[zero,one]
    s.close()


def v5_owner(mode,wal=None):
    clk=Clock();view=ContinuityView('two_lane',strict_bound=True);pending=[]
    cfg={'policy':'fine_certified','rho':1,'fine_seconds':2,'sample_rate':16000,
        'authority_runtime':{'dtype':'float32','max_new_tokens':1},'proposal_runtime':{'dtype':'float16'},
        'microbatch':2,'timeout_seconds':20,'proposal_barrier':'decoupled','proposal_reconciliation':'lazy',
        'verification_policy':'causal_evidence_choice','journal_sync_mode':'group_ready',
        'display_protocol':'canonical-snapshot-v1','trusted_text_binding':True,
        'publish_canonical_display':True,'evidence_type':'cpu_fixture_only',
        'ces_study':{'method':mode,'calibration':deepcopy(CAL),'fault_plan':{},'donors':[],
            'display_slo':2.,'commit_slo':8.,'wait_cap':0.}}
    def render(job,tokens):return list(tokens),str(tokens[0])
    class Worker(EvidenceFake):
        def poll(self):
            rows=super().poll()
            for r in rows or []:r.update(state_tokens=list(r['token_ids']),text=str(r['token_ids'][0]))
            return rows
    def emit(event):
        row=view.consume(event,clk())
        if row:pending.append(ConsumerAck(len(view.records),view.epoch,view.contract,row['session_id'],
            row['canonical_epoch'],row['canonical_version'],row['valid_visible_frontier'],
            row['certified_frontier'],clk()))
    def drain():
        rows=tuple(pending);pending.clear();return rows
    return CESScheduler(sessions=[{'session_id':i,'source_id':str(i),
        'audio':np.zeros(96000,dtype='<f4').tobytes(),'offset':i*.05,'language':'English'} for i in range(2)],
        contract=cfg,executors={'proposal':[Worker('p',clk)],'authority':[Worker('a',clk)]},
        clock=clk,sleep=clk.sleep,emit=emit,durable_journal_path=wal,trusted_render=render,
        consumer_ack_source=drain)


@pytest.mark.parametrize('mode',['risk_cost','progress','progress_joint'])
def test_v5_actual_owner_predicates_d1_and_wal_resume(mode,tmp_path):
    path=tmp_path/'history.wal';s=v5_owner(mode,path)
    result=s.run()
    assert result['certified_commits']==6 and result['fine_window_accounting_complete']
    assert s.ack_counts['accepted']>0
    assert all(e['certificate_consumed'] for e in s.events if e['kind']=='commit')
    s.close();resumed=v5_owner(mode,path)
    assert all(x.done for x in resumed.sessions.values()) and not resumed.jobs
    resumed.close()


def test_v5_requires_real_ack_provider():
    old=old_owner('fine')
    cfg=deepcopy(old.contract);cfg['ces_study']['method']='progress';old.close()
    with pytest.raises(ValueError,match='actual Consumer'):
        CESScheduler(contract=cfg)


def test_old_parent_still_fails_before_install_with_progress_mode():
    s=v5_owner('progress');s.clock.sleep(2.1);s._dispatch();s.clock.sleep(.01)
    worker=s.executors['authority'][0];original=worker.poll
    def wrong_parent():
        rows=original()
        for row in rows or []:s.jobs[row['job_id']]['parent']=-1
        return rows
    worker.poll=wrong_parent
    with pytest.raises(AssertionError,match='stale result'):s._receive()
    assert all(x.state.checkpoint_id==0 for x in s.sessions.values())
    s.close()


def test_recent_rejection_is_not_an_everlasting_parent_attribute():
    s=v5_owner('progress');s.clock.sleep(2.1);target=s.sessions[0]
    s.last_reject[0]=True
    s.reject_observations[0]={'rejected':True,'parent':target.state.checkpoint_id,
        'observed_perf':s.clock(),'job_id':'cpu-observation','end_window':1}
    assert s._features(target,s.clock()).previous_reject
    s.clock.sleep(8.1)
    assert not s._features(target,s.clock()).previous_reject
    assert s._features(target,s.clock()).reject_age_seconds==pytest.approx(8.1)
    s.reject_observations[0]['observed_perf']=s.clock()
    s.reject_observations[0]['parent']=target.state.checkpoint_id-2
    assert not s._features(target,s.clock()).previous_reject
    s.close()


def test_impossible_unreleased_consumer_frontier_fails_closed():
    s=old_owner('fine');s.clock.sleep(2.1)
    s.consumer_ack_source=lambda:(ack_for(s,frontier=64000),)
    with pytest.raises(ValueError,match='precedes audio release'):
        s._drain_consumer_acks(s.clock())
    assert not any(e['kind']=='commit' for e in s.events)
    s.close()


def test_v5_same_input_repeated_legal_cpu_histories():
    histories=[]
    for _ in range(2):
        s=v5_owner('progress');s.run()
        histories.append([(e['session_id'],e['version'],e['next_prompt_tokens'])
            for e in s.events if e['kind']=='commit'])
        s.close()
    assert histories[0]==histories[1]
