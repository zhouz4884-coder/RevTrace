"""Mechanical, bounded allowlist delivery; no credentials/models/audio copied."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,tarfile
W=Path(__file__).resolve().parent;G=W/'git_delivery_checkpoint_v1';D=G/'experiments/dependability_protocol_20261025'
assert not D.exists();D.mkdir(parents=True)
base=subprocess.check_output(['git','-C',str(G),'rev-parse','HEAD'],text=True).strip()
assert base=='d800523139d30486ca9158f06e750a2d80fcb9fc'
files=[]
def copy(p,relative=None):
 relative=relative or p.relative_to(W);target=D/relative
 assert target.resolve().is_relative_to(D.resolve()) and p.is_file() and p.stat().st_size<10_000_000
 data=p.read_bytes()
 if p.suffix in ['.py','.sh','.json','.md','.csv','.xml','.mjs']:
  assert not re.search(rb'ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----',data),p
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 assert target.read_bytes()==data
 files.append(dict(path=Path(relative).as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
for p in W.iterdir():
 if p.is_file() and p.suffix in ['.md','.py','.sh','.json','.csv','.xml'] and p.name not in ['remote_ops.py','build_public_checkpoint.py']:
  copy(p)
for folder in ['formal','adversarial','public_tables','historical_20261020','formal_independent_audit_v2',
 'n5_pilot_audit_v2','n5_development_audit_v1']:
 root=W/folder
 if root.exists():
  for p in root.rglob('*'):
   if p.is_file() and p.suffix in ['.md','.py','.mjs','.json','.csv','.xml']:copy(p)
for folder in ['runtime','runtime_n5','runtime_n5_v2','runtime_n5_v3','degradation']:
 root=W/folder
 for name in subprocess.check_output(['git','-C',str(root),'ls-files','-z']).decode().split('\0'):
  if name:copy(root/name)
archives=['formal_evidence_v1.tar.gz','pilot_evidence_v1.tar.gz','n5_pilot_evidence_v1.tar.gz',
 'n5_development_evidence_v2.tar.gz','n5_recovery_development_evidence_v1.tar.gz',
 'SOURCE_N1_v1.tar.gz','SOURCE_N5_v1.tar.gz','SOURCE_N5_v2.tar.gz','SOURCE_N5_v3.tar.gz',
 'RUNTIME_N5_v1.bundle','RUNTIME_N5_v2.bundle','RUNTIME_N5_v3.bundle']
for name in archives:
 p=W/name
 if name.endswith('.tar.gz'):
  with tarfile.open(p) as t:
   for member in t.getmembers():
    assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
    assert not member.name.lower().endswith(('.flac','.wav','.mp3','.safetensors','.pem','.env','.pt','.bin'))
 copy(p)
copy(W/'CHECKPOINT_README.md',Path('README.md'))
attr=D/'.gitattributes';attr.write_bytes(b'* -text\n');files.append(dict(path='.gitattributes',bytes=8,sha256=hashlib.sha256(attr.read_bytes()).hexdigest()))
assert len({r['path'] for r in files})==len(files)
total=sum(r['bytes'] for r in files);assert total<80_000_000
index=dict(base_public_commit=base,status='ADDITIVE_IN_PROGRESS_RESEARCH_CHECKPOINT_NOT_FINAL',files=sorted(files,key=lambda r:r['path']),
 bytes=total,file_count_excluding_this_manifest=len(files),scope='source/bounded archived evidence; no credentials/weights/audio; independent normal105running')
(D/'CHECKPOINT_MANIFEST.json').write_text(json.dumps(index,indent=2)+'\n')
print(json.dumps(dict(files=len(files)+1,bytes=total,manifest_sha256=hashlib.sha256((D/'CHECKPOINT_MANIFEST.json').read_bytes()).hexdigest())))
