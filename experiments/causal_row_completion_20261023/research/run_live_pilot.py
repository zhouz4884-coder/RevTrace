"""Frozen bounded ten-cell live pilot; no automatic formal matrix."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time

B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/row_completion_20261023'
S=P/'source_row_sdk_v2';D=O/'row_live_pilot_v1'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
assert read(O/'row_operator_independent_v1/SUMMARY.json')['GO_bounded_live_pilot']
assert read(O/'ROW_CPU_GATE_v2.json')['status'].startswith('PASS')
assert not D.exists();D.mkdir();(D/'journals').mkdir()
meta=read(S/'SOURCE_MANIFEST.json')
for r in meta['files']:assert hashlib.sha256((S/r['path']).read_bytes()).hexdigest()==r['sha256']
plan=[('fine','batch'),('fine','row'),('dgft','row'),('dgft','batch'),('standard','batch'),('standard','row'),('strict','row'),('strict','batch'),('score','batch'),('score','row')]
save(D/'RUN.json',{'experiment_id':'REVTRACE-ROW-LIVE-PILOT-v1','runtime_code_commit':meta['code_commit'],
 'controller_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'frozen_plan':plan,
 'sources':16,'arrival':'sync16','traffic':'F2','repeat':1,'not_formal_superiority':True,
 'all_five_policies_share_early_return_capability':True,'no_automatic_formal_or_rescue_launch':True})
completed=[]
try:
 for method,delivery in plan:
  assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'Do not contend with another task'
  name=f'{method}-{delivery}-sync16-F2-pilot';out=D/name
  cmd=[sys.executable,'-u',str(S/'scripts/run_tc_live_qwen.py'),'--model',str(B/'models/Qwen3-ASR-1.7B'),
    '--manifest',str(B/'datasets/revtrace/phaseD_20261021/manifest.json'),'--output',str(out),
    '--code-commit',meta['code_commit'],'--study-id','REVTRACE-ROW-LIVE-PILOT-v1','--sessions','16','--arrival','sync',
    '--seed','20261023','--trusted-text-binding','--display-protocol','canonical-snapshot-v1','--publish-canonical-display',
    '--consumer-policy','two_lane','--retain-verified-private-prefix','--phase-n-instrumentation','--capture-model-inputs',
    '--online-study-method',method,'--online-traffic','F2','--online-donors',str(B/'projects/revtrace_online_admission_20261022/DONORS.json'),
    '--online-fallback-layout','selective','--durable-journal-path',str(D/'journals'/(name+'.wal')),
    '--journal-sync-mode','group_ready','--result-delivery',delivery]
  save(D/(name+'.COMMAND.json'),{'argv':cmd,'runtime_source_commit':meta['code_commit'],'not_outcome_selected':True})
  with (D/(name+'.log')).open('w') as log:q=subprocess.run(['/usr/bin/time','-v','-o',str(D/(name+'.CPU_IO.txt'))]+cmd,cwd=S,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
  assert q.returncode==0,f'pilot failure {name}, no silent retry'
  result=read(out/'result.json');assert result['fine_window_accounting_complete']
  completed.append(name);save(D/'PROGRESS.json',{'completed':completed,'expected':10});print(name,flush=True)
 audit=[sys.executable,str(P/'audit_row_cells_v1.py'),str(B),'row_live_pilot_v1','10',str(S)]
 with (O/'ROW_LIVE_PILOT_AUDIT_v1.log').open('w') as log:q=subprocess.run(audit,cwd=S,stdout=log,stderr=subprocess.STDOUT)
 assert q.returncode==0,'independent live audit failed; no formal launch'
 save(D/'SUMMARY.json',{'status':'COMPLETE_ALL10_LIVE_PILOTS_INDEPENDENT_AUDIT_PASS','completed':completed,
   'runtime_code_commit':meta['code_commit'],'not_formal_effect_or_algorithm_increment':True,'no_formal_auto_launch':True})
except BaseException as e:
 save(D/'STOP.json',{'error':repr(e),'completed':completed,'no_silent_retry':True,'all_results_retained':True});raise
