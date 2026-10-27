"""Bounded read-only poll of the one owned native environment installation."""
from pathlib import Path
import importlib.util
import json
import shlex
import sys
spec=importlib.util.spec_from_file_location('authorized_ssh',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
version=sys.argv[1] if len(sys.argv)>1 else 'v1'
assert version in {'v1','v2','v3'}
source="""from pathlib import Path
import json
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
root=B/'results/revtrace/freeze_boundary_20261027/native_environment_v1'
out={'receipt_files':[p.name for p in root.glob('*')], 'owned_install_processes':[]}
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  argv=p.joinpath('cmdline').read_bytes().decode().rstrip('\\0').split('\\0')
  if len(argv)>=4 and argv[0]==str(B/'envs/revtrace_native_20261027/bin/python') and argv[1:4]==['-m','pip','install']:
   out['owned_install_processes'].append({'pid':int(p.name),'argv':argv})
 except (FileNotFoundError,PermissionError,UnicodeError):pass
for name in ['COMMANDS.json','RESULT.json','OWNED_PROCESS.json','FAILURE.json']:
 p=root/name
 if p.exists():out[name]=json.loads(p.read_text())
for name in ['install-pinned.stdout.txt','install-pinned.stderr.txt','download-wheels.stdout.txt','download-wheels.stderr.txt','offline-install.stdout.txt','offline-install.stderr.txt']:
 p=root/name
 if p.exists():out[name+'_tail']=p.read_text()[-7000:]
print(json.dumps(out,indent=2))
""".replace('native_environment_v1','native_environment_'+version)
client=helper.ssh_client()
try:
 _,out,err=client.exec_command(B+'/envs/revbatch-cu128/bin/python -c '+shlex.quote(source),timeout=45)
 print(out.read().decode()); e=err.read().decode()
 if e:print(e)
finally:client.close()
