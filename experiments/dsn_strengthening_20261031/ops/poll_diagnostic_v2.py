"""Read-only poll, using the exact launched PID generation and output."""
import json,pathlib,shlex,sys
E=pathlib.Path(__file__).resolve().parents[1];d=json.loads((E/'DIAG_STAGED_v2.json').read_bytes());h=json.loads((E/'DIAG_HANDLE_v2.json').read_bytes())
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
script='C='+repr(d)+'\nH='+repr(h)+'\n'+r'''
import hashlib,json,pathlib
out=pathlib.Path(C['results']);proc=pathlib.Path('/proc')/str(H['pid']);alive=False;state=None
if proc.exists():
 fields=(proc/'stat').read_text().rsplit(')',1)[1].split();state=fields[0]
 if state not in ('Z','X'):
  assert int(fields[19])==H['start_ticks'] and hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()==H['cmdline_sha256'],'PID generation changed'
  alive=True
result=dict(alive=alive,process_state=state,new_model_calls=0)
for name in ('PROGRESS.json','GATE.json'):
 p=out/name
 if p.exists():
  try:result[name]=json.loads(p.read_bytes())
  except json.JSONDecodeError:result[name]='WRITE_IN_PROGRESS'
log=pathlib.Path(H['log'])
if log.exists():result['log_tail']=log.read_text(errors='replace')[-4500:]
print(json.dumps(result))
'''
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(d['python'])+' -B -',timeout=30);i.write(script);i.flush();i.channel.shutdown_write();raw=o.read();err=e.read();rc=o.channel.recv_exit_status();assert rc==0,err.decode('utf8',errors='replace');print(raw.decode())
finally:c.close()
