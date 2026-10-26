"""Final PUBLIC evidence only. Manuscript/containingZIP stay local/private."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,tarfile
W=Path(__file__).resolve().parent;G=W/'git_delivery_checkpoint_v1';D=G/'experiments/dependability_protocol_20261025'
git=lambda *args:subprocess.check_output(['git','-C',str(G),*args])
base=git('rev-parse','HEAD').decode().strip();assert base=='3820b81f384fe16b10c3daa2415d612a9ab40a8d'
exclude={'remote_ops.py','ACTIVE_STATE.json','CURRENT_HANDOFF.md','CURRENT_HANDOFF_v2.md','build_anonymous_snapshot_v1.py',
 'check_private_review_repo.py','prepare_private_review_delivery_v1.py','resume_private_review_delivery_v2.py',
 'qa_candidate_v1.py','build_candidate_tables.py','build_candidate_reference_assets.py','format_candidate_spacing.py','finalize_candidate_qa.py'}
paths=[p for p in W.iterdir() if p.is_file() and p.suffix in ['.md','.py','.sh','.json','.xml','.csv'] and p.name not in exclude
 and not p.name.upper().startswith('PRIVATE_')]
for directory in ['formal','synthesis_data_v2','final_matrices_v3','role_formal_synthesis_v4','role_formal_primary_v2','figures']:
 paths.extend(p for p in (W/directory).rglob('*') if p.is_file() and p.suffix in ['.md','.py','.mjs','.json','.csv','.png','.pdf','.svg','.txt'])
paths.extend(W/'role_formal_collected_v2'/n for n in ['FORMAL_LAUNCH.json','FORMAL_RELEASE.json','FORMAL_RAW_INDEX_v1.json','formal/FREEZE.json','formal/SUMMARY.json'])
paths.append(W/'role_formal_evidence_v2.tar.gz')
for p in paths:
 assert 'candidate_20261026' not in p.relative_to(W).parts and p.name!='review_snapshot_v1.zip'
 if p.name.endswith('.tar.gz'):
  with tarfile.open(p) as t:
   for m in t:
    assert not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
    assert not m.name.lower().endswith(('.wav','.flac','.safetensors','.pem','.pt','.bin'))
files=[];staged=[];older_unchanged=[]
for p in sorted(set(paths)):
 rel=p.relative_to(W);q=D/rel;data=p.read_bytes();assert len(data)<10_000_000
 if q.exists():
  if q.read_bytes()!=data:older_unchanged.append(rel.as_posix())
  continue
 if p.suffix in ['.md','.py','.sh','.json','.xml','.csv']:assert not re.search(rb'ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----',data),p
 q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);staged.append(q.relative_to(G).as_posix())
 files.append(dict(path=rel.as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
status=D/'STATUS_CHECKPOINT_v6.json';assert not status.exists();status.write_bytes((W/'ACTIVE_STATE.json').read_bytes());staged.append(status.relative_to(G).as_posix())
files.append(dict(path=status.relative_to(D).as_posix(),bytes=status.stat().st_size,sha256=hashlib.sha256(status.read_bytes()).hexdigest()))
index=D/'CHECKPOINT_DELTA_v6.json';assert not index.exists();index.write_text(json.dumps(dict(base_commit=base,files=files,
 scope='FINAL_BOUNDED_PUBLIC_RESEARCH_EVIDENCE_ALL_GATES; unpublishedmanuscript/source/containingZIP intentionally local/private',
 frozen_old_bytes_preserved=older_unchanged,full_unpublished_manuscript_public=False,all_research_stages_resolved=True,automatic_submission=False),indent=2)+'\n');staged.append(index.relative_to(G).as_posix())
subprocess.run(['git','-C',str(G),'add','--',*staged],check=True)
changes=[x for x in git('diff','--cached','--name-status','-z').split(b'\0') if x]
for i in range(0,len(changes),2):assert changes[i]==b'A' and changes[i+1].startswith(b'experiments/dependability_protocol_20261025/')
subprocess.run(['git','-C',str(G),'-c','core.whitespace=cr-at-eol,-blank-at-eof','diff','--cached','--check'],check=True)
subprocess.run(['git','-C',str(G),'commit','-m','Close dependability research with all64 role faults, full strong controls and retained performanceNO-GO; manuscript kept private'],check=True,capture_output=True)
commit=git('rev-parse','HEAD').decode().strip()
out=dict(base=base,commit=commit,added_files=len(changes)//2,all_additive=True,unpublished_manuscript_public=False,
 bytes=sum(x['bytes'] for x in files),private_review_delivery_separate=True)
(W/'GITHUB_CHECKPOINT_DELTA_PREPUSH_v6.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
