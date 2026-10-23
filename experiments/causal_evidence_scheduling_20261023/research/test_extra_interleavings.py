"""CPU-only actual owner mode switches, no new GPU or performance evidence."""
from pathlib import Path
import sys
import pytest
W=Path(__file__).resolve().parent;S=W/'runtime';sys.path[:0]=[str(S/'src'),str(S/'tests')]
from test_ces import owner

@pytest.mark.parametrize('method',['ready_any','cost_gate','cost','causal_only','ces'])
def test_paid_worker_backlog_causes_real_G_to_V_owner_switch(method,tmp_path):
 s=owner(method,tmp_path/'state.wal');s.executors['proposal'][0].delay=.001;s.executors['authority'][0].delay=3.1
 result=s.run()
 ops={j['ces_operation'] for j in s.jobs.values() if j['role']=='authority'}
 assert ops=={'generate','verify'}
 assert result['certified_commits']==6 and result['fine_window_accounting_complete']
 assert all(v.state.audio_frontier_window==96000 for v in s.sessions.values())
 s.close()
 resumed=owner(method,tmp_path/'state.wal');assert all(v.done for v in resumed.sessions.values());resumed.close()

def test_wrong_operation_in_actual_completed_owner_result_cannot_install(tmp_path):
 s=owner('ready_any',tmp_path/'state.wal');s.clock.sleep(2.1);s._dispatch();s.clock.sleep(.01)
 w=s.executors['authority'][0];original=w.poll
 def mismatch():
  rows=original()
  for r in rows or []:r['ces_operation']='verify' if r['ces_operation']=='generate' else 'generate'
  return rows
 w.poll=mismatch;s._receive()
 with pytest.raises(ValueError,match='operation binding'):s._commit_ready()
 assert all(v.state.checkpoint_id==0 for v in s.sessions.values());s.close()
