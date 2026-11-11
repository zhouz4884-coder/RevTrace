"""Prepare incremental bounded evidence before the first serving cell."""
from pathlib import Path
import hashlib,json,re,subprocess
E=Path(__file__).resolve().parents[1]
W=Path(r'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace');T=W/'experiments'/E.name
def git(*a):return subprocess.check_output(['git','-C',str(W),*a],text=True).strip()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not git('status','--porcelain')
prior=json.loads((T/'DELIVERY_MANIFEST.json').read_bytes());known={r['path']:r for r in prior['files']}
selected=set()
def add(p):
 p=Path(p);assert p.is_file() and p.resolve().is_relative_to(E.resolve());selected.add(p)
def tree(name):
 for p in (E/name).rglob('*'):
  if p.is_file() and '.git' not in p.relative_to(E/name).parts and '__pycache__' not in p.parts:add(p)
for n in ['README.md','WORKING_STATE.json','NEW_EVIDENCE_AND_EXECUTION_DELTA.zh.md']:add(E/n)
tree('plans')
for p in (E/'packages').iterdir():
 if p.is_file():add(p)
for name in ['baseline_ops/CPU_BASELINE_V3','baseline_ops/CPU_PILOT_DRIVER_V2','baseline_ops/CPU_ENTRY_ROUTE_V1','baseline_ops/PILOT_PREPARATION_V2','baseline_ops/PILOT_BOUND_REFERENCE_V2','gpu_results/REFERENCE_FULL4_V2','header_packages_v1','MAGICDATA_HEADER_CONTROLS_v1']:tree(name)
for name in ['PILOT_PRELAUNCH_DESIGN_REVIEW_v1.zh.md','SERVICE_ENTRYPOINT_AUDIT_v1.zh.md','C1_ACTION_INVARIANT_MEMO_v1.zh.md','PILOT_REVIEW_AND_BUDGET_INDEX_v1.json']:add(E/'review'/name)
for name in ['LEDGER_FULL_BUDGET_DERIVED_v1.json','LEDGER_FULL_BUDGET_DERIVED_v1.zh.md','derive_full_budget.py']:add(E/'history_ops'/name)
add(E/'header_ops/HEADER_READINESS_CONTROLS_v1.zh.md')
for folder,manifest in [('baseline_source_v3','packages/BASELINE_SOURCE_v3.json'),('pilot_driver_source_v2','packages/PILOT_DRIVER_SOURCE_v2.json'),('magicdata_header_source','header_packages_v1/SOURCE.json')]:
 m=json.loads((E/manifest).read_bytes())
 for row in m['files']:
  p=E/folder/row['path'];assert sha(p)==row['sha256'];add(p)
for p in (E/'launch_ops/REFERENCE_FULL4_V2').iterdir():
 if p.is_file() and p.suffix=='.json' and not p.name.startswith('POLL_'):add(p)
for n in ['launch_reference_v2.py','collect_reference_prepare_service_v2.py']:add(E/'ops'/n)
pending=[]
for p in sorted(selected):
 rel=p.relative_to(E).as_posix();raw=p.read_bytes();assert len(raw)<5_000_000,rel
 for pattern in [r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}',r'hf_[A-Za-z0-9]{25,}',r'-----BEGIN [A-Z ]*PRIVATE KEY-----']:
  assert not re.search(pattern,raw.decode('utf8',errors='ignore')),'possible secret: '+rel
 if rel in known:assert sha(T/rel)==known[rel]['sha256'],'published prior bytes drift '+rel
 pending.append((rel,raw))
for rel,raw in pending:
 p=T/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 known[rel]=dict(path=rel,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
rows=sorted(known.values(),key=lambda r:r['path']);total=sum(r['bytes']for r in rows);assert total<32_000_000
for r in rows:assert (T/r['path']).stat().st_size==r['bytes'] and sha(T/r['path'])==r['sha256'],r['path']
m=dict(record_type='BOUNDED_CPU_AND_PAID_REFERENCE_DELIVERY_NOT_SERVING_RESULTS',prior_CPU_delivery_commit='e5bf242f022efac59fd5bb9d4785af8f39b5ebf0',files=rows,file_count=len(rows),bytes=total,new_serving_GPU_trials=0,paid_reference_GPU_runs=1,continuous_original_steps=69,restored_steps=138,warmup_steps=1,native_evaluated_full_step_records=196,reference_cost_separate=True,manuscript_and_anonymous_artifact_unchanged=True,large_raw_result_scope='8TB only; no models/datasets/cache/raw Consumer/character identity traces copied',execution_commits='Every actual source has its own full manifest/bundle; GitHub delivery commit is an archive, not any execution commit')
(T/'DELIVERY_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in m.items()if k!='files'}))
