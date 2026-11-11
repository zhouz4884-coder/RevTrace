"""Close/collect the actual eight-cell grouped resource study."""
from pathlib import Path
import hashlib,importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];D=E/'launch_ops/RESOURCE8_V1';h=json.loads((D/'HANDLE.json').read_bytes())
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
script='C='+repr(h)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,subprocess
p=Path('/proc')/str(C['pid']);active=False
if p.exists():
 f=(p/'stat').read_text().rsplit(')',1)[1].split();active=int(f[19])==C['start_ticks'] and f[0]not in('Z','X')
assert not active
owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader'],text=True).strip();assert not owners
out=Path(C['out']);g=json.loads((out/'GATE.json').read_bytes());s=json.loads((out/'SUMMARY.json').read_bytes());assert g['status']=='COMPLETE_FROZEN_RESOURCE8_TASK_AND_ALL_SOURCE_ENDPOINTS' and s['completed_trials']==8
for row in s['cells']:assert json.loads((Path(row['raw_result_location'])/'GATE.json').read_bytes())['status']=='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK'
print(json.dumps(dict(status='PASS_RESOURCE8_COMPLETE_AND_OWNED_PHYSICAL_RELEASE',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=C['pid'],start_ticks=C['start_ticks'],active_owned_process=False,compute_owners=owners,completed_trials=8,gate_sha256=hashlib.sha256((out/'GATE.json').read_bytes()).hexdigest(),new_independent_speakers=0)))
'''
with m.Remote()as c:
 raw=c.python(script,timeout=45);(D/'RESOURCE_CLOSURE.json').write_bytes(raw+b'\n');t=E/'gpu_results/RESOURCE8_V1'
 for n in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','PARTIAL_RESULTS.json','ROOT_ACTUAL_TRACE_RECHECK_ENTRY.json']:c.get(h['out']+'/'+n,t/n,maximum=5_000_000)
 s=json.loads((t/'SUMMARY.json').read_bytes())
 for r in s['cells']:
  for n in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','ORIGIN.json','EXTERNAL_RESOURCE_GROUP_AUDIT.json']:
   c.get(r['raw_result_location']+'/'+n,t/'cells'/r['cell_id']/n,maximum=5_000_000)
rows=[]
for group in ['sync2','sync4']:
 for arm in ['conservative','fullcall']:
  g=[r for r in s['cells']if r['source_group_id']==group and r['strategy']==arm];off=sum(r['primary']['offered_audio_seconds']for r in g);credit=sum(r['primary']['dual_deadline_audio_credit_seconds']for r in g)
  rows.append(dict(group=group,strategy=arm,trials=len(g),offered_audio_seconds=off,credit_audio_seconds=credit,credit_percent=100*credit/off,whole_run_passes=sum(r['primary']['complete_coverage_and_original_quantile_pass']for r in g)))
j=dict(record_type='DERIVED_FROM_COMPLETED_FROZEN_RESOURCE8_SUMMARY',source_summary_sha256=hashlib.sha256((E/'gpu_results/RESOURCE8_V1/SUMMARY.json').read_bytes()).hexdigest(),rows=rows,scope='Four reused speakers, eight timing/configuration trials; same two GPUs, all offered and synchronous500ms. No maximum-capacity or policy-exclusive increment inference.')
(E/'gpu_results/RESOURCE8_V1/BOUNDED_PRIMARY_TABLE.json').write_text(json.dumps(j,indent=2)+'\n',encoding='utf8');print(json.dumps(j))
