"""Append only audited fault21/pilot evidence; prior published bytes stay immutable."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,tarfile
W=Path(__file__).resolve().parent;G=W/'git_delivery_checkpoint_v1';D=G/'experiments/dependability_protocol_20261025'
git=lambda *args:subprocess.check_output(['git','-C',str(G),*args])
base=git('rev-parse','HEAD').decode().strip();assert base=='4e869ba846360161ae2b75a9dacf8e2681ef3512'
paths=[p for p in W.iterdir() if p.is_file() and p.suffix in ['.md','.py','.sh','.json','.xml','.csv'] and p.name not in ['remote_ops.py','ACTIVE_STATE.json','CURRENT_HANDOFF.md']]
for folder in ['n5_postfault_collected_v1','role_pilot_primary_v2','role_pilot_expanded_audit_v2']:
 paths.extend(p for p in (W/folder).rglob('*') if p.is_file() and p.suffix in ['.json','.md','.xml','.csv'])
for folder in ['adversarial_frozen_v1','adversarial_frozen_v2']:
 paths.extend(W/folder/f for f in git_source(W/folder)) if False else None
 paths.extend(W/folder/f for f in subprocess.check_output(['git','-C',str(W/folder),'ls-files','-z']).decode().split('\0') if f)
for name in ['n5_postfault_cpu_bounded_v1.tar.gz','ROLE_PROBE_SOURCE_v1.tar.gz','ROLE_PROBE_SOURCE_v2.tar.gz','role_pilot_evidence_v1.tar.gz','role_pilot_evidence_v2.tar.gz']:
 p=W/name
 with tarfile.open(p) as t:
  for m in t:
   assert not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
   assert not m.name.lower().endswith(('.flac','.wav','.mp3','.safetensors','.pem','.env','.pt','.bin'))
 paths.append(p)
files=[];staged=[];not_replaced=[]
for p in sorted(set(paths)):
 rel=p.relative_to(W);target=D/rel;data=p.read_bytes();assert len(data)<10_000_000
 if target.exists():
  if target.read_bytes()!=data:not_replaced.append(rel.as_posix())
  continue
 if p.suffix in ['.md','.py','.sh','.json','.xml','.csv']:
  assert not re.search(rb'ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----',data),p
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 files.append(dict(path=rel.as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()));staged.append(str(target.relative_to(G)))
snap=D/'STATUS_CHECKPOINT_v5.json';assert not snap.exists();snap.write_bytes((W/'ACTIVE_STATE.json').read_bytes())
files.append(dict(path=snap.relative_to(D).as_posix(),bytes=snap.stat().st_size,sha256=hashlib.sha256(snap.read_bytes()).hexdigest()));staged.append(str(snap.relative_to(G)))
index=D/'CHECKPOINT_DELTA_v5.json';assert not index.exists();index.write_text(json.dumps(dict(base_commit=base,files=files,
 scope='105normal+21recovery allaudited; two8case role pilots allgates; formal64 live; no new manuscript yet; all prior performanceNO-GOs retained',
 older_published_bytes_unchanged=not_replaced,original_manuscript_unchanged=True,goal_complete=False),indent=2)+'\n');staged.append(str(index.relative_to(G)))
subprocess.run(['git','-C',str(G),'add','--',*staged],check=True)
changes=[r for r in git('diff','--cached','--name-status','-z').split(b'\0') if r]
for i in range(0,len(changes),2):assert changes[i]==b'A' and changes[i+1].startswith(b'experiments/dependability_protocol_20261025/')
subprocess.run(['git','-C',str(G),'-c','core.whitespace=cr-at-eol','diff','--cached','--check'],check=True)
subprocess.run(['git','-C',str(G),'commit','-m','Archive21 independent recovery audits and role-limited GPU pilot replication; formal study active'],check=True,capture_output=True)
commit=git('rev-parse','HEAD').decode().strip();assert git('rev-parse','HEAD^').decode().strip()==base
(W/'GITHUB_CHECKPOINT_DELTA_PREPUSH_v5.json').write_text(json.dumps(dict(base=base,commit=commit,added_files=len(changes)//2,all_additive=True),indent=2)+'\n')
print(json.dumps(dict(commit=commit,added_files=len(changes)//2,total_bytes=sum(r['bytes'] for r in files))))
