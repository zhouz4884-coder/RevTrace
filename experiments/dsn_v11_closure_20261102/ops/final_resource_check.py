"""Final administrative readback: original bytes, original process generations, GPU empty."""
import json
from remote import Remote,E,B,P,O
handles=[json.loads((E/'handles'/n).read_bytes()) for n in ['TRACE_RUN_V1_HANDLE.json','TRACE_RUN_V3_HANDLE.json']]
script='C='+repr(dict(handles=handles,index=P+'/RAW_INDEX_v1.json',after=O+'/trace_accounting_v3/INPUT_HASHES_AFTER.json',out=O+'/FINAL_RESOURCE_AND_RAW_CLOSURE.json',nn=B+'/projects/revtrace_dsn_native_resilience_20261030/source_v2',manifest=B+'/projects/revtrace_dsn_native_resilience_20261030/SOURCE_v2.json'))+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,subprocess
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def proc(h):
 p=Path('/proc')/str(h['pid'])/'stat'
 if not p.exists():return dict(pid=h['pid'],original_start_ticks=h['start_ticks'],original_process_alive=False,state='absent')
 s=p.read_text().split();same=int(s[21])==h['start_ticks'];alive=same and s[2] not in ('Z','X')
 return dict(pid=h['pid'],original_start_ticks=h['start_ticks'],current_start_ticks=int(s[21]),original_process_alive=alive,state=s[2])
rows=[proc(h) for h in C['handles']];assert not any(r['original_process_alive'] for r in rows)
owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True).strip();assert not owners
after=json.loads(Path(C['after']).read_bytes())
for p,m in after.items():assert Path(p).stat().st_size==m['bytes'] and sha(p)==m['sha256'],p
assert len(after)==420
m=json.loads(Path(C['manifest']).read_bytes());assert m['code_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
assert subprocess.check_output(['git','-C',C['nn'],'rev-parse','HEAD'],text=True).strip()==m['code_commit']
assert not subprocess.check_output(['git','-C',C['nn'],'status','--porcelain','--untracked-files=all'],text=True).strip()
for r in m['files']:assert sha(Path(C['nn'])/r['path'])==r['sha256']
record=dict(status='PASS_FINAL_RECORDED_INPUTS_SOURCE_AND_RESOURCE_READBACK',verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),original_recorded_inputs_verified=len(after),input_after_manifest_sha256=sha(C['after']),original_NN_source=m['code_commit'],original_NN_files_verified=len(m['files']),original_NN_source_clean=True,CPU_controllers=rows,CUDA_compute_owners=owners,new_model_calls=0,scope='Read-only final administrative verification; no process signalled, restarted or model loaded')
with Path(C['out']).open('x') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(record))
'''
with Remote() as c:
 raw=c.python(script);c.get(O+'/FINAL_RESOURCE_AND_RAW_CLOSURE.json',E/'FINAL_RESOURCE_AND_RAW_CLOSURE.json');print(raw.decode())
