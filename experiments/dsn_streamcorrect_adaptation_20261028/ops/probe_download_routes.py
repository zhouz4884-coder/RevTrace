"""One-byte public download checks, with CDN URLs kept only in memory."""
import pathlib,json,urllib.request,sys,shlex,datetime
T=pathlib.Path(__file__).resolve().parents[1];O=T/'download_route_probe_v1';O.mkdir(exist_ok=False)
plan=json.loads((T/'download_plan_v1/PLAN.json').read_text());rows=[];remote_jobs=[]
for key in ('model.safetensors','large-v2-zh.pt.zip'):
 item=next(x for x in plan['files'] if x['path'].endswith(key))
 req=urllib.request.Request(item['url'],headers={'Range':'bytes=0-0'})
 try:
  with urllib.request.urlopen(req,timeout=35) as r:
   first=r.read(1);final=r.geturl();rows.append(dict(path=item['path'],local_status=r.status,first_byte=len(first)))
   remote_jobs.append(dict(path=item['path'],url=final,range='bytes=0-0'))
 except Exception as e:rows.append(dict(path=item['path'],local_error=type(e).__name__))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
code='''import sys,json,urllib.request,urllib.parse
out=[]
for x in json.load(sys.stdin):
 r={"path":x["path"],"cdn_host":urllib.parse.urlparse(x["url"]).hostname}
 try:
  with urllib.request.urlopen(urllib.request.Request(x["url"],headers={"Range":x["range"]}),timeout=25) as a:
   r.update(status=a.status,first_byte=len(a.read(1)))
 except Exception as e:r.update(error=type(e).__name__,http_status=getattr(e,"code",None))
 out.append(r)
print(json.dumps(out))'''
try:
 i,o,e=c.exec_command('python3 -B -c '+shlex.quote(code),timeout=60);i.write(json.dumps(remote_jobs));i.flush();i.channel.shutdown_write()
 b=o.read().decode();err=e.read().decode();rc=o.channel.recv_exit_status();assert not err,(rc,'remote public probe diagnostic')
 summary=dict(time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='one byte per route; no model writes and no GPU',local=rows,remote=json.loads(b),returncode=rc)
 (O/'SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
finally:c.close()
