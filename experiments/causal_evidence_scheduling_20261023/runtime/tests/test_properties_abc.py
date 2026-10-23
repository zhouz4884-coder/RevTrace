"""Deterministic CPU interleavings, not GPU timing or natural incidence."""
import importlib.util
from pathlib import Path
import pytest
from revtrace.live_qwen import LiveQwenScheduler
spec=importlib.util.spec_from_file_location('abc_fixture',Path(__file__).with_name('test_live_qwen.py'))
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)

def build(*,rho=3,proposal=.001,authority=.001,barrier='decoupled',durable=None,mode='lazy',instrument=True):
    ref=f.build(rho=rho,barrier=barrier,count=2)
    config=dict(ref.contract,proposal_reconciliation=mode,display_protocol='canonical-snapshot-v1',
                publish_canonical_display=True,blocking_instrumentation=instrument,timeout_seconds=10,
                durability_mode='wal' if durable else 'volatile')
    clock=f.Clock()
    sessions=[{'session_id':s.sid,'audio':s.audio,'source_id':s.source_id,'language':s.language,'offset':s.offset}
              for s in ref.sessions.values()]
    s=LiveQwenScheduler(sessions=sessions,contract=config,executors={'proposal':[f.Fake('p',clock,proposal)],
        'authority':[f.Fake('a',clock,authority)]},clock=clock,sleep=clock.sleep,emit=lambda e:None,durable_journal_path=durable)
    return s

@pytest.mark.parametrize('proposal,authority',[(.001,.05),(.025,.001),(.004,.01)])
@pytest.mark.parametrize('rho',[1,3])
@pytest.mark.parametrize('barrier',['segment','decoupled'])
def test_abc_and_same_input_repeated_oracle(proposal,authority,rho,barrier):
    histories=[]
    for _ in range(2):
        s=build(rho=rho,proposal=proposal,authority=authority,barrier=barrier)
        out=s.run();frontier={sid:0 for sid in s.sessions};commits={};canonical={};ever={sid:0 for sid in s.sessions};revision={sid:0 for sid in s.sessions}
        for e in s.events:
            sid=e.get('session_id')
            if e['kind']=='commit':
                assert e['audio_start_sample']==frontier[sid]
                frontier[sid]=e['audio_end_sample'];commits[sid,e['version']]=e
            if e['kind']=='display':assert e['audio_end_sample']>frontier[sid]
            if e['kind'] in ['display','canonical-display']:
                assert e['display_revision']>revision[sid];revision[sid]=e['display_revision']
                assert e['display_ever_frontier']>=ever[sid];ever[sid]=e['display_ever_frontier']
            if e['kind']=='canonical-display':
                assert e['transaction_id']==commits[sid,e['version']]['segment_id']
                assert e['text']==str(commits[sid,e['version']]['audio_end_sample']//160)
                canonical[sid,e['version']]=e
        assert set(canonical)==set(commits)
        assert out['fine_window_accounting_complete'] and len(s.window_outcomes)==12
        # Legal oracle: deterministic fake authority selects target-window token.
        for ss in s.sessions.values():
            assert ss.state.prompt_tokens==(6,) and ss.state.audio_frontier_window==960
            assert ss.state.stable_token_segments==tuple((w,) for w in range(rho,7,rho))
        histories.append([(k,v.state.prompt_tokens,v.state.audio_frontier_window,v.state.stable_token_segments) for k,v in s.sessions.items()])
        s.close()
    assert histories[0]==histories[1]

def test_correction_even_if_private_display_is_further():
    s=build(proposal=.001,authority=.05);s.run()
    corrections=[e for e in s.events if e['kind']=='canonical-display']
    assert any(e['audio_rollback_samples']>0 for e in corrections)
    assert all(e['canonical_snapshot']==e['text'] for e in corrections)
    assert all(e['protocol']=='versioned-full-snapshot-no-token-audio-patch' for e in corrections)

def test_legacy_has_obsolete_publications_but_lazy_does_not():
    counts=[]
    for mode in ['legacy','lazy']:
        s=build(proposal=.025,authority=.001,mode=mode);s.run();frontier={sid:0 for sid in s.sessions};n=0
        for e in s.events:
            if e['kind']=='commit':frontier[e['session_id']]=e['audio_end_sample']
            elif e['kind']=='display':n+=e['audio_end_sample']<=frontier[e['session_id']]
        counts.append(n)
    assert counts[0]>0 and counts[1]==0

def test_old_generation_completion_is_retired_without_publication():
    s=build(proposal=.01);s._dispatch();s.clock.sleep(.011);s._dispatch()
    # Isolated deterministic stale generation, not a production prevalence claim.
    for ss in s.sessions.values():ss.branch_generation+=1
    s.clock.sleep(.02);s._receive()
    assert any(e['kind']=='proposal-obsolete' and e['invalid_generation'] for e in s.events)
    assert not any(e['kind']=='display' for e in s.events)

def test_wal_failure_cannot_publish_certified_snapshot(tmp_path):
    s=build(durable=tmp_path/'failure.wal')
    def fail(_frame):raise OSError('fixture fsync/write failure')
    s._journal._write_frame=fail
    with pytest.raises(OSError):s.run()
    assert not any(e['kind'] in ['commit','canonical-display'] for e in s.events)
    assert all(ss.state.checkpoint_id==0 for ss in s.sessions.values());s.close()

def test_recovery_republishes_latest_real_canonical_text(tmp_path):
    path=tmp_path/'restore.wal';s=build(durable=path);s.run();s.close()
    recovered=build(durable=path)
    displays=[e for e in recovered.events if e['kind']=='canonical-display']
    assert len(displays)==2 and all(e['recovered'] and e['text']=='6' for e in displays)
    assert recovered.run()['certified_commits']==0;recovered.close()

def test_wait_bits_keep_self_and_capacity_overlap():
    s=build(rho=1,authority=.05);s.run()
    intervals=[e for e in s.events if e['kind']=='authority-wait-interval']
    assert intervals and any(e['bitmap']['self_inflight'] and e['bitmap']['worker_capacity_occupied'] for e in intervals)
    assert all(e['duration']>0 for e in intervals)
