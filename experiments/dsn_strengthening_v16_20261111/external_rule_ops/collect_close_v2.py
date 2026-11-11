"""Post-CPU closure and bounded output mirror, not another raw analysis."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1];H=E/'external_rule_ops';PACK=E/'external_rule_packages_v2'
launch=json.loads((H/'PROCESS_LAUNCH_V2.json').read_bytes());O=launch['raw_result_location']
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
with m.Remote() as c:
 code='L='+repr(launch)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,subprocess
p=Path('/proc/'+str(L['pid'])+'/stat');same=False
if p.exists():
 fields=p.read_text().rsplit(')',1)[1].split();same=fields[19]==L['start_ticks'] and fields[0]!='Z'
assert not same,'CPU process generation still active'
owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip();assert not owners,'CUDA owner exists at CPU closure'
O=Path(L['raw_result_location']);g=json.loads((O/'GATE.json').read_bytes());assert g['status']=='PASS_COMPLETE_ALL24_OFFLINE_EXTERNAL_RULE_ADAPTER'
files=[dict(name=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(O.iterdir()) if p.is_file()]
assert sum(x['bytes'] for x in files)<=12000000
print(json.dumps(dict(record_type='CPU_RESOURCE_CLOSURE_AND_BOUNDED_OUTPUT_INDEX',pid=L['pid'],start_ticks=L['start_ticks'],CPU_generation_active=False,CUDA_compute_PIDs=[],new_model_calls=0,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),gate=g,files=files,total_bytes=sum(x['bytes'] for x in files))))
'''
 raw=c.python(code,timeout=60);record=json.loads(raw);(H/'CPU_RESOURCE_CLOSURE_V2.json').write_bytes(raw+b'\n')
 out=H/'RESULTS_V2';out.mkdir(exist_ok=False)
 for f in record['files']:
  data=c.get(O+'/'+f['name'],out/f['name'],maximum=12000000)
  assert len(data)==f['bytes'] and hashlib.sha256(data).hexdigest()==f['sha256']
 (out/'DOWNLOAD_VERIFICATION.json').write_text(json.dumps(dict(files=len(record['files']),bytes=record['total_bytes'],all_hashes_match=True),indent=2)+'\n',encoding='utf8')
for args in (['--output',str(H/'FINAL_DEFAULT_SOURCE_GATE_V2.json')],['--source',str(E/'external_rule_source_v2'),'--manifest',str(PACK/'SOURCE.json'),'--output',str(H/'FINAL_ANALYSIS_SOURCE_GATE_V2.json')]):
 subprocess.run(['python','-B',str(R/'experiments/repository_identity_20261027/preflight.py'),*args],check=True,capture_output=True)
print(json.dumps({k:v for k,v in record.items() if k!='files'}))
