"""Only approved CPU reconstruction; remote writes restricted to new audit dir."""
from pathlib import Path
import importlib.util,json,shlex,hashlib,subprocess
P=Path(__file__).resolve().parent
commit=subprocess.check_output(['git','-C',str(P),'rev-parse','HEAD'],text=True).strip()
code=(P/'remote_reconstruct.py').read_bytes();digest=hashlib.sha256(code).hexdigest()
spec=importlib.util.spec_from_file_location('approved',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
client=helper.ssh_client()
try:
 python='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/streamtxn-cu128/bin/python'
 cmd='PYTHONDONTWRITEBYTECODE=1 R7_AUDIT_CODE_COMMIT='+commit+' R7_AUDIT_SCRIPT_SHA256='+digest+' '+shlex.quote(python)+' -B -c '+shlex.quote(code.decode())
 i,o,e=client.exec_command(cmd,timeout=180)
 raw=o.read();err=e.read();rc=o.channel.recv_exit_status()
 (P/'RECONSTRUCTION_STDOUT.json').write_bytes(raw);(P/'RECONSTRUCTION_STDERR.log').write_bytes(err)
 print(raw.decode());print(json.dumps(dict(returncode=rc,code_commit=commit,script_sha256=digest)))
 if rc:raise RuntimeError(err.decode())
 with client.open_sftp() as sftp:
  for name in ('INPUT_IDENTITY.json','SUMMARY.json','GATE.json'):
   sftp.get('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/freeze_boundary_20261027/r7_input_reconstruction_v1/'+name,str(P/name))
finally:client.close()
