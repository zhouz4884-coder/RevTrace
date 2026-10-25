from pathlib import Path
import hashlib,json,shutil,subprocess
W=Path(__file__).resolve().parent;G=W/'git_delivery_checkpoint_v1';D=G/'experiments/dependability_protocol_20261025'
git=lambda *args:subprocess.check_output(['git','-C',str(G),*args])
base=git('rev-parse','HEAD').decode().strip();assert base=='a96e82059df700daba7b275ab4aa735ff4f684df'
names=['N5_NORMAL_PRIMARY_v1.json','N5_NORMAL_AGGREGATION_v1.json','N5_NORMAL_BUDGETS_v1.json',
 'N5_NORMAL_DECISION_v1.json','N5_NORMAL_REPORT.zh.md','N5_RECOVERY_DEVELOPMENT_INDEPENDENT_GATE_v1.json',
 'n5_postnormal_cpu_bounded_v1.tar.gz','unpack_and_gate_n5_normal.py','collect_n5_postnormal_cpu.sh','launch_n5_formal_fault.sh',
 'run_n5_normal_summaries.sh','status_n5_cpu.sh','status_n5_fault_compact.sh','audit_n5_fault_formal_v1.py','audit_n5_fault_assets_v1.py',
 'test_n5_fault_audit.py','CPU_N5_FAULT_AUDIT_v1.xml','run_n5_postfault_cpu.py','launch_n5_postfault_cpu.sh',
 'run_role_probe_controller_v1.py','prepare_role_remote.sh','unpack_role_linux_cpu.sh','GITHUB_CHECKPOINT_PUBLIC_VERIFICATION_v3.json']
paths=[W/n for n in names]
for directory in ['n5_postnormal_collected_v1','literature/crossref_v2']:
 paths.extend(p for p in (W/directory).rglob('*') if p.is_file())
paths.extend(W/'literature'/n for n in ['fetch_substrate_metadata_v2.py','SUBSTRATE_DIFF_v2.md'])
files=[];staged=[]
for p in paths:
 rel=p.relative_to(W);target=D/rel;data=p.read_bytes();assert len(data)<10_000_000
 if target.exists():assert target.read_bytes()==data;continue
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 files.append(dict(path=rel.as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()));staged.append(str(target.relative_to(G)))
snap=D/'STATUS_CHECKPOINT_v4.json';assert not snap.exists();snap.write_bytes((W/'ACTIVE_STATE.json').read_bytes())
files.append(dict(path=snap.relative_to(D).as_posix(),bytes=snap.stat().st_size,sha256=hashlib.sha256(snap.read_bytes()).hexdigest()));staged.append(str(snap.relative_to(G)))
index=D/'CHECKPOINT_DELTA_v4.json';assert not index.exists();index.write_text(json.dumps(dict(base_commit=base,files=files,
 scope='105independent normal completed/all audits pass; CDE performanceNO-GO; formal recovery21live; no adversarialGPU yet',
 raw_GPU_data_8TB_bytes=711621405,original_manuscript_unchanged=True,goal_complete=False),indent=2)+'\n');staged.append(str(index.relative_to(G)))
subprocess.run(['git','-C',str(G),'add','--',*staged],check=True)
changes=[r for r in git('diff','--cached','--name-status','-z').split(b'\0') if r]
for i in range(0,len(changes),2):assert changes[i]==b'A' and changes[i+1].startswith(b'experiments/dependability_protocol_20261025/')
subprocess.run(['git','-C',str(G),'-c','core.whitespace=cr-at-eol','diff','--cached','--check'],check=True)
subprocess.run(['git','-C',str(G),'commit','-m','Archive all105 independent normal audits and explicit CDE performanceNO-GO; formal recovery remains active'],check=True,capture_output=True)
commit=git('rev-parse','HEAD').decode().strip();assert git('rev-parse','HEAD^').decode().strip()==base
(W/'GITHUB_CHECKPOINT_DELTA_PREPUSH_v4.json').write_text(json.dumps(dict(base=base,commit=commit,added_files=len(changes)//2,all_additive=True),indent=2)+'\n')
print(json.dumps(dict(commit=commit,added_files=len(changes)//2,total_bytes=sum(r['bytes'] for r in files))))
