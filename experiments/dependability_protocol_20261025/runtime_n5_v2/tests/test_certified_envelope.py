"""Production scheduler wiring with CPU executors, never GPU evidence."""
from dataclasses import replace
import importlib.util,json
from pathlib import Path
from types import SimpleNamespace
import pytest
from revtrace.live_qwen import fingerprint
from revtrace.certified_display import ConsumerAck
from revtrace.envelope_display import EnvelopeView
from revtrace.certified_envelope import CertifiedEnvelopeScheduler
from revtrace.degradation_state import CreditBook
from revtrace.input_debt_journal import InputJournal,InputJournalError

spec=importlib.util.spec_from_file_location('env_fixture',Path(__file__).with_name('test_live_qwen.py'))
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)

class CPUConsumer:
    def __init__(self,clock):self.clock=clock;self.view=EnvelopeView(policy='two_lane',fine_samples=160,strict_bound=True);self.acks=[];self.rows=[]
    def put(self,e):
        r=self.view.consume(e,self.clock())
        if e['kind']=='run-start':
            self.base=e['t0_perf'];self.contract=e['contract_digest']
            self.acks.append(dict(kind='stream-start-applied',owner_incarnation=self.base,contract_digest=self.contract))
        if r:
            r['observed_perf']=self.clock();self.rows.append(r)
            self.acks.append(ConsumerAck(len(self.rows),self.base,self.contract,r['session_id'],r['canonical_epoch'],
                r['canonical_version'],r['valid_visible_frontier'],r['certified_frontier'],self.clock(),r['envelope_mode']))
    def drain_acks(self):r,self.acks=self.acks,[];return r

def build(tmp,*,method='cde_full',pdelay=.025,adelay=.015,count=3,clock=None,offsets=None,emit_hook=None):
    clock=clock or f.Clock();consumer=CPUConsumer(clock);rho=1 if method=='fine_fair' else 3
    cfg=dict(policy='coarse' if rho==3 else 'fine_certified',rho=rho,fine_seconds=.01,sample_rate=16000,
        authority_runtime={'dtype':'float32'},proposal_runtime={'dtype':'float16'},microbatch=3,
        timeout_seconds=4,proposal_barrier='decoupled',proposal_reconciliation='lazy',
        verification_policy='canonical_generate',trusted_text_binding=True,retain_verified_private_prefix=True,
        capture_worker_records=True,display_protocol='canonical-snapshot-v1',manifest_sha256='a'*64,
        evidence_type='cpu_simulated_orchestration_only',async_implementation='standard' if method.startswith('standard') else 'revtrace',
        episode_origin_perf=100.,envelope=dict(method=method,budget_audio_seconds=.06,warning_age=.04,critical_age=.08,
            clear_age=.02,display_slo=.02,queue_threshold=1,reject_new_after_seconds=.12))
    class BoundFake(f.Fake):
        def poll(self):
            rows=super().poll()
            if rows:
                for r in rows:
                    r['token_ids']=list(r['state_tokens']);r['text']=str(r['token_ids'][0])
            return rows
    workers={'proposal':[BoundFake('p',clock,pdelay)],'authority':[BoundFake('a',clock,adelay)]}
    def render(j,z):return list(z),str(z[0])
    events=[]
    def emit(e):
        events.append(e);consumer.put(e)
        if emit_hook:emit_hook(e)
    s=CertifiedEnvelopeScheduler(consumer=consumer,input_journal_path=tmp/'input.wal',
        sessions=[dict(session_id=sid,audio=bytes(1920*4),source_id=str(sid),language='English',offset=(offsets or [0]*count)[sid]) for sid in range(count)],
        contract=cfg,executors=workers,emit=emit,clock=clock,sleep=clock.sleep,trusted_render=render,
        durable_journal_path=tmp/'canonical.wal')
    return s,consumer,events

@pytest.mark.parametrize('method',sorted(CertifiedEnvelopeScheduler.METHODS))
def test_all_safe_methods_conserve_actual_accepted_input_and_account_all_offered_windows(tmp_path,method):
    s,c,events=build(tmp_path,method=method);r=s.run()
    assert r['fine_window_accounting_complete']
    assert sum(r['fine_window_outcomes'].values())==36
    assert all(x.state.audio_frontier_window<=s.book.session(x.sid).accepted for x in s.sessions.values())
    assert all(e['job']['audio_end_sample']<=next(x['to_sample'] for x in reversed(events[:events.index(e)]) if x['kind']=='input-ack' and x['session_id']==e['job']['session_id'])
        for e in events if e['kind']=='worker-record')
    assert all(x['valid_visible_frontier']==x['certified_frontier'] for x in c.rows if x['envelope_mode'] in ['RECOVERY','CERTIFIED-ONLY'])
    assert all(x.state.prompt_tokens[-1]==12 for x in s.sessions.values() if x.state.prompt_tokens)
    assert any(e['kind']=='input-snapshot-synchronized' for e in events)
    s.close()

