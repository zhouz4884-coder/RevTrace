"""Bounded collection and CPU/PID closure; no model/process signals."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1];H=E/'opportunity_ops';L=json.loads((H/'PROCESS_LAUNCH_V1.json').read_bytes())
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
with m.Remote() as c:
 code='L='+repr(L)+'\n'+r'''
from pathlib import Path
import hashlib,json,subprocess,datetime
O=Path(L['raw_result_location']);gate=json.loads((O/'GATE.json').read_bytes());assert gate['status']=='PASS_COMPLETE_ALL24_OPPORTUNITY_BINDINGS'
p=Path('/proc/'+str(L['pid'])+'/stat');same=p.exists() and p.read_text().rsplit(')',1)[1].split()[19]==L['start_ticks'];state=p.read_text().rsplit(')',1)[1].split()[0] if same else None
assert not same or state in ('Z','X'),'CPU worker still executing'
files=[p for p in O.rglob('*') if p.is_file() and p.suffix in ('.json','.csv','.log')]
index=[dict(relative=str(p.relative_to(O)).replace('\\','/'),path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(files)]
assert sum(r['bytes'] for r in index)<=20000000
owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True).strip()
print(json.dumps(dict(gate=gate,index=index,closure=dict(status='PASS_OPPORTUNITY_CPU_COMPLETED_NO_OWN_ACTIVE_PROCESS',pid=L['pid'],start_ticks=L['start_ticks'],same_process_identity=same,state=state,
 CUDA_compute_owners_observed=owners,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_model_calls=0,no_process_signalled=True))))
'''
 raw=c.python(code,timeout=60);payload=json.loads(raw);D=H/'RESULTS_V1';D.mkdir(exist_ok=False)
 for r in payload['index']:
  local=D/r['relative'];blob=c.get(r['path'],local,maximum=20000000)
  assert len(blob)==r['bytes'] and hashlib.sha256(blob).hexdigest()==r['sha256']
 (D/'DOWNLOAD_VERIFICATION.json').write_text(json.dumps(payload['index'],indent=2)+'\n',encoding='utf8')
 (H/'CPU_RESOURCE_CLOSURE_V1.json').write_text(json.dumps(payload['closure'],indent=2)+'\n',encoding='utf8')
for args in (['--output',str(H/'FINAL_DEFAULT_SOURCE_GATE_V1.json')],['--source',str(E/'opportunity_audit_source_v1'),'--manifest',str(E/'opportunity_packages_v1/SOURCE.json'),'--output',str(H/'FINAL_AUDIT_SOURCE_GATE_V1.json')]):
 subprocess.run(['python','-B',str(R/'experiments/repository_identity_20261027/preflight.py'),*args],check=True,capture_output=True)
print(json.dumps(dict(files=len(payload['index']),bytes=sum(r['bytes'] for r in payload['index']),local=str(D),closure=payload['closure'],default_and_audit_source_final_gates='PASS')))
