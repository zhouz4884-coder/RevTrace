"""Four bounded live cells for the stronger fallback, no formal issuance."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
B=Path(sys.argv[1]);P=B/'projects/revtrace_online_admission_20261022';S=P/'pilot_sdk_v3';O=B/'results/revtrace/online_admission_20261022';D=O/'pilot_v3';D.mkdir(exist_ok=False)
assert json.loads((O/'PILOT_v2_AUDIT_GATE.json').read_text())['status']=='PASS_BOUND_ONLINE_KERNEL_AND_INPUT_AUDIT'
assert '163 passed' in (O/'CPU_LINUX_v3.log').read_text()
source=json.loads((S/'SOURCE_MANIFEST.json').read_text());code=source['code_commit']
for r in source['files']:assert hashlib.sha256((S/r['path']).read_bytes()).hexdigest()==r['sha256']
matrix=[{'method':m,'traffic':t} for t in ['clean','F2'] for m in ['score','strict']];done=[]
(O/'PILOT_v3_FREEZE.json').write_text(json.dumps({'code_commit':code,'matrix':matrix,'sources':'same4 pilot speakers, disjoint formal16','arrivals':'two2-source cohorts at0/32s, intra-cohort .25s','fallback_layout':'selective-with-paid-full-layout-guard','oracle_diagnostic':True,'formal_not_launched':True},indent=2)+'\n')
try:
 for r in matrix:
  assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
  name=r['method']+'-'+r['traffic'];out=D/name
  cmd=[sys.executable,'-u',str(S/'scripts/run_tc_live_qwen.py'),'--model',str(B/'models/Qwen3-ASR-1.7B'),'--manifest',str(O/'PILOT_MANIFEST.json'),'--output',str(out),'--code-commit',code,'--study-id','ONLINE-ADMISSION-STRONG-FALLBACK-PILOT-v3','--sessions','4','--arrival','staggered','--online-arrival-cohort','2','--trusted-text-binding','--display-protocol','canonical-snapshot-v1','--publish-canonical-display','--consumer-policy','two_lane','--retain-verified-private-prefix','--phase-n-instrumentation','--capture-model-inputs','--online-study-method',r['method'],'--online-traffic',r['traffic'],'--online-donors',str(P/'DONORS.json'),'--online-fallback-layout','selective','--online-oracle-diagnostic','--durable-journal-path',str(D/'journals'/(name+'.wal')),'--journal-sync-mode','group_ready']
  (D/(name+'.COMMAND.json')).write_text(json.dumps({'command':cmd,'time_unix':time.time(),'code_commit':code},indent=2)+'\n')
  with (D/(name+'.log')).open('w') as stream:q=subprocess.run(['/usr/bin/time','-v','-o',str(D/(name+'.CPU_IO.txt'))]+cmd,cwd=S,stdout=stream,stderr=subprocess.STDOUT)
  if q.returncode:raise RuntimeError('Strong fallback pilot failed: '+name)
  done.append(name);(O/'PILOT_v3_PROGRESS.json').write_text(json.dumps({'completed':done,'expected':4}));print(name,flush=True)
 (O/'PILOT_v3_SUMMARY.json').write_text(json.dumps({'status':'COMPLETE_4_STRONG_FALLBACK_GPU_PILOTS','completed':done,'formal_not_launched':True},indent=2)+'\n')
except BaseException as e:(O/'STOP_PILOT_v3.json').write_text(json.dumps({'error':repr(e),'completed':done},indent=2)+'\n');raise
