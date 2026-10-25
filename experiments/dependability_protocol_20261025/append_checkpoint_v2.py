from pathlib import Path
import hashlib,json,shutil,subprocess
W=Path(__file__).resolve().parent;G=W/'git_delivery_checkpoint_v1';D=G/'experiments/dependability_protocol_20261025'
git=lambda *args:subprocess.check_output(['git','-C',str(G),*args])
base=git('rev-parse','HEAD').decode().strip();assert base=='1b42262950a7ac5a9ee5bfe7f06d6c59171d0148'
selected=[W/name for name in ['UNIFIED_FAULT_MATRIX_v1.md','EVIDENCE_UPDATE_20261026.md','audit_n5_recovery_assets.py',
 'status_n5_compact.sh','GITHUB_CHECKPOINT_PUBLIC_VERIFICATION_v1.json']]
selected += [p for p in (W/'figures').iterdir() if p.is_file() and p.suffix in ['.md','.py','.json','.csv','.txt','.pdf','.svg','.png']]
files=[]
for p in selected:
 rel=p.relative_to(W);target=D/rel;target.parent.mkdir(exist_ok=True,parents=True)
 if target.exists():assert target.read_bytes()==p.read_bytes(),'prepared delivery changed'
 else:shutil.copyfile(p,target)
 data=target.read_bytes();assert data==p.read_bytes()
 files.append(dict(path=rel.as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
record=dict(base_commit=base,status='APPEND_ONLY_NO_MEASURED_RESULT_OR_ORIGINAL_MANUSCRIPT_CHANGED',files=files,
 original_prefix_manifest_sha256=hashlib.sha256((D/'CHECKPOINT_MANIFEST.json').read_bytes()).hexdigest(),goal_complete=False)
index=D/'CHECKPOINT_DELTA_v2.json';index.write_text(json.dumps(record,indent=2)+'\n')
subprocess.run(['git','-C',str(G),'add','--',*[str((D/p.relative_to(W)).relative_to(G)) for p in selected],str(index.relative_to(G))],check=True)
changes=git('diff','--cached','--name-status','-z').split(b'\0');changes=[x for x in changes if x]
for i in range(0,len(changes),2):assert changes[i]==b'A' and changes[i+1].startswith(b'experiments/dependability_protocol_20261025/')
subprocess.run(['git','-C',str(G),'-c','core.whitespace=cr-at-eol','diff','--cached','--check','--','.',
 ':(exclude)experiments/dependability_protocol_20261025/figures/cost_boundary_v1.svg'],check=True)
r=subprocess.run(['git','-C',str(G),'commit','-m','Append source-scoped cost figure and provisional unified fault matrix'],check=True,capture_output=True,text=True)
commit=git('rev-parse','HEAD').decode().strip();assert git('rev-parse','HEAD^').decode().strip()==base
(W/'GITHUB_CHECKPOINT_DELTA_PREPUSH_v2.json').write_text(json.dumps(dict(base=base,commit=commit,added_files=len(changes)//2,all_additive=True),indent=2)+'\n')
print(json.dumps(dict(commit=commit,added_files=len(changes)//2)))
