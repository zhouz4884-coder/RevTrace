"""Publish closed32 serving trials/audits plus separately labelled N4 activity."""
from pathlib import Path
import hashlib,json,re,subprocess
E=Path(__file__).resolve().parents[1];W=Path(r'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace');T=W/'experiments'/E.name
def git(*a):return subprocess.check_output(['git','-C',str(W),*a],text=True).strip()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not git('status','--porcelain')
old=json.loads((T/'DELIVERY_MANIFEST.json').read_bytes());known={r['path']:r for r in old['files']};selected=set()
def add(p):
 p=Path(p);assert p.is_file() and p.resolve().is_relative_to(E.resolve());selected.add(p)
def tree(n):
 for p in (E/n).rglob('*'):
  if p.is_file() and '.git'not in p.relative_to(E/n).parts and '__pycache__'not in p.parts:add(p)
for idx in ['opportunity_packages_v1/PUBLICATION_INDEX_V1.json','eos_packages_v1/PUBLICATION_INDEX.json']:
 p=E/idx;add(p)
 for row in json.loads(p.read_bytes())['files']:
  q=E/row['path'];assert q.stat().st_size==row['bytes']and sha(q)==row['sha256'];add(q)
for n in ['gpu_results/PILOT24_V2','gpu_results/RESOURCE8_V1','baseline_ops/CPU_RESOURCE_DRIVER_V1','baseline_ops/CPU_RESOURCE_DRIVER_V2','baseline_ops/RESOURCE_PREPARATION_V2','baseline_ops/CPU_FOCUSED_CONFIRMATION_V1','baseline_ops/CPU_FOCUSED_CONFIRMATION_V2','baseline_ops/FOCUSED_CONFIRMATION_PREPARATION_V2']:tree(n)
for p in (E/'packages').iterdir():
 if p.is_file()and p.name.startswith(('RESOURCE_DRIVER_','FOCUSED_CONFIRMATION_','DEFAULT_AFTER_FOCUSED')):add(p)
for folder,mf in [('resource_driver_source_v2','packages/RESOURCE_DRIVER_SOURCE_v2.json'),('focused_confirmation_source_v2','packages/FOCUSED_CONFIRMATION_SOURCE_v2.json')]:
 for row in json.loads((E/mf).read_bytes())['files']:
  p=E/folder/row['path'];assert sha(p)==row['sha256'];add(p)
for n in ['COMMON_GUARDS_AND_CONTRIBUTION_INTERPRETATION_v1.zh.md','ORIGINAL_CONTINUOUS_BASELINE_OPPORTUNITY_v1.zh.md','RESOURCE_ALLOCATION_INDEPENDENT_DECISION_v1.zh.md','RESOURCE_ALLOCATION_OPPORTUNITY_DECISION_v1.zh.md','ADVICE_ACTION_DECISION_v1.zh.md','EXTERNAL_DECISION_RULE_FEASIBILITY_v1.zh.md']:add(E/'review'/n)
for tag in ['PILOT24_V2','RESOURCE8_V1','CONFIRM_NEW2_FULL_READY_V1']:
 for p in (E/'launch_ops'/tag).glob('*.json'):
  if not p.name.startswith('POLL_'):add(p)
for n in ['launch_pilot24_v2.py','close_pilot24_v2.py','launch_resource8_v1.py','close_resource8_v1.py','launch_focused_new2_v1.py']:add(E/'ops'/n)
for n in ['WORKING_STATE.json','README.md']:add(E/n)
op=E/'opportunity_ops/RESULTS_V1/GATE.json';assert json.loads(op.read_bytes())['status'].startswith('PASS')
for n,count in [('PILOT24_V2',24),('RESOURCE8_V1',8)]:assert json.loads((E/'gpu_results'/n/'SUMMARY.json').read_bytes())['completed_trials']==count
poll=max((E/'launch_ops/CONFIRM_NEW2_FULL_READY_V1').glob('POLL_*.json'),key=lambda p:p.stat().st_mtime_ns);x=json.loads(poll.read_bytes());pr=x['records'].get('PROGRESS.json',{})
live=dict(record_type='CLOSED_PILOT24_RESOURCE8_AND_SEPARATE_RUNNING_CONFIRMATION',observed_utc=x['utc'],completed_serving_trials=32,pilot24_gate='COMPLETE_FROZEN_V16_MAIN_AND_AUXILIARY_TASK_AND_ENDPOINTS',resource8_gate='COMPLETE_FROZEN_RESOURCE8_TASK_AND_ALL_SOURCE_ENDPOINTS',pilot24_report='gpu_results/PILOT24_V2/PILOT24_REPORT.zh.md',resource8_report='gpu_results/RESOURCE8_V1/RESOURCE8_REPORT.zh.md',opportunity_audit_report='opportunity_ops/OPPORTUNITY_AUDIT_REPORT_V1.zh.md',EOS_report='review/EOS_DIAGNOSTIC_v1.zh.md',current_campaign='CONFIRM_NEW2_FULL_READY_V1',current_active=x['controller']['active_owned_process'],current_completed=pr.get('completed'),current_planned=8,current_sources=['BAC009S0902W0343','BAC009S0906W0197'],scope='Two pilot speakers plus two further confirmation speakers pending complete. Closed32 includes a distinct four-speaker concurrency study; these are not32 independent speakers. No final N4/N8 comparison is claimed.')
(E/'LIVE_GPU_STATUS.json').write_text(json.dumps(live,indent=2)+'\n',encoding='utf8');add(E/'LIVE_GPU_STATUS.json')
pending=[]
for p in sorted(selected):
 rel=p.relative_to(E).as_posix();raw=p.read_bytes();assert len(raw)<8_000_000,rel
 if rel in known:assert sha(T/rel)==known[rel]['sha256'],'published prior drift '+rel
 for pat in [r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}',r'hf_[A-Za-z0-9]{25,}',r'-----BEGIN [A-Z ]*PRIVATE KEY-----']:assert not re.search(pat,raw.decode('utf8',errors='ignore')),'possible secret '+rel
 pending.append((rel,raw))
for rel,raw in pending:
 p=T/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);known[rel]=dict(path=rel,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
rows=sorted(known.values(),key=lambda r:r['path']);total=sum(r['bytes']for r in rows);assert total<64_000_000
for row in rows:assert sha(T/row['path'])==row['sha256']
manifest=dict(record_type='BOUNDED_CLOSED32_AND_RUNNING_CONFIRMATION_DELIVERY',files=rows,file_count=len(rows),bytes=total,closed_serving_trials=32,closed_pilot_trials=24,closed_resource_trials=8,completed_opportunity_CPU_controls=22,completed_EOS_CPU_controls=4,paid_reference_GPU_runs=1,reference_continuous_steps=69,reference_restored_steps=138,reference_warmup_steps=1,current_confirmation='CONFIRM_NEW2_FULL_READY_V1',current_confirmation_is_incomplete=True,manuscript_and_anonymous_artifact_unchanged=True,large_raw_stays_8TB=True,publication_commit_not_execution_commit=True)
(T/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in manifest.items()if k!='files'}))
