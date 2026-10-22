"""Deterministic CPU controls; no GPU timing or recognition-quality claims."""
import importlib.util
import math
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('fixture_live', Path(__file__).with_name('test_live_qwen.py'))
fixture=importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)


def run_case(mode, *, pdelay=.025, adelay=.001, count=2, duration=.24,
             barrier='decoupled', path=None):
    base=fixture.build(barrier=barrier, count=count)
    config=dict(base.contract, proposal_reconciliation=mode,
                publish_canonical_display=True, timeout_seconds=10,
                durability_mode='wal' if path else 'volatile')
    import numpy as np
    specs=[{'session_id':ss.sid,'audio':np.zeros(round(duration*16000),dtype='<f4').tobytes(),
            'source_id':ss.source_id,'language':ss.language,'offset':ss.offset}
           for ss in base.sessions.values()]
    s=fixture.LiveQwenScheduler(sessions=specs,contract=config,executors=base.executors,
        emit=lambda e:None,clock=base.clock,sleep=base.sleep,durable_journal_path=path)
    s.executors['proposal'][0].delay=pdelay
    s.executors['authority'][0].delay=adelay
    result=s.run()
    return s,result


def history(s):
    return [(e['session_id'],e['audio_start_sample'],e['audio_end_sample'],
             e['segment_tokens'],e['next_prompt_tokens'])
            for e in s.events if e['kind']=='commit']


def obsolete_publications(s):
    f={sid:0 for sid in s.sessions}; n=0
    for e in s.events:
        if e['kind']=='commit': f[e['session_id']]=e['audio_end_sample']
        elif e['kind']=='display': n+=s.jobs[e['job_id']]['audio_end_sample']<=f[e['session_id']]
    return n


@pytest.mark.parametrize('pdelay,adelay',[(.001,.001),(.025,.001),(.001,.06),(.04,.009)])
@pytest.mark.parametrize('count',[1,2,5])
def test_lazy_matches_legal_authority_oracle_and_accounts_every_window(pdelay,adelay,count):
    old,_=run_case('legacy',pdelay=pdelay,adelay=adelay,count=count)
    new,r=run_case('lazy',pdelay=pdelay,adelay=adelay,count=count)
    assert history(old)==history(new)
    assert obsolete_publications(new)==0
    assert r['fine_window_accounting_complete']
    assert sum(r['fine_window_outcomes'].values())==count*24
    assert all(s.state.audio_frontier_window==3840 for s in new.sessions.values())
    for e in new.events:
        if e['kind']=='enqueue' and e['role']=='proposal':
            assert e['audio_start_sample']<e['audio_end_sample']


def test_original_witness_is_nonvacuous_and_repair_skips_real_work():
    old,_=run_case('legacy',count=1)
    new,r=run_case('lazy',count=1)
    assert obsolete_publications(old)>0
    assert obsolete_publications(new)==0
    assert any(e['kind']=='proposal-rebase' for e in new.events)
    assert r['fine_window_outcomes'].get('covered-without-dispatch',0)>0
    dispatch=lambda s:sum(e['kind']=='enqueue' and e['role']=='proposal' for e in s.events)
    assert dispatch(new)<dispatch(old)


def test_old_parent_ahead_target_is_allowed_with_stalled_authority():
    s,r=run_case('lazy',pdelay=.001,adelay=.09)
    assert r['display_events']==48
    assert not any(e['kind']=='proposal-obsolete' for e in s.events)


def test_partial_final_window_retains_full_audio_accounting():
    s,r=run_case('lazy',duration=.237)
    assert all(x.state.audio_frontier_window==3792 for x in s.sessions.values())
    assert sum(r['fine_window_outcomes'].values())==48


def test_safe_barrier_is_unchanged():
    a,ra=run_case('legacy',barrier='segment')
    b,rb=run_case('lazy',barrier='segment')
    assert history(a)==history(b)
    assert ra['display_events']==rb['display_events']==48


def test_canonical_publication_is_explicit_and_shared_by_controls():
    for mode in ['legacy','lazy']:
        s,r=run_case(mode)
        assert r['canonical_display_events']==r['certified_commits']
        assert any(e['kind']=='canonical-display' and not e['provisional'] for e in s.events)


def test_lazy_durable_history_reopens_without_duplicate_transitions(tmp_path):
    path=tmp_path/'lazy.wal'
    s,r=run_case('lazy',path=path)
    before=[(x.sid,x.state.checkpoint_id,x.state.prompt_tokens) for x in s.sessions.values()]
    s.close()
    reopened,again=run_case('lazy',path=path)
    assert again['certified_commits']==0
    assert [(x.sid,x.state.checkpoint_id,x.state.prompt_tokens) for x in reopened.sessions.values()]==before
    assert all(x.state.contract_epoch==2 for x in reopened.sessions.values())
    reopened.close()


def test_declared_modes_and_grouped_boundary_fail_closed():
    s=fixture.build(); config=dict(s.contract,proposal_reconciliation='invalid')
    with pytest.raises(ValueError,match='unknown'):
        fixture.LiveQwenScheduler(sessions=[],contract=config,executors=s.executors,emit=lambda e:None)
    config=dict(s.contract,proposal_reconciliation='lazy',verification_policy='grouped_replay')
    with pytest.raises(ValueError,match='independent'):
        fixture.LiveQwenScheduler(sessions=[],contract=config,executors=s.executors,emit=lambda e:None)
