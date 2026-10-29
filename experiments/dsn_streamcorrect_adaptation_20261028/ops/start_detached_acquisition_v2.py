"""Renew public URLs in RAM, hand payload to detached disk worker via pipe."""
import base64,datetime,hashlib,json,pathlib,shlex,sys,urllib.request,time
T=pathlib.Path(__file__).resolve().parents[1];plan_path=T/'download_plan_v1/PLAN.json';plan=json.loads(plan_path.read_text())
jobs=[];ranges=[]
def open_retry(request):
 for attempt in range(5):
  try:return urllib.request.urlopen(request,timeout=45)
  except Exception as e:
   print(json.dumps(dict(phase='public_route_retry',attempt=attempt+1,error=type(e).__name__)),flush=True)
   if attempt==4:raise RuntimeError('public route renewal failed; no remote child launched') from None
   time.sleep(min(4.,.5*2**attempt))
def small_cached(row):
 name=pathlib.PurePosixPath(row['path']).name;candidates=[]
 if '/ultravox_b95bec8/' in row['path']:candidates.append(T/'asset_inventory_v2'/name)
 if '/llama32_1b_instruct_f8e6b/' in row['path']:
  if name=='config.json':candidates.append(T/'modelscope_metadata_v1/response_4.json')
  if name=='LICENSE.txt':candidates.append(T/'modelscope_metadata_v1/response_5.json')
 for p in candidates:
  if not p.is_file():continue
  b=p.read_bytes()
  if len(b)!=row['bytes']:continue
  if row.get('sha256') and hashlib.sha256(b).hexdigest()!=row['sha256']:continue
  if row.get('git_blob_sha1') and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()!=row['git_blob_sha1']:continue
  return b
 return None
for row in plan['files']:
 print(json.dumps(dict(phase='renew_public_download_route',asset=pathlib.PurePosixPath(row['path']).name)),flush=True)
 job={'public':row};url=row['url']
 if row['bytes']>100000 and 'huggingface.co/' in url:url+=('&' if '?' in url else '?')+'download=true'
 cached=small_cached(row) if row['bytes']<=100000 else None
 if cached is not None:job['data_b64']=base64.b64encode(cached).decode()
 else:
  with open_retry(url) as r:
   if row['bytes']<=100000:
    b=r.read(100001);assert len(b)==row['bytes'];job['data_b64']=base64.b64encode(b).decode()
   else:r.read(1);job['download_url']=r.geturl()
 jobs.append(job)
for row in plan['range_files']:
 entry=row['entry'];a=entry['local_offset'];b=a+entry['compressed']+4095
 print(json.dumps(dict(phase='renew_public_archive_route',asset=pathlib.PurePosixPath(row['path']).name)),flush=True)
 with open_retry(urllib.request.Request(row['url'],headers={'Range':f'bytes={a}-{b}'})) as r:
  assert r.status==206;r.read(1);url=r.geturl()
 ranges.append(dict(public=row,download_url=url))
payload=dict(public_plan=plan,plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),jobs=jobs,range_jobs=ranges)
parent_code='''import pathlib,json,subprocess,sys,os,hashlib,datetime
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028/assets_v1'
payload=json.load(sys.stdin)
h=O/'ACTIVE_DOWNLOAD_HANDLE.json'
if h.exists():
 old=json.loads(h.read_text());p=pathlib.Path('/proc')/str(old['pid'])
 if p.exists() and int((p/'stat').read_text().rsplit(')',1)[1].split()[19])==old['start_ticks']:raise RuntimeError('old exact writer still alive; no duplicate launch')
log=O/'acquisition_attempt03_detached.log';assert not log.exists()
command=[str(B/'envs/revbatch-cu128/bin/python'),'-B',str(P/'asset_acquisition_worker_v2.py')]
with log.open('x') as f:
 child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
 child.stdin.write(json.dumps(payload).encode());child.stdin.close()
proc=pathlib.Path('/proc')/str(child.pid)
record=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),safe_log=str(log),worker=str(P/'asset_acquisition_worker_v2.py'),payload_route='anonymous stdin pipe only; no signed URLs in argv/files',detached=True)
(O/'DETACHED_LAUNCH_HANDLE_attempt03.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))'''
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revbatch-cu128/bin/python -B -c '+shlex.quote(parent_code),timeout=90)
 i.write(json.dumps(payload));i.flush();i.channel.shutdown_write()
 b=o.read().decode();err=e.read().decode();rc=o.channel.recv_exit_status()
 if rc or err:raise RuntimeError('detached launch failed; inspect public launcher record (temporary URL diagnostics suppressed)')
 handle=json.loads(b);folder=T/'acquisition_attempt03';folder.mkdir(exist_ok=False);(folder/'HANDLE.json').write_text(json.dumps(handle,indent=2))
 status_path=T/'CURRENT_STATUS.json';s=json.loads(status_path.read_text());s.update(status='ACTIVE_DETACHED_ASSET_ACQUISITION',heavy_io_started=True,acquisition=handle,native_neural_calls=0,formal_application_service_cells_completed=0)
 status_path.write_text(json.dumps(s,indent=2));print(json.dumps(handle,indent=2))
finally:c.close()
