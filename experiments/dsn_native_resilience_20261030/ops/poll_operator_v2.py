"""Exact frozen-operator progress; observation does not restart or collect large logs."""
import json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];h=json.loads((F/'OPERATOR_PILOT_HANDLE_v2.json').read_bytes())
script=r"""import pathlib,json,hashlib
h=HANDLE;p=pathlib.Path('/proc')/str(h['pid']);r=dict(pid=h['pid'],alive=p.exists())
if p.exists():
 s=(p/'stat').read_text().rsplit(')',1)[1].split();r.update(state=s[0],exact_start=int(s[19])==h['start_ticks'],exact_command=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==h['cmdline_sha256'])
out=pathlib.Path(h['out'])
for name in ('PROGRESS.json','GATE.json'):
 q=out/name
 if q.exists():
  try:r[name]=json.loads(q.read_bytes())
  except json.JSONDecodeError:r[name]='temporarily partial; not worker death'
if (out/'GATE.json').exists():
 log=pathlib.Path(h['log'])
 with log.open('rb') as f:f.seek(max(0,log.stat().st_size-6000));r['log_tail']=f.read().decode(errors='replace')
print(json.dumps(r))
""".replace('HANDLE',repr(h))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(h['command'][0])+' -B -',timeout=15);i.write(script);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();assert o.channel.recv_exit_status()==0,err.decode();print(b.decode())
finally:c.close()

