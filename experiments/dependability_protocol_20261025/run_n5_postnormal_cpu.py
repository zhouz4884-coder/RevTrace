"""One bounded CPU audit chain, only after the exact 105-cell GPU owner exits."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_dependability_20261025/n5_v3';O=B/'results/revtrace/dependability_20261025/n5_v3_supervisor_v2'
def read(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(4*1024*1024),b''):h.update(x)
 return h.hexdigest()
def save(p,d):
 t=p.with_name(p.name+'.partial');t.write_text(json.dumps(d,indent=2)+'\n');t.replace(p)
def live(h):
 p=Path('/proc')/str(h['pid'])
 if not p.exists():return False
 s=p.joinpath('stat').read_text().rsplit(')',1)[1].split()
 return s[19]==str(h.get('start_ticks',h.get('linux_start_ticks'))) and s[0]!='Z'
def main():
 stage=O/'formal_normal';done=read(stage/'SUMMARY.json');launch=read(O/'FORMAL_NORMAL_LAUNCH.json')
 assert done['cells']==done['expected']==len(set(done['completed']))==105 and not (stage/'STOP.json').exists()
 assert not live(launch)
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
 dest=O/'postnormal_cpu_v1';dest.mkdir(exist_ok=False)
 m=read(P/'runtime/SOURCE_MANIFEST.json')
 for r in m['files']:assert sha(P/'runtime'/r['path'])==r['sha256']
 for name in ['INDEPENDENT_MANIFEST_v1.json','DEVELOPMENT_MANIFEST.json']:
  target=O/name;assert not target.exists();target.write_bytes((P/name).read_bytes())
 released=[]
 for name in done['completed']:
  for h in read(stage/name/'attempt0/OWNED_WORKER_HANDLES.json'):
   assert not live(h);released.append(dict(h,verified_exited_or_zombie=True))
 save(dest/'RELEASE_AND_SOURCE.json',dict(status='PASS105_COMPLETENESS_AND_210_OWNED_WORKER_EXIT',runtime_commit=m['code_commit'],owned=released))
 index=[]
 for p in stage.rglob('*'):
  if p.is_file():
   p.resolve().relative_to(O.resolve());assert not p.name.lower().endswith(('.flac','.wav','.safetensors'))
   index.append(dict(path=p.relative_to(O).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
 save(dest/'NORMAL_RAW_INDEX_v1.json',dict(files=index,scope='authoritative raw remains on8TB; bounded hashes, not a serving result'))
 commands=[('PRIMARY', [sys.executable,str(P/'audit_n5_formal_v1.py'),'--root',str(O),'--stage','formal_normal',
   '--runtime-manifest',str(P/'runtime/SOURCE_MANIFEST.json'),'--output',str(dest/'primary')]),
  ('NORMAL_ASSETS',[sys.executable,str(P/'audit_assets_n5.py'),'--stage',str(stage),'--manifest',str(P/'INDEPENDENT_MANIFEST_v1.json'),
   '--model',str(B/'models/Qwen3-ASR-1.7B'),'--output',str(dest/'NORMAL_ASSET_REPLAY_v1.json')]),
  ('RECOVERY_ASSETS',[sys.executable,str(P/'audit_n5_recovery_assets.py'),'--root',str(O),'--manifest',str(P/'DEVELOPMENT_MANIFEST.json'),
   '--model',str(B/'models/Qwen3-ASR-1.7B'),'--output',str(dest/'RECOVERY_ASSET_REPLAY_v1.json')])]
 completed=[]
 try:
  sys.path.insert(0,str(P/'runtime/scripts'));from audit_dsn_journal import audit
  wal=[]
  for name in done['completed']:
   E=stage/name;f=E/'canonical.wal';before=sha(f);r=audit(f,E/'attempt0');assert sha(f)==before
   wal.append(dict(episode=name,audit=r))
  save(dest/'NORMAL_WAL_REPLAY_v1.json',dict(status='PASS105_READ_ONLY_EXISTING_ADMISSION_REPLAY',checks=wal,new_neural_GPU_calls=0))
  for label,cmd in commands:
   save(dest/'PROGRESS.json',dict(stage=label,completed=completed,status='RUNNING_CPU_ONLY'))
   with (dest/(label+'.log')).open('xb') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True,cwd=P)
   completed.append(label)
  save(dest/'SUMMARY.json',dict(status='PASS105_PRIMARY_WAL_ASSETS_AND_RECOVERY_ASSETS',completed=completed,
   runtime_commit=m['code_commit'],raw_files=len(index),raw_bytes=sum(r['bytes'] for r in index),new_neural_GPU_calls=0,
   note='formal_fault still requires main-agent independent GO_SAFETY_ONLY; this does not launch GPU'))
 except BaseException as e:
  save(dest/'STOP.json',dict(error=repr(e),completed=completed,all_raw_retained=True,no_automatic_retry=True));raise
if __name__=='__main__':main()
