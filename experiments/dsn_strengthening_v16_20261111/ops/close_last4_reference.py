"""Close only the newly measured last-four reference; no serving synthesis."""
from pathlib import Path
import hashlib,importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];D=E/'launch_ops/REFERENCE_LAST4_V1';h=json.loads((D/'HANDLE.json').read_bytes())
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
script='C='+repr(h)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,subprocess
p=Path('/proc')/str(C['pid']);active=False
if p.exists():
 f=(p/'stat').read_text().rsplit(')',1)[1].split();active=int(f[19])==C['start_ticks'] and f[0]not in('Z','X')
assert not active
owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader'],text=True).strip();assert not owners
out=Path(C['out']);g=json.loads((out/'GATE.json').read_bytes());assert g['status']=='PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES'and g['completed_sources']==g['expected_sources']==4 and g['all_original_full_state_C_IDs_equal']
print(json.dumps(dict(status='PASS_LAST4_MEASURED_REFERENCE_AND_PHYSICAL_RELEASE',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=C['pid'],start_ticks=C['start_ticks'],active_owned_process=False,compute_owners=owners,gate_sha256=hashlib.sha256((out/'GATE.json').read_bytes()).hexdigest(),actual_serving_runs=0)))
'''
with m.Remote()as c:
 raw=c.python(script,timeout=30);(D/'RESOURCE_CLOSURE.json').write_bytes(raw+b'\n')
 for n in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','MODEL_READY.json','GENESIS.json','PROGRESS.json','INPUTS.json','REFERENCE_ENERGY.json','REFERENCE_DETAILS.json','GATE.json','SUMMARY.json','REFERENCE_RECEIPT.json']:c.get(h['out']+'/'+n,E/'gpu_results/REFERENCE_LAST4_V1'/n,maximum=5_000_000)
s=json.loads((E/'gpu_results/REFERENCE_LAST4_V1/SUMMARY.json').read_bytes());print(json.dumps(dict(status=s['status'],sources=s['completed_sources'],ledger=s['ledger'],reference_only=True,actual_serving_runs=0)))
