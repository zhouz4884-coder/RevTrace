"""Resume failed style-check only. Generated SVG bytes remain unchanged."""
from pathlib import Path
import hashlib,json,shutil,subprocess
W=Path(__file__).resolve().parent;G=W/'git_delivery_checkpoint_v1';D=G/'experiments/dependability_protocol_20261025'
git=lambda *args:subprocess.check_output(['git','-C',str(G),*args])
base=git('rev-parse','HEAD').decode().strip();assert base=='3820b81f384fe16b10c3daa2415d612a9ab40a8d'
index=D/'CHECKPOINT_DELTA_v6.json';m=json.loads(index.read_text());assert m['base_commit']==base
for r in m['files']:
 p=D/r['path'];assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
for p in [Path(__file__),W/'PUBLIC_ARCHIVAL_STYLE_NOTE_v6.md']:
 q=D/p.name;assert not q.exists();shutil.copyfile(p,q);m['files'].append(dict(path=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
index.write_text(json.dumps(m,indent=2)+'\n')
subprocess.run(['git','-C',str(G),'add','--',str(index.relative_to(G)),str((D/Path(__file__).name).relative_to(G)),str((D/'PUBLIC_ARCHIVAL_STYLE_NOTE_v6.md').relative_to(G))],check=True)
changes=[x for x in git('diff','--cached','--name-status','-z').split(b'\0') if x]
for i in range(0,len(changes),2):
 assert changes[i]==b'A' and changes[i+1].startswith(b'experiments/dependability_protocol_20261025/')
 assert b'candidate_20261026/' not in changes[i+1] and b'review_snapshot_v1.zip' not in changes[i+1]
subprocess.run(['git','-C',str(G),'-c','core.whitespace=cr-at-eol,-blank-at-eof','diff','--cached','--check','--','.',':(exclude)**/*.svg'],check=True)
subprocess.run(['git','-C',str(G),'commit','-m','Close bounded dependability research:64 formal role faults, all safe controls and negative decisions; draft kept private'],check=True,capture_output=True)
commit=git('rev-parse','HEAD').decode().strip()
def tree(ref):return {x.split(b'\t',1)[1]:x.split(b'\t',1)[0] for x in git('ls-tree','-r','-z',ref).split(b'\0') if x}
before=tree(base);after=tree(commit);assert all(after.get(k)==v for k,v in before.items())
for r in m['files']:
 key=('experiments/dependability_protocol_20261025/'+r['path']).encode();data=(D/r['path']).read_bytes()
 assert after[key].split()[2]==hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest().encode()
out=dict(base=base,commit=commit,added_files=len(changes)//2,all_additive=True,previous_entries_preserved=len(before),
 all_new_blob_bytes_verified=True,unpublished_manuscript_public=False,private_review_delivery_separate=True)
(W/'GITHUB_CHECKPOINT_DELTA_PREPUSH_v6.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
