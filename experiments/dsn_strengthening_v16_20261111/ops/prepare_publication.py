"""Copy an explicit bounded research snapshot into the clean publication tree."""
from pathlib import Path
import hashlib,json,re,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1]
W=Path(r'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace')
T=W/'experiments'/E.name
def git(root,*a):return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
need=lambda ok,why: None if ok else (_ for _ in ()).throw(RuntimeError(why))
need(git(R,'rev-parse','HEAD')=='7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f','legacy HEAD changed')
need(not git(W,'status','--porcelain'),'publication tree must start clean')
paths=set()
def add(p):
    p=Path(p);need(p.is_file() and p.resolve().is_relative_to(E.resolve()),'bad publication path '+str(p));paths.add(p)
def tree(p):
    for x in (E/p).rglob('*'):
        if x.is_file() and '.git' not in x.relative_to(E/p).parts and '__pycache__' not in x.parts:add(x)
for n in ['.gitattributes','README.md','MISSED_STRONG_EVIDENCE.zh.md','PRE_EXPERIMENT_EVIDENCE_REPORT_MANIFEST.json','GPU_PLAN_FOR_REVIEW.zh.md','WORKING_STATE.json','NEW_EVIDENCE_AND_EXECUTION_DELTA.zh.md']:add(E/n)
for p in ['plans','formal_packages_v1','FORMAL_ACTION_RESULTS_v1','baseline_ops/CPU_BASELINE_V1','baseline_ops/CPU_BASELINE_V2','baseline_ops/CPU_ACCOUNTING_V1','readiness_ops','readiness_ops_v2']:tree(p)
for p in (E/'packages').iterdir():
    if p.is_file() and p.name.startswith(('BASELINE_','ACCOUNTING_','IMMUTABLE_','UNCHANGED_')):add(p)
# Complete runtime source files are selected from the external full manifest,
# never by recursively copying a working repository or its .git directory.
for row in json.loads((E/'packages/BASELINE_SOURCE_v2.json').read_bytes())['files']:add(E/'baseline_source_v2'/row['path'])
for n in ['BASELINE_DESIGN.zh.md','UIR_DESIGN.zh.md','FORMAL_RECOVERY_OPPORTUNITIES.zh.md','FORMAL_RECOVERY_OPPORTUNITIES.json','FORMAL_RECOVERY_CPU_RESULTS_v1.zh.md','FORMAL_RECOVERY_PHASE_ENERGY_v1.json','FORMAL_RECOVERY_RAW_PHASES_v1.json','FORMAL_RECOVERY_WHISPER_LOADER_v1.json','LOADER_CONTROL_HISTORICAL_INPUT_REFERENCE_v2.json','LOADER_CONTROL_REVISION_v2.zh.md','LOADER_CONTROL_REVISION_v2.json','FORMAL_RECOVERY_BASELINE_v2_READ_REVIEW.zh.md','LEDGER_v2_INDEPENDENT_REVIEW.zh.md','HISTORICAL_EVIDENCE.zh.md','HISTORICAL_EVIDENCE.json','METADATA_SOURCE_CHOICE_v1.zh.md','METADATA_SOURCE_CHOICE_v1.json','MAGICDATA_TEST_METADATA_VERIFIED_v2.json']:add(E/'review'/n)
for p in ['history_ops/results/PRIMARY_v1','history_ops/results/INDEPENDENT_v1','history_ops/results/LEDGER_v2','history_ops/results/EXPOSURE_v2','history_ops/results/EXPOSURE_INDEPENDENT_v2']:tree(p)
# Only bounded records/source bundles from history_ops, excluding checkout Git,
# unvalidated prototypes, raw traces and large character-level proof artifacts.
for p in (E/'history_ops').iterdir():
    if p.is_file() and p.suffix in {'.json','.md','.bundle'} and not p.name.startswith('POLL_'):add(p)
index=E/'history_ops/publication/PUBLICATION_FILE_INDEX.json'
for row in json.loads(index.read_bytes())['files']:
    p=E/row['path'];need(p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'history publication input drift '+row['path']);add(p)
add(index)
need((E/'history_ops/results/EXPOSURE_v2/GATE.json').exists(),'exposure not closed')
need((E/'history_ops/results/EXPOSURE_INDEPENDENT_v2/GATE.json').exists(),'independent exposure not closed')
for d in ['baseline_ops/CPU_BASELINE_V2','baseline_ops/CPU_ACCOUNTING_V1','history_ops/results/PRIMARY_v1','history_ops/results/INDEPENDENT_v1','history_ops/results/LEDGER_v2','history_ops/results/EXPOSURE_v2','history_ops/results/EXPOSURE_INDEPENDENT_v2','readiness_ops_v2/results']:
    need(json.loads((E/d/'GATE.json').read_bytes())['status'].startswith('PASS'),'completion gate '+d)
rows=[]
for p in sorted(paths):
    raw=p.read_bytes();need(len(raw)<5_000_000,'individual artifact is not bounded '+str(p))
    txt=raw.decode('utf8',errors='ignore')
    for pattern in [r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}',r'hf_[A-Za-z0-9]{25,}',r'-----BEGIN [A-Z ]*PRIVATE KEY-----']:
        need(re.search(pattern,txt) is None,'possible secret; stop without echoing value: '+str(p))
    q=T/p.relative_to(E);need(not q.exists(),'never replace a publication artifact '+str(q))
    rows.append(dict(path=p.relative_to(E).as_posix(),bytes=len(raw),sha256=sha(p)))
need(sum(r['bytes']for r in rows)<20_000_000,'snapshot too large')
for row in rows:
    p=E/row['path'];raw=p.read_bytes();need(hashlib.sha256(raw).hexdigest()==row['sha256'],'input changed during publication')
    q=T/row['path'];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
    need(sha(q)==row['sha256'],'copy hash mismatch')
manifest=dict(record_type='BOUNDED_RESEARCH_DELIVERY_NOT_NEURAL_EXECUTION',files=rows,file_count=len(rows),bytes=sum(r['bytes']for r in rows),new_GPU_trials=0,new_model_calls=0,manuscript_and_anonymous_artifact_unchanged=True,large_raw_result_scope='8TB only; no models/datasets/cache/raw Consumer/character identity traces copied',execution_commits='See per-experiment source manifests/bundles; publication commit is not any execution source commit')
(T/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in manifest.items()if k!='files'}))
