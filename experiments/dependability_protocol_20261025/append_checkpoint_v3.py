"""Append only verified CPU/source/figure progress, no partial formal winners."""
from pathlib import Path
import hashlib,json,shutil,subprocess
W=Path(__file__).resolve().parent;G=W/'git_delivery_checkpoint_v1';D=G/'experiments/dependability_protocol_20261025'
git=lambda *args:subprocess.check_output(['git','-C',str(G),*args])
base=git('rev-parse','HEAD').decode().strip();assert base=='bdde18b85189f4aea93be93c657d4c7a79616725'
names=['audit_n5_formal_v1.py','aggregate_n5_normal_v1.py','audit_n5_budgets_v1.py','run_n5_postnormal_cpu.py','launch_n5_postnormal_cpu.sh',
 'test_n5_audit_metrics.py','test_n5_aggregation.py','N5_METRIC_SCOPE_v1.md','CPU_N5_AUDIT_METRICS_v1.xml','CPU_N5_AUDIT_METRICS_v2.xml',
 'CPU_N5_AGGREGATION_v1.xml','CPU_ROLE_CHANNEL_v1.xml','CPU_ROLE_CHANNEL_v2.xml','CPU_FEEDBACK_OPERATOR_v1.xml',
 'CPU_ROLE_AND_OPERATOR_v1.xml','CPU_ROLE_AND_OPERATOR_v2.xml','CPU_ROLE_AND_OPERATOR_v3.xml','CPU_ROLE_AND_OPERATOR_FROZEN_v4.xml',
 'CPU_ROLE_AND_OPERATOR_FROZEN_v5.xml','ROLE_PROBE_CPU_GATE_v1.json','ROLE_PROBE_SOURCE_MANIFEST_v1.json','ROLE_PROBE_SOURCE_v1.tar.gz',
 'GITHUB_CHECKPOINT_PUBLIC_VERIFICATION_v2.json']
paths=[W/n for n in names]
for directory in ['adversarial','n5_development_expanded_audit_v2','n5_development_budget_audit_v1']:
 for p in (W/directory).rglob('*'):
  if p.is_file() and p.suffix in ['.py','.md','.json','.csv']:paths.append(p)
for p in (W/'figures').iterdir():
 if p.is_file() and (p.name.startswith(('causal_','CAUSAL_','plot_causal_','qa_causal_'))):paths.append(p)
for row in json.loads((W/'ROLE_PROBE_SOURCE_MANIFEST_v1.json').read_text())['files']:
 paths.append(W/'adversarial_frozen_v1'/row['path'])
files=[];staged=[]
for p in paths:
 relative=p.relative_to(W);target=D/relative;data=p.read_bytes();assert len(data)<10_000_000
 if target.exists():
  assert target.read_bytes()==data,'published source changed; use a versioned path: '+str(relative)
  continue
 target.parent.mkdir(exist_ok=True,parents=True);shutil.copyfile(p,target)
 files.append(dict(path=relative.as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()));staged.append(str(target.relative_to(G)))
snapshot=D/'STATUS_CHECKPOINT_v3.json';assert not snapshot.exists();snapshot.write_bytes((W/'ACTIVE_STATE.json').read_bytes())
files.append(dict(path=snapshot.relative_to(D).as_posix(),bytes=snapshot.stat().st_size,sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest()));staged.append(str(snapshot.relative_to(G)))
record=dict(base_commit=base,files=files,scope='CPU/source/causal-figure progress; normal105stillrunning, no GPU adversarial claims',
 manuscript_unchanged=True,goal_complete=False)
index=D/'CHECKPOINT_DELTA_v3.json';assert not index.exists();index.write_text(json.dumps(record,indent=2)+'\n');staged.append(str(index.relative_to(G)))
subprocess.run(['git','-C',str(G),'add','--',*staged],check=True)
changes=[x for x in git('diff','--cached','--name-status','-z').split(b'\0') if x]
for i in range(0,len(changes),2):assert changes[i]==b'A' and changes[i+1].startswith(b'experiments/dependability_protocol_20261025/')
subprocess.run(['git','-C',str(G),'-c','core.whitespace=cr-at-eol','diff','--cached','--check','--','.',
 ':(exclude)experiments/dependability_protocol_20261025/figures/causal_protocol_v1.svg',
 ':(exclude)experiments/dependability_protocol_20261025/CPU_ROLE_AND_OPERATOR_v3.xml',
 ':(exclude)experiments/dependability_protocol_20261025/CPU_ROLE_AND_OPERATOR_FROZEN_v4.xml'],check=True)
subprocess.run(['git','-C',str(G),'commit','-m','Append mapped causal protocol, full-denominator audits and CPU-gated role-channel probe source'],check=True,capture_output=True)
commit=git('rev-parse','HEAD').decode().strip();assert git('rev-parse','HEAD^').decode().strip()==base
(W/'GITHUB_CHECKPOINT_DELTA_PREPUSH_v3.json').write_text(json.dumps(dict(base=base,commit=commit,added_files=len(changes)//2,all_additive=True),indent=2)+'\n')
print(json.dumps(dict(commit=commit,added_files=len(changes)//2,total_bytes=sum(r['bytes'] for r in files))))
