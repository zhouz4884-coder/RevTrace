"""Bounded real online pilot only. Never launches the formal matrix."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
B=Path(sys.argv[1]);P=B/'projects/revtrace_online_admission_20261022';S=P/'pilot_sdk_v2';O=B/'results/revtrace/online_admission_20261022';D=O/'pilot_v2';D.mkdir(exist_ok=False)
code=json.loads((S/'SOURCE_MANIFEST.json').read_text())['code_commit']
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert '153 passed' in (O/'CPU_LINUX_v2.log').read_text()
for r in json.loads((S/'SOURCE_MANIFEST.json').read_text())['files']:assert sha(S/r['path'])==r['sha256']
weights=[{'file':p.name,'sha256':sha(p)} for p in sorted((B/'models/Qwen3-ASR-1.7B').glob('*.safetensors'))]
matrix=[{'method':m,'traffic':t} for t in ['clean','F2'] for m in ['fine','unprotected','score','strict','dgft','standard']]
(O/'PILOT_v2_FREEZE.json').write_text(json.dumps({'study':'ONLINE-ADMISSION-PILOT-v2','code_commit':code,'matrix':matrix,'weights':weights,'manifest_sha256':sha(O/'PILOT_MANIFEST.json'),'donors_sha256':sha(P/'DONORS.json'),'protocol_sha256':sha(P/'PROTOCOL.md'),'CPU_scope':153,'formal_launched':False,'oracle_diagnostic_cost_not_formal_performance':True},indent=2)+'\n')
done=[]
try:
 for r in matrix:
  assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'Another GPU task active; do not interfere'
  name=r['method']+'-'+r['traffic'];out=D/name
  command=[sys.executable,'-u',str(S/'scripts/run_tc_live_qwen.py'),'--model',str(B/'models/Qwen3-ASR-1.7B'),'--manifest',str(O/'PILOT_MANIFEST.json'),'--output',str(out),'--code-commit',code,'--study-id','ONLINE-ADMISSION-PILOT-v2','--sessions','4','--arrival','sync','--trusted-text-binding','--publish-canonical-display','--display-protocol','canonical-snapshot-v1','--consumer-policy','two_lane','--retain-verified-private-prefix','--phase-n-instrumentation','--capture-model-inputs','--online-study-method',r['method'],'--online-traffic',r['traffic'],'--online-donors',str(P/'DONORS.json'),'--online-oracle-diagnostic','--durable-journal-path',str(D/'journals'/(name+'.wal')),'--journal-sync-mode','group_ready']
  (D/(name+'.COMMAND.json')).write_text(json.dumps({'command':command,'code_commit':code,'time_unix':time.time()},indent=2)+'\n')
  with (D/(name+'.log')).open('w') as stream:q=subprocess.run(['/usr/bin/time','-v','-o',str(D/(name+'.CPU_IO.txt'))]+command,cwd=S,stdout=stream,stderr=subprocess.STDOUT)
  if q.returncode:raise RuntimeError('Pilot failed: '+name)
  done.append(name);(O/'PILOT_v2_PROGRESS.json').write_text(json.dumps({'status':'RUNNING','completed':done,'expected':12}));print(name,flush=True)
 (O/'PILOT_v2_SUMMARY.json').write_text(json.dumps({'status':'COMPLETE_12_REAL_GPU_PILOT_CELLS','completed':done,'formal_not_launched':True},indent=2)+'\n')
except BaseException as e:
 (O/'STOP_PILOT_v2.json').write_text(json.dumps({'error':repr(e),'completed':done},indent=2)+'\n');raise
