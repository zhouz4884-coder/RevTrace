"""Independent post-run CPU diagnostics and correction of a static audit field."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;S=P/'runtime';O=B/'results/revtrace/ces_v5_20261025'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert read(O/'SUMMARY.json')['online_cells']==48
assert not (O/'POST_CPU_STARTED.json').exists()
save(O/'POST_CPU_STARTED.json',{'pid':os.getpid(),'time_unix':time.time(),'GPU_calls':0,
 'code_sha256':{n:sha(P/n) for n in ['post_cpu.py','diagnose_actual.py','replay_actual_inputs.py','audit_v5_metadata_fixed.py']}})
commands=[('diagnosis',[sys.executable,str(P/'diagnose_actual.py'),str(B)]),
 ('input_replay',[sys.executable,str(P/'replay_actual_inputs.py'),str(B),'pilot_v1']),
 ('metadata_corrected_audit',[sys.executable,str(P/'audit_v5_metadata_fixed.py'),'--root',str(O),'--stage','pilot_v1','--source',str(S),
 '--output',str(O/'pilot_v1_audit_corrected'),'--model',str(B/'models/Qwen3-ASR-1.7B'),
 '--references',str(B/'results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json'),'--expected-cells',str(O/'pilot_v1_EXPECTED.json')])]
completed=[]
try:
 for name,cmd in commands:
  with (O/('POST_'+name+'.log')).open('w') as f:r=subprocess.run(cmd,cwd=P,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
  assert r.returncode==0,(name,r.returncode)
  completed.append(name);save(O/'POST_CPU_PROGRESS.json',{'completed':completed,'GPU_calls':0});print('CPU_POST_COMPLETE',name,flush=True)
 old=read(O/'pilot_v1_audit/SUMMARY.json');new=read(O/'pilot_v1_audit_corrected/SUMMARY.json')
 assert not old['failures'] and not new['failures'] and old['cells']==new['cells']==48
 for name in ['SERVICE_CELLS.csv','COMMON_FRONTIERS.csv','SOURCE_QUALITY.csv','PHYSICAL_COSTS.csv']:
  assert sha(O/'pilot_v1_audit'/name)==sha(O/'pilot_v1_audit_corrected'/name)
 save(O/'AUDIT_METADATA_CORRECTION.json',{'original_summary_actual_model_calls':old['actual_model_calls'],
  'corrected_summary_actual_model_calls':new['actual_model_calls'],'all_four_metric_CSVs_byte_identical':True,
  'reason':'Original CPU-authored audit summary accidentally retained a literal0; actual costs were already recorded correctly in PHYSICAL_COSTS.csv',
  'new_GPU_calls_for_correction':0,'original_audit_retained':True})
 save(O/'POST_CPU_SUMMARY.json',{'status':'PASS_INDEPENDENT_V5_DIAGNOSIS_INPUT_REPLAY_AND_METADATA_CORRECTION',
  'completed':completed,'GPU_calls':0,'online_cells':48})
except BaseException as e:
 save(O/'POST_CPU_STOP.json',{'error':repr(e),'completed':completed,'GPU_calls':0,'raw_retained':True});raise
