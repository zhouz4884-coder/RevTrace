"""Authorized read-only SSH; credential retained inside approved helper."""
from pathlib import Path
import importlib.util,json,shlex,sys,hashlib
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('approved',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
client=helper.ssh_client()
try:
 command='python3 -c '+shlex.quote((P/'remote_index.py').read_text(encoding='utf8'))
 stdin,stdout,stderr=client.exec_command(command,timeout=90)
 body=stdout.read();error=stderr.read();rc=stdout.channel.recv_exit_status()
 if rc:raise RuntimeError(error.decode('utf8','replace'))
 result=json.loads(body)
 (P/'REMOTE_INDEX.json').write_bytes(body)
 print(json.dumps(dict(roots={k:dict(exists=v['exists'],files=len(v['files'])) for k,v in result['roots'].items()},
     related_project_names=result['related_project_names'],related_result_names=result['related_result_names'],
     local=str(P/'REMOTE_INDEX.json'),sha256=hashlib.sha256(body).hexdigest())))
finally:client.close()
