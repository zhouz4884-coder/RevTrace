"""Closed8TB evidence index and exact owned-resource check; never kills work."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
B=Path(sys.argv[1]);P=B/'projects/revtrace_ces_20261023';O=B/'results/revtrace/ces_20261023'
assert json.loads((O/'POST_SUMMARY.json').read_text())['status']=='ALL_FORMAL_CPU_AUDITS_AND_STATISTICS_COMPLETE'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(8*1024*1024),b''):h.update(x)
 return h.hexdigest()
assert not (O/'RAW_EVIDENCE_INDEX.json').exists()
source=json.loads((P/'runtime_v4/SOURCE_MANIFEST.json').read_text())
for r in source['files']:assert sha(P/'runtime_v4'/r['path'])==r['sha256']
expected={'model-00001-of-00002.safetensors':'a4cd1f1a04d90b757dc7f7dd26254e69a013b19e80efe590a83c6a3bde8608d6',
 'model-00002-of-00002.safetensors':'6e0b9d9e09e2e0238e7ef3cc8a484ab387e91b90f1900bedf88bc92d7929ccfc'}
assert {n:sha(B/'models/Qwen3-ASR-1.7B'/n) for n in expected}==expected
owned_alive=[];handles=0
for f in O.glob('*/**/OWNED_WORKER_HANDLES.json'):
 for h in json.loads(f.read_text()):
  handles+=1;proc=Path('/proc')/str(h['pid'])
  if not proc.exists():continue
  try:
   ticks=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]
   if ticks==h['linux_start_ticks'] and sha(proc/'cmdline')==h['command_sha256']:owned_alive.append(h)
  except FileNotFoundError:pass
assert not owned_alive,owned_alive
controllers=[]
for name in ['FORMAL_PID.json','PILOT_PID_v1.json','PILOT_PID_v2.json','PILOT_PID_v3.json','PILOT_PID_v4.json']:
 h=json.loads((O/name).read_text());proc=Path('/proc')/str(h['pid']);cmd=proc.joinpath('cmdline').read_bytes() if proc.exists() else b''
 own=str(P).encode() in cmd and (b'run_formal.py' in cmd or b'run_pilot' in cmd)
 assert not own,(name,h['pid']);controllers.append({'record':name,'pid':h['pid'],'original_command_not_running':True})
files=[];exclusions=[]
for root in [P,O]:
 for f in sorted(root.rglob('*')):
  if not f.is_file():continue
  if f.name.endswith(('.partial','.lock')) or '__pycache__' in f.parts or '.pytest_cache' in f.parts:
   exclusions.append(str(f));continue
  files.append({'path':str(f),'bytes':f.stat().st_size,'sha256':sha(f)})
index={'status':'CLOSED_RAW_PROJECT_AND_RESULT_INDEX','roots':[str(P),str(O)],'files':files,
 'explicit_ephemeral_exclusions':exclusions,'model_weights_unchanged':expected,'source_commit':source['code_commit'],
 'self_and_later_index_summary_not_indexed':True}
(O/'RAW_EVIDENCE_INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True)
summary={'status':'PASS_SOURCE_MODELS_RAW_INDEX_AND_OWN_GPU_RELEASE','files':len(files),'bytes':sum(r['bytes'] for r in files),
 'index_sha256':sha(O/'RAW_EVIDENCE_INDEX.json'),'source_commit':source['code_commit'],
 'worker_handles_verified_not_alive':handles,'controllers':controllers,'current_GPU_apps':gpu,
 'GPU_observed_idle':not gpu.strip(),'foreign_work_not_touched':True,'no_new_GPU_issuance':True}
(O/'INDEX_AND_RELEASE_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
