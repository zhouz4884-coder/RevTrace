"""Frozen72-cell online necessity/cost study; no adaptive tuning or new topic."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
B=Path(sys.argv[1]);P=B/'projects/revtrace_online_admission_20261022';S=P/'pilot_sdk_v3';O=B/'results/revtrace/online_admission_20261022';D=O/'formal_v1'
def read(p):return json.loads(p.read_text())
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert read(O/'STRONG_BASELINE_GATE.json')['status']=='PASS_STRONG_BASELINE_BEFORE_FORMAL'
assert read(O/'batch16_protocol_v1/SUMMARY.json')['status']=='PASS_BATCH16_COMPLETE_VERIFICATION_AND_SELECTIVE_FALLBACK'
source=read(S/'SOURCE_MANIFEST.json');code=source['code_commit'];assert code=='55cd52dfdbab71298cdb7eae3b0c08c9424020c6'
for r in source['files']:assert sha(S/r['path'])==r['sha256']
assert '163 passed' in (O/'CPU_LINUX_v3.log').read_text()
mf=B/'datasets/revtrace/phaseD_20261021/manifest.json';manifest=read(mf);assert len(manifest['sessions'])==len({r['source_id'].split('-')[0] for r in manifest['sessions']})==16
weights=read(O/'PILOT_v2_FREEZE.json')['weights']
for r in weights:assert sha(B/'models/Qwen3-ASR-1.7B'/r['file'])==r['sha256']
methods=['fine','unprotected','score','strict','dgft','standard'];strata=[(l,t) for l in ['sync16','cohort8'] for t in ['clean','F2']];matrix=[]
for repeat in range(3):
 order=strata[repeat:]+strata[:repeat]
 for gi,(load,traffic) in enumerate(order):
  k=(2*repeat+gi)%6;ms=methods[k:]+methods[:k]
  if repeat==1:ms=list(reversed(ms))
  for method in ms:matrix.append({'repeat':repeat,'load':load,'traffic':traffic,'method':method})
assert len(matrix)==72 and not D.exists();D.mkdir()
freeze={'experiment':'REVTRACE-ONLINE-ADMISSION-FORMAL-v1','matrix':matrix,'runtime_code_commit':code,'runtime_source_manifest_sha256':sha(S/'SOURCE_MANIFEST.json'),'controller_sha256':sha(Path(__file__)),'source_manifest_sha256':sha(mf),'weights':weights,'donors_sha256':sha(P/'DONORS.json'),'protocol_sha256':sha(P/'PROTOCOL.md'),'fairness_amendment_sha256':sha(P/'FAIRNESS_AMENDMENT_PRE_FORMAL.md'),'formal_estimands_v2_sha256':sha(P/'FORMAL_ESTIMANDS_PRE_FREEZE_v2.md'),'statistical_seed':20261022,'formal_audio_sources':16,'repeat_count_per_stratum_method':3,'fresh_runs_not_pilot_repeats':True,'oracle_diagnostics_in_serving':False,'fallback_layout':'selective-with-row-separability-full-fallback-guard','best_verification_alternative_includes_fine_independent_authority':True,'no_paper_edits_or_Elastic_DAG_V2_recovery_expansion':True}
(O/'FORMAL_FREEZE.json').write_text(json.dumps(freeze,indent=2)+'\n');done=[]
try:
 for r in matrix:
  assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'Unexpected GPU task; do not interfere'
  name=f"{r['method']}-{r['load']}-{r['traffic']}-r{r['repeat']}";out=D/name
  cmd=[sys.executable,'-u',str(S/'scripts/run_tc_live_qwen.py'),'--model',str(B/'models/Qwen3-ASR-1.7B'),'--manifest',str(mf),'--output',str(out),'--code-commit',code,'--study-id','REVTRACE-ONLINE-ADMISSION-FORMAL-v1','--sessions','16','--arrival','sync' if r['load']=='sync16' else 'staggered','--seed',str(20261022+r['repeat']),'--trusted-text-binding','--display-protocol','canonical-snapshot-v1','--publish-canonical-display','--consumer-policy','two_lane','--retain-verified-private-prefix','--phase-n-instrumentation','--capture-model-inputs','--online-study-method',r['method'],'--online-traffic',r['traffic'],'--online-donors',str(P/'DONORS.json'),'--online-fallback-layout','selective','--durable-journal-path',str(D/'journals'/(name+'.wal')),'--journal-sync-mode','group_ready']
  if r['load']=='cohort8':cmd+=['--online-arrival-cohort','8']
  (D/(name+'.COMMAND.json')).write_text(json.dumps({'command':cmd,'code_commit':code,'frozen_run':r,'time_unix':time.time()},indent=2)+'\n')
  with (D/(name+'.log')).open('w') as f:q=subprocess.run(['/usr/bin/time','-v','-o',str(D/(name+'.CPU_IO.txt'))]+cmd,cwd=S,stdout=f,stderr=subprocess.STDOUT)
  if q.returncode:raise RuntimeError('Formal cell failed; no silent retry: '+name)
  result=read(out/'result.json');assert result['fine_window_accounting_complete']
  done.append(name);(O/'FORMAL_PROGRESS.json').write_text(json.dumps({'status':'RUNNING','completed':done,'expected':72,'last_completed':name}));print(name,flush=True)
 (O/'FORMAL_SUMMARY.json').write_text(json.dumps({'status':'COMPLETE_72_FRESH_ONLINE_FORMAL_CELLS','completed':done,'frozen_code':code,'no_more_GPU_experiments_issued':True},indent=2)+'\n')
except BaseException as e:(O/'STOP_FORMAL_v1.json').write_text(json.dumps({'error':repr(e),'completed':done,'remaining_matrix_not_silently_dropped':True},indent=2)+'\n');raise
