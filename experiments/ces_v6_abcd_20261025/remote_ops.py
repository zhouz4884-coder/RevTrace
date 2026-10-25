"""Scoped experiment transport using the existing authorized credential route."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,importlib.util,json,time,os
W=Path(__file__).resolve().parent;B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
spec=importlib.util.spec_from_file_location('approved',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
p=argparse.ArgumentParser();p.add_argument('--script',type=Path);p.add_argument('--put',type=Path);p.add_argument('--get')
p.add_argument('--remote');p.add_argument('--local',type=Path);p.add_argument('--timeout',type=float,default=55)
a=p.parse_args();record={'time_unix':time.time()};(W/'operations').mkdir(exist_ok=True);client=None
try:
 client=helper.ssh_client()
 if a.script:
  raw=a.script.read_bytes();record['script_sha256']=hashlib.sha256(raw).hexdigest()
  i,o,e=client.exec_command('bash --noprofile --norc -s',timeout=a.timeout);i.write(raw);i.channel.shutdown_write()
  out=o.read().decode(errors='replace');err=e.read().decode(errors='replace');rc=o.channel.recv_exit_status()
  record.update(stdout=out,stderr=err,returncode=rc);print(out)
  if err:print(err)
  if rc:raise RuntimeError('Remote operation failed: '+str(rc))
 else:
  target=a.remote if a.put else a.get;path=PurePosixPath(target)
  assert path.is_absolute() and '..' not in path.parts
  assert any(target.startswith(B+'/'+part+'/') for part in ['projects/revtrace_ces_v6_abcd_20261025','results/revtrace/ces_v6_abcd_20261025'])
  sftp=client.open_sftp();sftp.get_channel().settimeout(a.timeout)
  if a.put:
   assert a.put.stat().st_size<60_000_000
   try:sftp.stat(target)
   except FileNotFoundError:pass
   else:raise FileExistsError('Refuse overwrite')
   sftp.put(str(a.put),target);record.update(upload=target,sha256=hashlib.sha256(a.put.read_bytes()).hexdigest())
  else:
   assert not a.local.exists() and sftp.stat(target).st_size<100_000_000
   partial=a.local.with_name(a.local.name+'.partial-'+str(os.getpid()))
   assert not partial.exists();sftp.get(target,str(partial))
   assert partial.stat().st_size==sftp.stat(target).st_size
   partial.rename(a.local);record.update(download=target,sha256=hashlib.sha256(a.local.read_bytes()).hexdigest())
finally:
 if client is not None:client.close()
 (W/'operations'/(str(time.time_ns())+'.json')).write_text(json.dumps(record,indent=2)+'\n')
