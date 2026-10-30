"""Tiny exact-handle observation; never restarts a worker."""
import hashlib,json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];h=json.loads((F/'FIRST_CELL_HANDLE_v1.json').read_bytes())
script=r"""import pathlib,json,hashlib
h=HANDLE;p=pathlib.Path('/proc')/str(h['pid']);r=dict(pid=h['pid'],alive=p.exists())
if p.exists():
 s=(p/'stat').read_text().rsplit(')',1)[1].split();r.update(state=s[0],start_ticks=int(s[19]),cmdline_sha256=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest());r['exact_identity']=r['start_ticks']==h['start_ticks'] and (r['cmdline_sha256']==h['cmdline_sha256'] or r['state']=='Z')
out=pathlib.Path(h['out'])
for name in ('GATE.json','METRICS_GATE.json','SUMMARY.json'):
 q=out/name
 if q.exists():
  d=json.loads(q.read_bytes());r[name]={k:d.get(k) for k in ('status','gate','cell_id','primary','integrity') if k in d} if name=='SUMMARY.json' else d
log=pathlib.Path(h['log'])
if log.exists():
 with log.open('rb') as f:f.seek(max(0,log.stat().st_size-2500));r['log_tail']=f.read().decode(errors='replace')
print(json.dumps(r))
""".replace('HANDLE',repr(h))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(h['command'][0])+' -B -',timeout=15);i.write(script);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();rc=o.channel.recv_exit_status();assert rc==0,err.decode();print(b.decode())
finally:c.close()

