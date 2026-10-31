from pathlib import Path
import hashlib,json,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_dsn_writing_closure_20261031'
read=lambda p:json.loads(Path(p).read_bytes())
files=[];phases=[]
for mode in ('controls','complete20'):
 cfg=read(P/('CONTENT_'+mode.upper()+'_v4_FROZEN.json'));root=Path(cfg['intended_output'])
 phases.append(dict(mode=mode,gate=read(root/'GATE.json') if (root/'GATE.json').exists() else None))
 if root.exists():
  for path in sorted(root.iterdir()):
   if path.is_file():files.append(dict(path=str(path),relative=mode+'/'+path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
 for path,label in [(Path(cfg['stdout_path']),mode+'/CLI_STDOUT.json'),(Path(cfg['stderr_path']),mode+'/CLI_STDERR.log')]:
  if path.exists():files.append(dict(path=str(path),relative=label,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
for name in ['CONTENT_CONTROLS_v4_FROZEN.json','CONTENT_COMPLETE20_v4_FROZEN.json','ENVIRONMENT_CONTENT_v4_FROZEN.json','ROOT_NOARG_CONTENT_CPU_v4.json','PRELAUNCH_CONTROLS_v4.json','PRELAUNCH_COMPLETE20_v4.json','FORMAL_CONTENT_CPU_EXECUTION_RECEIPT_v4.json']:
 path=P/name
 if path.exists():files.append(dict(path=str(path),relative='prelaunch/'+name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=10).strip()
assert not gpu,'GPU work must remain absent'
leases=[]
for mode in ('controls','complete20'):
 cfg=read(P/('CONTENT_'+mode.upper()+'_v4_FROZEN.json'));assert not Path(cfg['lease_path']).exists()
print(json.dumps(dict(phases=phases,files=files,total_bytes=sum(r['bytes'] for r in files),GPU_compute_owners_empty=True,CPU_experiment_leases_released=True,new_model_calls=0)))
