"""CPU-only actual-crash audit chain; does not start another GPU experiment."""
from pathlib import Path
import hashlib,json,subprocess,sys
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/n5_v3'
O=B/'results/revtrace/dependability_20261025/n5_v3_supervisor_v2'
def read(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,v):
 t=p.with_name(p.name+'.partial');t.write_text(json.dumps(v,indent=2)+'\n');t.replace(p)
def live(h):
 p=Path('/proc')/str(h['pid'])
 if not p.exists():return False
 s=p.joinpath('stat').read_text().rsplit(')',1)[1].split();return s[19]==str(h.get('start_ticks',h.get('linux_start_ticks'))) and s[0]!='Z'
def main():
 launch=read(O/'FORMAL_FAULT_LAUNCH.json');assert not live(launch)
 done=read(O/'formal_fault/SUMMARY.json');assert done['cells']==done['expected']==len(set(done['completed']))==21
 assert not (O/'formal_fault/STOP.json').exists()
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
 dest=O/'postfault_cpu_v1';dest.mkdir(exist_ok=False)
 m=read(P/'runtime/SOURCE_MANIFEST.json')
 for r in m['files']:assert sha(P/'runtime'/r['path'])==r['sha256']
 handles=[]
 for name in done['completed']:
  for attempt in [0,1]:
   for h in read(O/'formal_fault'/name/f'attempt{attempt}/OWNED_WORKER_HANDLES.json'):
    assert not live(h);handles.append(dict(h,verified_exited_or_zombie=True))
 save(dest/'RELEASE.json',dict(status='PASS21_TWO_ATTEMPTS_84_OWNED_WORKER_EXIT',handles=handles))
 files=[]
 for p in (O/'formal_fault').rglob('*'):
  if p.is_file():p.resolve().relative_to(O.resolve());files.append(dict(path=p.relative_to(O).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
 save(dest/'FAULT_RAW_INDEX_v1.json',dict(files=files))
 complete=[]
 try:
  sys.path.insert(0,str(P/'runtime/scripts'));from audit_dsn_journal import audit
  checks=[]
  for name in done['completed']:
   E=O/'formal_fault'/name;before=sha(E/'canonical.wal');first=audit(E/'canonical.wal')
   r=audit(E/'canonical.wal',E/'attempt1',expected_prior_commits=first['commits_before_latest_restart'])
   assert sha(E/'canonical.wal')==before and r['restart_epochs']==1;checks.append(dict(episode=name,audit=r))
  save(dest/'WAL_REPLAY_v1.json',dict(status='PASS21_READ_ONLY_CANONICAL_RESTART_AND_DEDUP_REPLAY',checks=checks,new_neural_GPU_calls=0));complete.append('WAL21')
  commands=[('PRIMARY21',[sys.executable,str(P/'audit_n5_fault_formal_v1.py'),'--root',str(O),
   '--runtime-manifest',str(P/'runtime/SOURCE_MANIFEST.json'),'--output',str(dest/'PRIMARY_v1.json')]),
   ('ASSETS42_ATTEMPTS',[sys.executable,str(P/'audit_n5_fault_assets_v1.py'),'--root',str(O),'--manifest',str(P/'INDEPENDENT_MANIFEST_v1.json'),
    '--model',str(B/'models/Qwen3-ASR-1.7B'),'--output',str(dest/'ASSETS_v1.json')])]
  for label,cmd in commands:
   save(dest/'PROGRESS.json',dict(status='RUNNING_CPU_ONLY',stage=label,completed=complete))
   with (dest/(label+'.log')).open('xb') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True,cwd=P)
   complete.append(label)
  save(dest/'SUMMARY.json',dict(status='PASS21_FORMAL_RECOVERY_WAL_PRIMARY_AND_ACTUAL_ASSETS',completed=complete,
   raw_files=len(files),raw_bytes=sum(r['bytes'] for r in files),new_neural_GPU_calls=0,
   limits='process-group cold restart, not host/power/network exactly-once display or any universal RTO'))
 except BaseException as e:save(dest/'STOP.json',dict(error=repr(e),completed=complete,raw_retained=True));raise
if __name__=='__main__':main()
