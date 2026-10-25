"""CPU single-owner/physical-drain fixture, not GPU serving or neural evidence."""
import pytest
from test_live_qwen import Fake,build

class Partial(Fake):
    row_delivery=True
    def __init__(self,name,clock):
        super().__init__(name,clock);self.batch_drained=False;self.sent=False;self.drains=[];self.bad=False
    def submit(self,jobs):
        super().submit(jobs);self.batch_drained=False;self.sent=False
    def poll(self):
        if self.jobs is None:return None
        if not self.sent and self.clock()>=self.started+.001:
            jobs=self.jobs
            self.sent=True
            return [{'job_id':'foreign' if self.bad else j['job_id'],'runtime_digest':j['runtime_digest'],
             'prefix_audio_sha256':j['prefix_audio_sha256'],'started_perf':self.started,
             'completed_perf':self.clock(),'generated_tokens':1,'hit_token_limit':False,
             'text':str(j['end_window']),'token_ids':[j['end_window']],
             'state_tokens':[j['end_window']+(0 if j['role']=='authority' else 999)]} for j in jobs]
        if self.sent and self.clock()>=self.started+.02:
            self.jobs=None;self.batch_drained=True;self.drains.append(self.clock());return []
        return None

def test_logical_finish_still_drains_all_physical_work():
    s=build(rho=1,count=1,barrier='decoupled')
    p,a=Partial('p',s.clock),Partial('a',s.clock)
    s.executors={'proposal':[p],'authority':[a]}
    result=s.run()
    assert not s.inflight and p.drains and a.drains
    assert s.clock()>=max(p.drains+a.drains)
    assert result['certified_commits']==6
    assert all(ss.state.audio_frontier_window==960 for ss in s.sessions.values())

def test_partial_outside_leased_job_set_is_rejected():
    s=build(rho=1,count=1,barrier='decoupled');p,a=Partial('p',s.clock),Partial('a',s.clock);p.bad=True
    s.executors={'proposal':[p],'authority':[a]}
    with pytest.raises(AssertionError,match='outside leased'):s.run()
    assert not any(e['kind']=='commit' for e in s.events)

def test_early_publication_precedes_physical_reuse_without_reusing_it():
    s=build(rho=1,count=1,barrier='decoupled');p,a=Partial('p',s.clock),Partial('a',s.clock)
    s.executors={'proposal':[p],'authority':[a]};s.run()
    first=min(e['installed']+s.t0 for e in s.events if e['kind']=='commit')
    assert first<a.drains[0]
    assert len(a.drains)==6 and len(p.drains)==6
