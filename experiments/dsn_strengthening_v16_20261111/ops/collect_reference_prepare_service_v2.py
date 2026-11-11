"""Close measured reference; execute only metadata steps3/4/5, no serving."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1];D=E/'launch_ops/REFERENCE_FULL4_V2'
h=json.loads((D/'HANDLE.json').read_bytes());hand=json.loads((E/'baseline_ops/PILOT_PREPARATION_V2/LAUNCH_HANDOFF.json').read_bytes())
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
script='C='+repr(h)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,subprocess
p=Path('/proc')/str(C['pid']);active=False
if p.exists():
 f=(p/'stat').read_text().rsplit(')',1)[1].split();active=int(f[19])==C['start_ticks'] and f[0] not in ('Z','X')
assert not active,'owned reference still running'
owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader'],text=True).strip();assert not owners
out=Path(C['out']);g=json.loads((out/'GATE.json').read_bytes());assert g['status']=='PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES' and g['expected_sources']==g['completed_sources']==4
assert g['all_original_full_state_C_IDs_equal'] and g['actual_NN_source_commit']=='de0936b2e30179d63aeef6e235cd1af685578c58'
print(json.dumps(dict(status='PASS_REFERENCE_AND_OWNED_PROCESS_PHYSICAL_RELEASE',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=C['pid'],start_ticks=C['start_ticks'],active_owned_process=False,compute_owners=owners,gate_sha256=hashlib.sha256((out/'GATE.json').read_bytes()).hexdigest(),reference_only=True,actual_serving_runs=0)))
'''
with m.Remote() as c:
 raw=c.python(script,timeout=30);(D/'RESOURCE_CLOSURE.json').write_bytes(raw+b'\n')
 for name in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','MODEL_READY.json','GENESIS.json','PROGRESS.json','INPUTS.json','REFERENCE_ENERGY.json','REFERENCE_DETAILS.json','GATE.json','SUMMARY.json','REFERENCE_RECEIPT.json']:
  c.get(h['out']+'/'+name,E/'gpu_results/REFERENCE_FULL4_V2'/name,maximum=5_000_000)
 for row in hand['ordered_commands'][2:5]:
  c.python('import subprocess\nsubprocess.run('+repr(row['command'])+',check=True)\n',timeout=45)
 prep=hand['ordered_commands'][0]['command'][6].rsplit('/',1)[0]
 for name in ['SERVICE_PLAN.json','SERVICE_PRELAUNCH.json']:
  c.get(prep+'/'+name,E/'baseline_ops/PILOT_PREPARATION_V2'/name)
 for name in ['REFERENCE_RECEIPT.json','REFERENCE_DETAILS.json','GENESIS.json','GATE.json']:
  c.get(prep+'/PILOT_BOUND_REFERENCE/'+name,E/'baseline_ops/PILOT_BOUND_REFERENCE_V2'/name,maximum=5_000_000)
 plan=json.loads((E/'baseline_ops/PILOT_PREPARATION_V2/SERVICE_PLAN.json').read_bytes());assert len(plan['cells'])==24
 for cell in plan['cells']:c.get(cell['config'],E/'baseline_ops/PILOT_PREPARATION_V2/service_configs'/Path(cell['config']).name)
print(json.dumps(dict(status='PASS_MEASURED_FULL4_AND_BOUND_SUBSET2_PILOT24_METADATA_FROZEN_NOT_LAUNCHED',reference_gate=sha(E/'gpu_results/REFERENCE_FULL4_V2/GATE.json'),service_plan_sha256=sha(E/'baseline_ops/PILOT_PREPARATION_V2/SERVICE_PLAN.json'),planned_cells=24,actual_serving_runs=0)))
