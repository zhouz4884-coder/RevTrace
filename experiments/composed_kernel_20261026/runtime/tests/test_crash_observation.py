"""CPU observer controls, not a GPU/crash-recovery success claim."""
import json,time
from pathlib import Path
from revtrace.certified_display import RealtimeConsumer

class EchoView:
    def consume(self,e,now):
        if e['kind']=='run-start':return
        return dict(owner_incarnation=1.,contract_digest='x',session_id=0,
            canonical_epoch=1,canonical_version=0,valid_visible_frontier=0,
            certified_frontier=0,observed_perf=now)

def test_completed_observation_is_readable_before_close(tmp_path):
    p=tmp_path/'live.jsonl';c=RealtimeConsumer(tmp_path/'closed.jsonl',view=EchoView(),crash_trace_path=p)
    c.put(dict(kind='run-start',t0_perf=time.perf_counter(),contract_digest='x'))
    c.put(dict(kind='fixture'))
    for _ in range(200):
        if p.exists() and p.stat().st_size:break
        time.sleep(.005)
    live=[json.loads(x) for x in p.read_text().splitlines()]
    assert len(live)==1 and not (tmp_path/'closed.jsonl').exists()
    c.close();closed=[json.loads(x) for x in (tmp_path/'closed.jsonl').read_text().splitlines()]
    assert live==closed and live[0]['valid_visible_frontier']==0

def test_default_observer_does_not_write_crash_trace(tmp_path):
    c=RealtimeConsumer(tmp_path/'closed.jsonl',view=EchoView())
    c.put(dict(kind='run-start',t0_perf=time.perf_counter(),contract_digest='x'));c.put(dict(kind='fixture'));c.close()
    assert [p.name for p in tmp_path.iterdir()]==['closed.jsonl']
