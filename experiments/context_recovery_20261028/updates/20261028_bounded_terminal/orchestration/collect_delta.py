"""Collect only terminal result trees, excluding environment/cache/test temp."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,stat,sys,tarfile,time
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
p=argparse.ArgumentParser();p.add_argument('--cut',required=True);p.add_argument('--native-snapshot');p.add_argument('stages',nargs='*');a=p.parse_args()
assert a.stages or a.native_snapshot
L=Path(r'D:\VLA_QWEN\RevTrace\experiments\context_recovery_20261028');D=L/a.cut
assert D.parent==L and not D.exists();D.mkdir()
O='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/freeze_boundary_20261027'
c=ssh_client()
try:
 s=c.open_sftp();s.get_channel().settimeout(60)
 def read(path):
  with s.open(path,'rb') as f:return f.read()
 def exists(path):
  try:s.stat(path);return True
  except FileNotFoundError:return False
 def walk(path):
  rows=[]
  for f in s.listdir_attr(path):
   q=path+'/'+f.filename
   assert not stat.S_ISLNK(f.st_mode)
   if stat.S_ISDIR(f.st_mode):
    if f.filename not in ['tmp','__pycache__','.pytest_cache']:rows+=walk(q)
   elif stat.S_ISREG(f.st_mode):rows.append((q,f.st_size))
  return rows
 files=[]
 for stage in a.stages:
  assert '/' not in stage and (exists(O+'/'+stage+'/GATE.json') or exists(O+'/'+stage+'/STOP.json')),'terminal evidence required'
  files+=walk(O+'/'+stage)
  for suffix in ['_HANDLE.json','_PRELAUNCH.json','_controller.log']:
   q=O+'/'+stage+suffix
   if exists(q):files.append((q,s.stat(q).st_size))
 if a.native_snapshot:
  assert '/' not in a.native_snapshot
  root=O+'/'+a.native_snapshot;progress=json.loads(read(root+'/PROGRESS.json'))
  (D/'NATIVE_PROGRESS_SNAPSHOT.json').write_text(json.dumps(dict(observed_unix=time.time(),progress=progress,scope='completed cell snapshot, not phase completion'),indent=2)+'\n')
  for r in progress['rows']:
   if r['execution_status']=='SKIPPED_PROVIDER_NO_GO':continue
   assert r['execution_status'] in ['COMPLETE','FAILED','FAILED_AUDIT']
   files+=walk(root+'/cells/'+r['id'])
  for name in ['FREEZE.json','ENVIRONMENT.json','SMOKE_PLAN.json','SELF_CHECK_REQUEST.json','SELF_CHECK_ENERGY.json','self_check_power.jsonl','self_check_stdout.txt','self_check_stderr.txt']:
   q=root+'/'+name
   if exists(q):files.append((q,s.stat(q).st_size))
  files+=walk(root+'/operator_self_check')
 assert sum(n for _,n in files)<250*1024*1024,'bounded source/raw only'
 index=[]
 class Reader:
  def __init__(self,f):self.f=f;self.h=hashlib.sha256();self.n=0
  def read(self,n):
   b=self.f.read(n);self.h.update(b);self.n+=len(b);return b
 archive=D/'COMPLETED_RAW_RECORDS.tar.gz'
 with tarfile.open(archive,'w:gz',compresslevel=6) as tar:
  for q,n in sorted(set(files)):
   name=str(PurePosixPath(q).relative_to(PurePosixPath(O)));info=tarfile.TarInfo(name);info.size=n;info.mode=0o644
   with s.open(q,'rb') as f:
    r=Reader(f);tar.addfile(info,r);assert r.n==n
   index.append(dict(path=name,bytes=n,sha256=r.h.hexdigest()))
 for stage in a.stages:
  for name in ['GATE.json','STOP.json','SUMMARY.json','RESULT.json','FREEZE.json','ENVIRONMENT.json']:
   if exists(O+'/'+stage+'/'+name):
    dest=D/stage/name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(read(O+'/'+stage+'/'+name))
 record=dict(status='COMPLETED_CELL_SNAPSHOT_NOT_PHASE_COMPLETE' if a.native_snapshot else 'TERMINAL_RAW_BYTE_COPY',stages=a.stages,native_snapshot=a.native_snapshot,files=index,raw_bytes=sum(x['bytes'] for x in index),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),archive_bytes=archive.stat().st_size,observed_unix=time.time(),scope='no models, audio, caches or environments; failures retained')
 (D/'RAW_INDEX.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps({k:v for k,v in record.items() if k!='files'},indent=2))
finally:c.close()
