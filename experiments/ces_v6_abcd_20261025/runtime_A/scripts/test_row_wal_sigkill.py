"""Real Linux SIGKILL + original WAL, synthetic row/model fixture only."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from revtrace.live_qwen import LiveQwenScheduler
from revtrace.durable_journal import DurableCommitJournal
from test_live_qwen import Clock,Fake
import numpy as np

class Split(Fake):
    row_delivery=True
    def __init__(self,name,clock):super().__init__(name,clock);self.stage=0;self.batch_drained=False
    def submit(self,jobs):super().submit(jobs);self.stage=0;self.batch_drained=False
    def poll(self):
        if self.jobs is None:return None
        elapsed=self.clock()-self.started
        if self.stage==0 and elapsed>=.001:which=self.jobs[:1];self.stage=1
        elif self.stage==1 and elapsed>=.015:which=self.jobs[1:];self.stage=2
        elif self.stage==2 and elapsed>=.02:
            self.jobs=None;self.batch_drained=True;return []
        else:return None
        return [{'job_id':j['job_id'],'runtime_digest':j['runtime_digest'],'prefix_audio_sha256':j['prefix_audio_sha256'],
          'started_perf':self.started,'completed_perf':self.clock(),'generated_tokens':1,'hit_token_limit':False,
          'text':str(j['end_window']),'token_ids':[j['end_window']],
          'state_tokens':[j['end_window']+(0 if j['role']=='authority' else 999)]} for j in which]

def make(path,emit=lambda e:None):
    clock=Clock();cfg={'policy':'coarse','rho':3,'fine_seconds':.01,'sample_rate':16000,
      'authority_runtime':{'dtype':'float32'},'proposal_runtime':{'dtype':'float16'},
      'microbatch':2,'timeout_seconds':3,'proposal_barrier':'decoupled','proposal_reconciliation':'lazy',
      'journal_sync_mode':'group_ready','publish_canonical_display':True,'evidence_type':'CPU_synthetic_row_process_kill_fixture'}
    ss=[{'session_id':i,'audio':np.zeros(960,dtype='<f4').tobytes(),'source_id':str(i),'language':'English','offset':0.} for i in range(2)]
    return LiveQwenScheduler(sessions=ss,contract=cfg,executors={'proposal':[Split('p',clock)],'authority':[Split('a',clock)]},
      clock=clock,sleep=clock.sleep,emit=emit,durable_journal_path=path)

def child(path,point):
    original=DurableCommitJournal.commit_transitions
    if point=='before-WAL':
        def before(self,*a,**kw):os.kill(os.getpid(),signal.SIGKILL)
        DurableCommitJournal.commit_transitions=before
    def emit(e):
        if point=='after-WAL-before-publication' and e['kind']=='commit':os.kill(os.getpid(),signal.SIGKILL)
        if point=='after-publication' and e['kind']=='canonical-display':os.kill(os.getpid(),signal.SIGKILL)
    s=make(path,emit);s.run();raise RuntimeError('fault point not reached')

def parent(out):
    assert sys.platform.startswith('linux'),'This test is Linux process-kill evidence only'
    out.mkdir(exist_ok=False);cases=[]
    for point in ['before-WAL','after-WAL-before-publication','after-publication']:
        p=out/(point+'.wal');cmd=[sys.executable,str(Path(__file__).resolve()),'--child',str(p),point]
        q=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
        (out/(point+'.log')).write_text(q.stdout+'\n'+q.stderr)
        assert q.returncode==-signal.SIGKILL,(point,q.returncode)
        s=make(p);states=[s.sessions[i].state for i in range(2)]
        expected=[0,0] if point=='before-WAL' else [480,0]
        assert [st.audio_frontier_window for st in states]==expected
        assert all(st.contract_epoch==2 for st in states)
        result=s.run()
        assert not s.inflight and all(st['state']['audio_frontier_window']==960 for st in result['final_states'])
        ids=[tid for ss in s.sessions.values() for tid in ss.state.committed_segment_ids]
        assert len(ids)==len(set(ids))==4
        s.close()
        cases.append({'point':point,'exit_code':q.returncode,'recovered_frontiers':expected,
          'completed_frontiers':[960,960],'unique_installs':4,'duplicate_installs':0,
          'not_a_GPU_or_host_power_failure_test':True})
    record={'status':'PASS_LINUX_ROW_WAL_SIGKILL_CPU_FIXTURE','cases':cases,'real_original_journal':True,
      'synthetic_model_rows_not_GPU':True,'new_model_calls':0,
      'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'SUMMARY.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))

if __name__=='__main__':
    if sys.argv[1]=='--child':child(Path(sys.argv[2]),sys.argv[3])
    else:parent(Path(sys.argv[1]))