def test_failure_after_input_ack_recovers_exact_debt_and_original_clock(tmp_path):
    class Kill(RuntimeError):pass
    first={'scheduler':None}
    def kill(e):
        if e['kind']=='input-ack':raise Kill('CPU fixture after actual input synchronization')
    s,c,e=build(tmp_path,emit_hook=kill)
    with pytest.raises(Kill):s.run()
    A={sid:v.accepted for sid,v in s.book.sessions.items()};assert max(A.values())>0
    s.close();clock=s.clock;clock.sleep(.08)
    resumed,c,events=build(tmp_path,clock=clock)
    assert {sid:v.accepted for sid,v in resumed.book.sessions.items()}==A
    assert resumed.origin==100. and resumed.owner_epoch==2
    result=resumed.run();assert result['fine_window_accounting_complete']
    assert all(e['audio_ready_perf']<resumed.t0 for e in events if e['kind']=='enqueue' and e['audio_end_sample']==160)
    assert all(e['audio_start_sample']<e['audio_end_sample'] for e in events if e['kind']=='enqueue')
    resumed.close()

def test_rejection_is_persistent_and_never_moves_a_canonical_frontier(tmp_path):
    s,c,e=build(tmp_path,adelay=.3,count=5);r=s.run()
    rejected=[sid for sid,b in s.book.sessions.items() if b.rejected]
    assert rejected and all(s.sessions[sid].state.audio_frontier_window==0 for sid in rejected)
    s.close();again,_,_=build(tmp_path,adelay=.3,count=5,clock=s.clock)
    assert all(again.book.session(sid).rejected for sid in rejected)
    r=again.run();assert all(again.sessions[sid].state.audio_frontier_window==0 for sid in rejected)
    again.close()

def test_snapshot_atomicity_restores_reservations_after_eof_and_rejection(tmp_path):
    s,_,_=build(tmp_path,count=3,adelay=.08);r=s.run();last=s.input_journal.snapshot
    assert last and sum(v['reserved']-v['certified'] for v in last['sessions'].values())<=last['budget']
    s.close()
    with InputJournal(tmp_path/'input.wal',manifest_sha256='a'*64,
        policy_sha256=fingerprint({'envelope':s.options,'manifest':'a'*64,'origin_perf':100.,'rho':3,'sample_rate':16000})) as j:
        assert j.snapshot==last

def test_changed_immutable_accepted_input_fails_closed(tmp_path):
    s,_,_=build(tmp_path);s.run();s.close()
    # Change the last authoritative input-prefix binding, retaining a valid
    # frame checksum through the trusted fixture API; source bytes remain zero.
    p=tmp_path/'input.wal';ctx=s.input_journal.context
    with InputJournal(p,**ctx) as j:
        snap=json.loads(json.dumps(j.snapshot));key=next(k for k,v in snap['sessions'].items() if v['accepted'])
        snap['sessions'][key]['accepted_prefix_sha256']='f'*64
        with pytest.raises(InputJournalError):j.checkpoint(snap)

def test_actual_feedback_and_lease_features_change_the_full_rule(tmp_path):
    s,_,_=build(tmp_path)
    p=dict(oldest_uncertified_age=.09,unseen_accepted_audio_samples=160,accepted_debt_samples=320,
        reserved_debt_samples=320,actual_authority_ready_queue=0,actual_private_ready_queue=1,
        authority_physical_leases=1,private_physical_leases=0,pending_offered_audio_samples=0)
    assert s._caught_up(s._recovered_frontiers) is False
    s._stream_applied=True;s.mode=__import__('revtrace.degradation_state',fromlist=['Mode']).Mode.NORMAL
    assert s._choose_mode(p).value=='CERTIFIED-ONLY'
    assert s._choose_mode(dict(p,unseen_accepted_audio_samples=0)).value!='CERTIFIED-ONLY'
    assert s._choose_mode(dict(p,authority_physical_leases=0)).value!='CERTIFIED-ONLY'
    s.close()
