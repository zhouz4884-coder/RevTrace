"""Collect a complete two-arm confirmation; keep pilot and confirmation phases."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1]
p=argparse.ArgumentParser();p.add_argument('--tag',required=True,choices=['CONFIRM_NEW2_FULL_READY_V1','CONFIRM_LAST4_FULL_READY_V1']);p.add_argument('--expected',type=int,required=True);a=p.parse_args();D=E/'launch_ops'/a.tag;h=json.loads((D/'HANDLE.json').read_bytes())
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
script='C='+repr(dict(handle=h,expected=a.expected))+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,subprocess
h=C['handle'];p=Path('/proc')/str(h['pid']);active=False
if p.exists():
 f=(p/'stat').read_text().rsplit(')',1)[1].split();active=int(f[19])==h['start_ticks'] and f[0]not in('Z','X')
assert not active
owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader'],text=True).strip();assert not owners
out=Path(h['out']);g=json.loads((out/'GATE.json').read_bytes());s=json.loads((out/'SUMMARY.json').read_bytes());assert g['status']=='COMPLETE_FOCUSED_FULL_READY_CONFIRMATION_TASK_AND_ENDPOINTS' and s['completed_trials']==C['expected']
for r in s['cells']:assert json.loads((Path(r['raw_result_location'])/'GATE.json').read_bytes())['status']=='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK'
print(json.dumps(dict(status='PASS_FOCUSED_CONFIRMATION_AND_OWNED_PHYSICAL_RELEASE',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=h['pid'],start_ticks=h['start_ticks'],active_owned_process=False,compute_owners=owners,completed_trials=C['expected'],gate_sha256=hashlib.sha256((out/'GATE.json').read_bytes()).hexdigest())))
'''
with m.Remote()as c:
 raw=c.python(script,timeout=45);(D/'RESOURCE_CLOSURE.json').write_bytes(raw+b'\n');t=E/'gpu_results'/a.tag
 for n in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','PARTIAL_RESULTS.json']:c.get(h['out']+'/'+n,t/n,maximum=5_000_000)
 s=json.loads((t/'SUMMARY.json').read_bytes())
 for r in s['cells']:
  for n in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','ORIGIN.json']:c.get(r['raw_result_location']+'/'+n,t/'cells'/r['cell_id']/n,maximum=5_000_000)
rows=[]
for arm in ['fullcall','ready_only']:
 g=[r for r in s['cells']if r['strategy']==arm];off=sum(r['primary']['offered_audio_seconds']for r in g);credit=sum(r['primary']['dual_deadline_audio_credit_seconds']for r in g)
 rows.append(dict(strategy=arm,trials=len(g),offered_audio_seconds=off,credit_audio_seconds=credit,credit_percent=100*credit/off,whole_run_passes=sum(r['primary']['complete_coverage_and_original_quantile_pass']for r in g)))
j=dict(record_type='DERIVED_COMPLETED_FOCUSED_CONFIRMATION_PRIMARY_TABLE',tag=a.tag,source_summary_sha256=hashlib.sha256((E/'gpu_results'/a.tag/'SUMMARY.json').read_bytes()).hexdigest(),rows=rows,scope='New policy comparison on preselected existing speakers; pilot remains distinct; timing repeats do not add acoustic units.')
(E/'gpu_results'/a.tag/'BOUNDED_PRIMARY_TABLE.json').write_text(json.dumps(j,indent=2)+'\n',encoding='utf8');print(json.dumps(j))
