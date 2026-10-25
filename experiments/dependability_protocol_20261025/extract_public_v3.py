"""Persistent Git object reader; isolated output, full blob/SHA validation."""
from pathlib import Path
import hashlib,json,subprocess
W=Path(__file__).resolve().parent;repo=W.parent/'online_admission_20261022/git_delivery_stage_v1';idx=json.loads((W/'PUBLIC_TREE_INDEX.json').read_text());out=W/'source_archive_v3';assert not out.exists();out.mkdir()
child=subprocess.Popen(['git','-C',str(repo),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE);copied=[]
try:
 for r in idx['files']:
  name=r['path'];p=Path(name);base=p.name.lower()
  reports=p.suffix.lower()=='.md'
  runtime=('/runtime/' in name or '/source/' in name) and p.suffix.lower() in {'.py','.toml','.ini','.json','.txt','.md'}
  summary=p.suffix.lower() in {'.json','.csv'} and any(x in base for x in ['summary','audit','evidence','manifest','freeze','groups','claim','decision','state']) and r['bytes']<2_000_000
  if not (reports or runtime or summary) or r['bytes']>2_000_000:continue
  child.stdin.write((r['git_blob']+'\n').encode());child.stdin.flush();head=child.stdout.readline().decode().split();assert head==[r['git_blob'],'blob',str(r['bytes'])]
  data=child.stdout.read(r['bytes']);assert child.stdout.read(1)==b'\n' and len(data)==r['bytes']
  assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==r['git_blob']
  target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
  copied.append({**r,'sha256':hashlib.sha256(data).hexdigest()})
finally:
 child.stdin.close();child.wait(timeout=10)
assert child.returncode==0
manifest=W/'PUBLIC_EXTRACT_V3_MANIFEST.json';assert not manifest.exists();manifest.write_text(json.dumps({'commit':idx['commit'],'files':copied,'not_a_new_experiment':True},indent=2)+'\n')
print(json.dumps({'files':len(copied),'bytes':sum(r['bytes'] for r in copied),'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest()}))
