"""Read-only final source/PID-generation/result observation; no process signals."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1];H=E/'history_ops'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
pointer=R/'experiments/repository_identity_20261027/CURRENT.json';before=sha(pointer)
items=[('PRIMARY_v1','PROCESS_LAUNCH_v1.json','source_v1','SOURCE_v1.json'),('INDEPENDENT_v1','AUDIT_PROCESS_LAUNCH_v1.json','audit_source_v1','AUDIT_SOURCE_v1.json'),
 ('LEDGER_v2','LEDGER_PROCESS_LAUNCH_v2.json','ledger_source_v2','LEDGER_SOURCE_v2.json'),('EXPOSURE_v2','METRICS_v2_PROCESS_LAUNCH.json','exposure_v2_source','METRICS_v2_SOURCE.json'),
 ('EXPOSURE_INDEPENDENT_v2','METRICS_AUDIT_v2_PROCESS_LAUNCH.json','exposure_independent_v2_source','METRICS_AUDIT_v2_SOURCE.json')]
for role,_,source,manifest in items:
 subprocess.run(['python','-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--source',str(H/source),'--manifest',str(H/manifest),'--output',str(H/('FINAL_'+role+'_SOURCE_PREFLIGHT.json'))],check=True,capture_output=True)
subprocess.run(['python','-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--output',str(H/'FINAL_ROOT_DEFAULT_PREFLIGHT.json')],check=True,capture_output=True)
records=[]
for role,launch,_,_ in items:
 record=json.loads((H/launch).read_bytes());record['role']=role
 record['local_summary_sha256']=sha(H/'results'/role/'SUMMARY.json');record['local_gate_sha256']=sha(H/'results'/role/'GATE.json');records.append(record)
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
code='RECORDS='+repr(records)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,subprocess
rows=[]
for r in RECORDS:
 p=Path('/proc/'+str(r['pid'])+'/stat');same=p.exists() and p.read_text().split()[21]==r['start_ticks'];state=p.read_text().split()[2] if same else None
 executing=same and state not in ('Z','X');assert not executing
 O=Path(r['raw_result_location']);summary=O/'SUMMARY.json';gate=O/'GATE.json'
 assert hashlib.sha256(summary.read_bytes()).hexdigest()==r['local_summary_sha256'] and hashlib.sha256(gate.read_bytes()).hexdigest()==r['local_gate_sha256']
 assert json.loads(gate.read_bytes())['status'].startswith('PASS')
 rows.append(dict(role=r['role'],pid=r['pid'],start_ticks=r['start_ticks'],same_process_identity=same,state=state,executing=False,
  source_commit=r['code_commit'],raw_result_location=str(O),summary_sha256=r['local_summary_sha256'],gate_sha256=r['local_gate_sha256']))
g=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],capture_output=True,text=True)
print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS_FIVE_CPU_RUNS_COMPLETED_NO_OWN_ACTIVE_PROCESS',runs=rows,
 CUDA_compute_owners_observed=g.stdout.strip(),new_model_calls=0,scope='Read-only PID-generation and immutable-result observation; no process signalled or restarted')))
'''
with m.Remote() as c:raw=c.python(code,timeout=60)
j=json.loads(raw);j['CURRENT_sha256_before']=before;j['CURRENT_sha256_after']=sha(pointer);j['CURRENT_unchanged_during_closure']=before==sha(pointer)
assert j['CURRENT_unchanged_during_closure'];assert json.loads(pointer.read_bytes())['source_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
(H/'FINAL_CPU_RESOURCE_CLOSURE.json').write_text(json.dumps(j,indent=2)+'\n',encoding='utf8')
print(json.dumps(j))
