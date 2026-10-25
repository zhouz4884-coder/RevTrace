"""Telemetry-off preserves correctness rules; not an optimizer."""
import importlib.util
from pathlib import Path
from revtrace.live_qwen import LiveQwenScheduler
spec=importlib.util.spec_from_file_location('diag_fixture',Path(__file__).with_name('test_live_qwen.py'))
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
def test_full_hook_switch_retains_same_canonical_and_real_publications(tmp_path):
    values=[]
    for enabled in [False,True]:
        ref=f.build(count=1);clock=f.Clock();s0=ref.sessions[0]
        cfg=dict(ref.contract,diagnostic_lifecycle=enabled,blocking_instrumentation=enabled,
            proposal_reconciliation='lazy',display_protocol='canonical-snapshot-v1',publish_canonical_display=True,
            durability_mode='wal')
        s=LiveQwenScheduler(sessions=[{'session_id':0,'audio':s0.audio,'source_id':'0','language':'English','offset':0.}],
            contract=cfg,clock=clock,sleep=clock.sleep,emit=lambda e:None,
            executors={'proposal':[f.Fake('p',clock)],'authority':[f.Fake('a',clock)]},
            durable_journal_path=tmp_path/f'{enabled}.wal')
        result=s.run();values.append(s.sessions[0].state.prompt_tokens)
        assert result['canonical_display_events']==2
        assert any(e['kind']=='wal-owner-start' for e in s.events)==enabled
        assert all(('eligible_perf' in e)==enabled for e in s.events if e['kind']=='enqueue')
        assert not any(e['kind']=='wal-physical-timing' for e in s.events)
        if enabled:assert any(e['kind']=='wal-host-clock-fixture' for e in s.events)
        s.close()
    assert values[0]==values[1]
