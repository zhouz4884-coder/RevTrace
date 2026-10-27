"""Collect bounded environment receipts only; wheels remain on the 8 TB disk."""
from pathlib import Path
import hashlib,importlib.util,json,shlex
spec=importlib.util.spec_from_file_location('authorized_ssh',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
remote_script="""from pathlib import Path
import hashlib,json
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/freeze_boundary_20261027')
out=[]
for version in ['v1','v2','v3']:
 for p in sorted((B/('native_environment_'+version)).iterdir()):
  if p.is_file():
   assert p.stat().st_size<200000
   out.append(dict(version=version,name=p.name,path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
print(json.dumps(out))
"""
c=helper.ssh_client()
try:
 _,o,e=c.exec_command(B+'/envs/revbatch-cu128/bin/python -c '+shlex.quote(remote_script),timeout=45)
 rows=json.loads(o.read().decode());assert not e.read()
 out=Path(__file__).parent/'env_receipts';assert not out.exists();out.mkdir()
 s=c.open_sftp();s.get_channel().settimeout(45)
 for row in rows:
  dest=out/row['version']/row['name'];dest.parent.mkdir(exist_ok=True)
  s.get(row['path'],str(dest))
  assert dest.stat().st_size==row['bytes'] and hashlib.sha256(dest.read_bytes()).hexdigest()==row['sha256']
 result=json.loads((out/'v3/RESULT.json').read_text())
 smoke=json.loads((out/'v3/native-import-smoke.stdout.txt').read_text())
 receipt=dict(status='PASS_BYTE_MATCHED_ENVIRONMENT_RECEIPTS',files=rows,actual=smoke,environment_gate=result['status'],
              v2_boundary='600-second timeout retained in local ENVIRONMENT_RETRY.json; pip partial output unavailable in that attempt',
              wheels_retained_on_8TB=True,no_model_or_research_execution=True)
 (out/'COLLECTION.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(dict(files=len(rows),actual=smoke,status=result['status'],collection=str(out/'COLLECTION.json'))))
finally:c.close()
