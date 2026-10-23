"""Actual Linux process-kill/WAL, CPU fake model. Not a GPU recovery result."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys
S=Path(sys.argv[1]);sys.path[:0]=[str(S/'src'),str(S/'tests')]
from test_ces import owner
from revtrace.durable_journal import DurableCommitJournal
def make(mode,path):
 s=owner(mode,path)
 # Match the same fixed manifest offsets in child/recovery: the test owner has
 # offsets0,.05, so only the first session is in its first ready group.
 return s
def child(mode,path,point):
 if point=='before-WAL':
  def fail(*a,**kw):os.kill(os.getpid(),signal.SIGKILL)
  DurableCommitJournal.commit_transitions=fail
 s=make(mode,path)
 def event(e):
  if point=='after-WAL-before-publication' and e['kind']=='commit':os.kill(os.getpid(),signal.SIGKILL)
 s.emit=event;s.run();raise RuntimeError('kill boundary not reached')
if len(sys.argv)>2 and sys.argv[2]=='--child':child(sys.argv[3],Path(sys.argv[4]),sys.argv[5])
else:
 D=Path(sys.argv[2]);assert sys.platform.startswith('linux');D.mkdir(exist_ok=False);cases=[]
 for mode in ['strict','ces']:
  for point in ['before-WAL','after-WAL-before-publication']:
   wal=D/(mode+'-'+point+'.wal');q=subprocess.run([sys.executable,str(Path(__file__)),str(S),'--child',mode,str(wal),point],capture_output=True,text=True)
   (D/(mode+'-'+point+'.log')).write_text(q.stdout+'\n'+q.stderr);assert q.returncode==-signal.SIGKILL,q.returncode
   s=make(mode,wal);before=[v.state.audio_frontier_window for v in s.sessions.values()]
   assert before==([0,0] if point=='before-WAL' else [32000,0]),before
   assert all(v.state.contract_epoch==2 for v in s.sessions.values());r=s.run()
   assert all(v.state.audio_frontier_window==96000 for v in s.sessions.values())
   ids=[x for v in s.sessions.values() for x in v.state.committed_segment_ids];assert len(ids)==len(set(ids))==6
   s.close();cases.append({'mode':mode,'point':point,'exit_code':q.returncode,'recovered_frontiers':before,'unique_installs':6,'duplicates':0})
 (D/'SUMMARY.json').write_text(json.dumps({'status':'PASS_CES_CPU_SIGKILL_WAL','cases':cases,'new_GPU_calls':0,'synthetic_model_only':True,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
 print(json.dumps(cases))
