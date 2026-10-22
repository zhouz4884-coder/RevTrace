from pathlib import Path
import hashlib,json,subprocess,sys,time
B=Path(sys.argv[1]);P=B/'projects/revtrace_elastic_20261022';S=P/'elastic_sdk';O=B/'results/revtrace/elastic_20261022';F=O/'formal';F.mkdir(exist_ok=True)
assert json.loads((O/'STRESS_SPACE_GATE.json').read_text())['decision']=='GO_MINIMAL_ELASTIC_PROTOTYPE'
code=json.loads((S/'SOURCE_MANIFEST.json').read_text())['code_commit'];assert json.loads((S/'SOURCE_MANIFEST.json').read_text())['CPU_protocol_tests']==148
mf=B/'datasets/revtrace/elastic_20261022_32/manifest.json';calib=O/'SERVICE_CALIBRATION.json';names=['fixed1','fixed2','fixed3','backlog','deadline','joint'];matrix=[]
for repeat in range(4):
 order=names[2*repeat:]+names[:2*repeat] if repeat<3 else list(reversed(names))
 for policy in order:matrix.append({'repeat':repeat,'policy':policy})
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
weights=[{'file':p.name,'sha256':sha(p)} for p in sorted((B/'models/Qwen3-ASR-1.7B').glob('*.safetensors'))];prior=json.loads((O/'STRESS_SCOUT_FREEZE.json').read_text())['weights_verified_before_GPU'];assert {r['file']:r['sha256'] for r in weights}=={r['file']:r['sha256'] for r in prior}
assert not list(F.glob('*/result.json'))
(O/'FORMAL_FREEZE.json').write_text(json.dumps({'matrix':matrix,'code_commit':code,'manifest_sha256':sha(mf),'calibration_sha256':sha(calib),'weights_verified_before_GPU':weights,'controller_sha256':sha(Path(__file__)),'fresh_not_scout':True},indent=2)+'\n');done=[]
try:
 for r in matrix:
  assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
  name=f"{r['policy']}-lhl32-r{r['repeat']}";out=F/name;assert not out.exists()
  command=[sys.executable,'-u',str(S/'scripts/run_tc_live_qwen.py'),'--model',str(B/'models/Qwen3-ASR-1.7B'),'--manifest',str(mf),'--output',str(out),'--code-commit',code,'--study-id','ELASTIC-FORMAL-LHL32','--mode','coarse','--granularity-policy',r['policy'],'--service-calibration',str(calib),'--sessions','32','--arrival','low-high-low','--proposal-barrier','decoupled','--proposal-reconciliation','lazy','--display-protocol','canonical-snapshot-v1','--publish-canonical-display','--trusted-text-binding','--consumer-policy','two_lane','--retain-verified-private-prefix','--phase-n-instrumentation','--capture-model-inputs','--durable-journal-path',str(F/'journals'/(name+'.wal')),'--journal-sync-mode','group_ready']
  (F/(name+'.COMMAND.json')).write_text(json.dumps({'command':command,'code_commit':code,'frozen_unix':time.time()},indent=2)+'\n')
  with (F/(name+'.log')).open('w') as stream:q=subprocess.run(['/usr/bin/time','-v','-o',str(F/(name+'.CPU_IO.txt'))]+command,cwd=S,stdout=stream,stderr=subprocess.STDOUT)
  if q.returncode:raise RuntimeError('Formal cell failed: '+name)
  done.append(name);(O/'FORMAL_PROGRESS.json').write_text(json.dumps({'completed':done,'expected':24}));print(name,flush=True)
 (O/'FORMAL_SUMMARY.json').write_text(json.dumps({'status':'COMPLETE_24_FORMAL_CELLS','completed':done},indent=2)+'\n')
except BaseException as e:(O/'STOP_FORMAL.json').write_text(json.dumps({'error':repr(e),'completed':done},indent=2));raise
