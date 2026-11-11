"""Collect bounded completed pilot outputs and verify owned physical release."""
from pathlib import Path
import hashlib,importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];D=E/'launch_ops/PILOT24_V2';h=json.loads((D/'HANDLE.json').read_bytes())
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
script='C='+repr(h)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,subprocess
p=Path('/proc')/str(C['pid']);active=False
if p.exists():
 f=(p/'stat').read_text().rsplit(')',1)[1].split();active=int(f[19])==C['start_ticks'] and f[0] not in ('Z','X')
assert not active,'owned matrix still running'
owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader'],text=True).strip();assert not owners
out=Path(C['out']);g=json.loads((out/'GATE.json').read_bytes());s=json.loads((out/'SUMMARY.json').read_bytes())
assert g['status']=='COMPLETE_FROZEN_V16_MAIN_AND_AUXILIARY_TASK_AND_ENDPOINTS' and g['completed_trials']==s['completed_trials']==24
for row in s['cells']:
 raw=Path(row['raw_result_location']);gate=json.loads((raw/'GATE.json').read_bytes());assert gate['status']=='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK'
print(json.dumps(dict(status='PASS_PILOT24_COMPLETED_AND_OWNED_PHYSICAL_RELEASE',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=C['pid'],start_ticks=C['start_ticks'],active_owned_process=False,compute_owners=owners,completed_trials=24,source_commit=s['actual_NN_source_commit'],gate_sha256=hashlib.sha256((out/'GATE.json').read_bytes()).hexdigest(),separate_trace_audit_pending=True)))
'''
with m.Remote()as c:
 raw=c.python(script,timeout=45);(D/'RESOURCE_CLOSURE.json').write_bytes(raw+b'\n')
 target=E/'gpu_results/PILOT24_V2'
 for n in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','PARTIAL_RESULTS.json','ROOT_ACTUAL_TRACE_RECHECK_ENTRY.json']:
  c.get(h['out']+'/'+n,target/n,maximum=5_000_000)
 summary=json.loads((target/'SUMMARY.json').read_bytes())
 for row in summary['cells']:
  for n in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','ORIGIN.json','EXTERNAL_V16_AUDIT.json']:
   try:c.get(row['raw_result_location']+'/'+n,target/'cells'/row['cell_id']/n,maximum=5_000_000)
   except FileNotFoundError:
    if n!='EXTERNAL_V16_AUDIT.json':raise
rows=[]
for arm in sorted({r['strategy']for r in summary['cells']}):
 g=[r for r in summary['cells']if r['strategy']==arm];off=sum(r['primary']['offered_audio_seconds']for r in g);credit=sum(r['primary']['dual_deadline_audio_credit_seconds']for r in g)
 rows.append(dict(strategy=arm,trials=len(g),offered_audio_seconds=off,dual_deadline_credit_audio_seconds=credit,credit_percent=100*credit/off,whole_run_passes=sum(r['primary']['complete_coverage_and_original_quantile_pass']for r in g)))
out=dict(record_type='DERIVED_SUM_OF_COMPLETED_NATIVE_CONTROLLER_RESULTS_NOT_NEW_MEASUREMENT',source_summary_sha256=hashlib.sha256((E/'gpu_results/PILOT24_V2/SUMMARY.json').read_bytes()).hexdigest(),source_NN='de0936b2e30179d63aeef6e235cd1af685578c58',driver='f367c4e1068a9391a0e99d8537c94995a3388e13',completed_trials=24,existing_speakers=2,rows=rows,separate_trace_and_opportunity_audit_pending=True)
(E/'gpu_results/PILOT24_V2/BOUNDED_PRIMARY_TABLE.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8');print(json.dumps(out))
