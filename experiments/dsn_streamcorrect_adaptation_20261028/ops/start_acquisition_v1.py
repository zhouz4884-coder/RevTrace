"""Run only after the root's idle-window release. No public weights on Windows."""
import base64,hashlib,json,pathlib,shlex,sys,urllib.request
T=pathlib.Path(__file__).resolve().parents[1];plan_path=T/'download_plan_v1/PLAN.json';plan=json.loads(plan_path.read_text())
jobs=[];ranges=[]
for row in plan['files']:
 job={'public':row}
 request_url=row['url']
 if row['bytes']>100000 and 'huggingface.co/' in request_url:
  request_url+=('&' if '?' in request_url else '?')+'download=true'
 with urllib.request.urlopen(request_url,timeout=45) as r:
  if row['bytes']<=100000:
   b=r.read(100001);assert len(b)==row['bytes'];job['data_b64']=base64.b64encode(b).decode()
  else:r.read(1);job['download_url']=r.geturl()
 jobs.append(job)
for row in plan['range_files']:
 entry=row['entry'];a=entry['local_offset'];b=a+entry['compressed']+4095
 with urllib.request.urlopen(urllib.request.Request(row['url'],headers={'Range':f'bytes={a}-{b}'}),timeout=45) as r:
  assert r.status==206;r.read(1);url=r.geturl()
 ranges.append(dict(public=row,download_url=url))
payload=dict(public_plan=plan,plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),jobs=jobs,range_jobs=ranges)
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 code=(T/'ops/remote_acquire_assets.py').read_text();i,o,e=c.exec_command('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revbatch-cu128/bin/python -B -c '+shlex.quote(code),timeout=7200)
 i.write(json.dumps(payload));i.flush();i.channel.shutdown_write()
 while True:
  line=o.readline()
  if not line:break
  print(line,end='',flush=True)
 err=e.read().decode();rc=o.channel.recv_exit_status()
 if err:print('Remote acquisition diagnostic suppressed to avoid logging temporary CDN URLs; inspect GATE.json error type.',file=sys.stderr)
 raise SystemExit(rc)
finally:c.close()
