"""Stream exact public assets to the designated disk; CDN signatures in memory."""
import base64,datetime,hashlib,json,os,pathlib,subprocess,sys,time,urllib.request,zipfile,struct,zlib,traceback
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
O=B/'results/revtrace/dsn_streamcorrect_20261028/assets_v1';O.mkdir(parents=True,exist_ok=True)
payload=json.load(sys.stdin);plan=payload['public_plan'];jobs=payload['jobs'];ranges=payload['range_jobs']
lock=O/'ACTIVE_DOWNLOAD_HANDLE.json'
if lock.exists():
 old=json.loads(lock.read_text());p=pathlib.Path('/proc')/str(old['pid'])
 if p.exists() and int((p/'stat').read_text().rsplit(')',1)[1].split()[19])==old['start_ticks']:raise RuntimeError('same acquisition process still live; no duplicate writer')
pid=os.getpid();ticks=int(pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
lock.write_text(json.dumps(dict(pid=pid,start_ticks=ticks,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())))
(O/'PUBLIC_PLAN.json').write_text(json.dumps(plan,indent=2))
record=dict(experiment_id=plan['experiment_id'],plan_sha256=payload['plan_sha256'],pid=pid,start_ticks=ticks,files=[])
def safe(p):
 p=pathlib.Path(p)
 if not p.is_absolute() or not p.is_relative_to(B) or '..' in p.parts:raise ValueError('asset target outside designated disk')
 p.parent.mkdir(parents=True,exist_ok=True);return p
def digest_file(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def validate(b,row):
 if len(b)!=row['bytes']:raise ValueError('small asset length mismatch')
 if row.get('sha256') and hashlib.sha256(b).hexdigest()!=row['sha256']:raise ValueError('small asset SHA mismatch')
 if row.get('git_blob_sha1') and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()!=row['git_blob_sha1']:raise ValueError('small asset original Git blob mismatch')
try:
 for job in jobs:
  row=job['public'];p=safe(row['path'])
  if p.exists():
   observed=digest_file(p)
   if p.stat().st_size!=row['bytes'] or (row.get('sha256') and observed!=row['sha256']):raise ValueError('existing final asset identity mismatch')
   if row.get('git_blob_sha1'):validate(p.read_bytes(),row)
   record['files'].append(dict(path=str(p),bytes=p.stat().st_size,sha256=observed,previous_complete=True));continue
  part=p.with_name(p.name+'.partial')
  if 'data_b64' in job:
   b=base64.b64decode(job['data_b64']);validate(b,row)
   with part.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
   observed=hashlib.sha256(b).hexdigest()
  else:
   pos=part.stat().st_size if part.exists() else 0
   if pos>row['bytes']:raise ValueError('oversize partial asset')
   h=hashlib.sha256();left=pos
   if pos:
    with part.open('rb') as f:
     for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
   headers={'Range':f'bytes={pos}-'} if pos else {}
   with urllib.request.urlopen(urllib.request.Request(job['download_url'],headers=headers),timeout=60) as response:
    if pos and (response.status!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {pos}-')):raise ValueError('server does not honor exact resume range')
    if not pos and response.status not in (200,206):raise ValueError('unexpected public download status')
    last=time.monotonic()
    with part.open('ab') as f:
     while True:
      b=response.read(8*1024*1024)
      if not b:break
      f.write(b);h.update(b);left+=len(b)
      if left>row['bytes']:raise ValueError('asset exceeds frozen length')
      if time.monotonic()-last>10:print(json.dumps(dict(progress=p.name,bytes=left,total=row['bytes'])),flush=True);last=time.monotonic()
     f.flush();os.fsync(f.fileno())
   if left!=row['bytes']:raise ValueError('incomplete public asset')
   observed=h.hexdigest()
   if row.get('sha256') and observed!=row['sha256']:raise ValueError('full public weight SHA mismatch')
  if p.exists():raise ValueError('never replace a final asset')
  part.rename(p);p.chmod(0o444)
  record['files'].append(dict(path=str(p),bytes=p.stat().st_size,sha256=observed))
  (O/'PROGRESS.json').write_text(json.dumps(record,indent=2));print(json.dumps(record['files'][-1]),flush=True)
 for job in ranges:
  row=job['public'];p=safe(row['path']);entry=row['entry']
  if p.exists():
   b=p.read_bytes()
  else:
   start=entry['local_offset'];stop=start+entry['compressed']+4095
   with urllib.request.urlopen(urllib.request.Request(job['download_url'],headers={'Range':f'bytes={start}-{stop}'}),timeout=60) as response:
    if response.status!=206:raise ValueError('archive server ignored exact range')
    b=response.read(entry['compressed']+4097)
   if len(b)>entry['compressed']+4096:raise ValueError('archive bounded range exceeded')
   v=struct.unpack_from('<4s5H3L2H',b);assert v[0]==b'PK\x03\x04';pos=30+v[-2]+v[-1]
   comp=b[pos:pos+entry['compressed']];b=zlib.decompress(comp,-15) if entry['method']==8 else comp
   if len(b)!=entry['bytes'] or zlib.crc32(b)!=entry['crc32']:raise ValueError('frozen public archive member mismatch')
   with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
   p.chmod(0o444)
  if len(b)!=entry['bytes'] or zlib.crc32(b)!=entry['crc32']:raise ValueError('final member CRC mismatch')
  record['files'].append(dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),archive_member=entry['path']))
  (O/'PROGRESS.json').write_text(json.dumps(record,indent=2));print(json.dumps(record['files'][-1]),flush=True)
 archive=B/'cache/revtrace_streamcorrect_20261028/large-v2-zh.pt.zip';target=safe(plan['model_root']+'/asr/large-v2-zh.pt')
 if not target.exists():
  part=target.with_name(target.name+'.partial')
  if part.exists():raise ValueError('partial decompression exists; inspect before explicitly restarting extraction')
  h=hashlib.sha256();size=0
  with zipfile.ZipFile(archive) as z,z.open('large-v2-zh.pt') as source,part.open('xb') as dest:
   for b in iter(lambda:source.read(8*1024*1024),b''):dest.write(b);h.update(b);size+=len(b)
   dest.flush();os.fsync(dest.fileno())
  if size!=6173691427:raise ValueError('native ASR uncompressed size mismatch')
  part.rename(target);target.chmod(0o444);observed=h.hexdigest()
 else:
  observed=digest_file(target);expected=None
  prior=O/'ASSET_MANIFEST.json'
  if prior.exists():
   expected=next((r['sha256'] for r in json.loads(prior.read_text())['files'] if r['path']==str(target)),None)
  if expected is None:
   h=hashlib.sha256()
   with zipfile.ZipFile(archive) as z,z.open('large-v2-zh.pt') as source:
    for b in iter(lambda:source.read(8*1024*1024),b''):h.update(b)
   expected=h.hexdigest()
  if observed!=expected or target.stat().st_size!=6173691427:raise ValueError('existing native ASR bytes differ from verified original archive')
 record['files'].append(dict(path=str(target),bytes=target.stat().st_size,sha256=observed,verified_parent_zip_sha256='ab30ddd181d1ab323711ea29d991f1d68ab9b6f0e43f5b8612f2dad6a65d07a4'))
 record.update(status='PASS_EXACT_NATIVE_ASSETS_ACQUIRED',finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),gpu_launched=False)
 (O/'ASSET_MANIFEST.json').write_text(json.dumps(record,indent=2));(O/'GATE.json').write_text(json.dumps(dict(status=record['status'],files=len(record['files']))))
 print(json.dumps(dict(status=record['status'],files=len(record['files']))),flush=True)
except BaseException as e:
 # Do not log signed CDN URLs from urllib diagnostics.
 diagnostic=dict(status='INCOMPLETE_ACQUISITION_PRESERVED',error=type(e).__name__,http_status=getattr(e,'code',None),
  python=sys.version,missing_attribute=getattr(e,'name',None),frames=[dict(file=f.filename,line=f.lineno,function=f.name) for f in traceback.extract_tb(e.__traceback__)])
 (O/'GATE.json').write_text(json.dumps(diagnostic));print(json.dumps(diagnostic),flush=True);raise SystemExit(1)
