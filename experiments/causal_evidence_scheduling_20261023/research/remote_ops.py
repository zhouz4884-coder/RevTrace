"""Scoped approved SSH transport. Credential remains in helper memory."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,importlib.util,json,time
W=Path(__file__).resolve().parent
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
spec=importlib.util.spec_from_file_location('approved',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
p=argparse.ArgumentParser();p.add_argument('--script',type=Path);p.add_argument('--put',type=Path)
p.add_argument('--remote');p.add_argument('--get');p.add_argument('--local',type=Path);p.add_argument('--timeout',type=float,default=45)
a=p.parse_args();c=h.ssh_client();log={'time_unix':time.time()};(W/'operations').mkdir(exist_ok=True)
try:
 if a.script:
  raw=a.script.read_bytes();log['script_sha256']=hashlib.sha256(raw).hexdigest()
  i,o,e=c.exec_command('bash --noprofile --norc -s',timeout=a.timeout);i.write(raw);i.channel.shutdown_write()
  out=o.read().decode(errors='replace');err=e.read().decode(errors='replace');rc=o.channel.recv_exit_status()
  log.update(stdout=out,stderr=err,exit_code=rc);print(out);print(err);assert rc==0
 else:
  target=a.remote if a.put else a.get;q=PurePosixPath(target)
  assert q.is_absolute() and '..' not in q.parts
  assert any(target.startswith(B+'/'+part+'/') for part in ['projects/revtrace_ces_20261023','results/revtrace/ces_20261023'])
  f=c.open_sftp()
  if a.put:
   assert a.put.stat().st_size<50_000_000
   try:f.stat(target);raise RuntimeError('Refuse overwrite')
   except FileNotFoundError:pass
   f.put(str(a.put),target);log.update(upload=target,sha256=hashlib.sha256(a.put.read_bytes()).hexdigest())
  else:
   assert not a.local.exists() and f.stat(target).st_size<100_000_000
   f.get(target,str(a.local));log.update(download=target,sha256=hashlib.sha256(a.local.read_bytes()).hexdigest())
finally:
 c.close();(W/'operations'/(str(time.time_ns())+'.json')).write_text(json.dumps(log,indent=2)+'\n')
