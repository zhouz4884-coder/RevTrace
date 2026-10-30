"""Read-only terminal/count observation of postNN CPU analyses."""
import json,pathlib,sys
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';roots=dict(trace=B+'/results/revtrace/dsn_native_refinement_20261030/formal_actual36_v1',native=B+'/results/revtrace/dsn_native_resilience_20261030/native_work_recount_v1',export=B+'/results/revtrace/dsn_native_resilience_20261030/bounded_formal36_v3')
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 s=c.open_sftp();out={}
 for name,root in roots.items():
  out[name]={}
  for leaf in ('PROGRESS.json','GATE.json','results/GATE.json'):
   try:
    with s.open(root+'/'+leaf,'rb') as f:value=json.loads(f.read())
    out[name][leaf]={k:v for k,v in value.items() if k not in ('results','cells','plans')}
   except FileNotFoundError:pass
 s.close();print(json.dumps(out))
finally:c.close()
