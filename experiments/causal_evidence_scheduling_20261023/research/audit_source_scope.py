"""Byte-level safety-substrate preservation, not an experiment outcome."""
from pathlib import Path
import ast,hashlib,json,subprocess
W=Path(__file__).resolve().parent;S=W/'runtime';old=W.parent/'causal_row_completion_20261023/source_row_sdk_v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((S/'SOURCE_MANIFEST.json').read_text());assert manifest['code_commit']=='e0aeae1b418644c378dde331c59b55fc5948b40f'
for r in manifest['files']:assert sha(S/r['path'])==r['sha256']
protected=['src/revtrace/'+n+'.py' for n in ['dgft','live_qwen','durable_journal','certified_display','continuity_proof','standard_safe_async','sequence_verifier','online_admission','row_lifecycle','row_stream']]+['scripts/online_selection_worker.py']
assert all(sha(S/n)==sha(old/n) for n in protected)
t=ast.parse((S/'src/revtrace/ces_runtime.py').read_text());features=next(n for n in ast.walk(t) if isinstance(n,ast.FunctionDef) and n.name=='_features')
assert 'fault' not in ast.unparse(features).lower() and 'donor' not in ast.unparse(features).lower()
current={r['path']:r['sha256'] for r in manifest['files']};base=json.loads((old/'SOURCE_MANIFEST.json').read_text())['files']
delta=[r['path'] for r in base if current[r['path']]!=r['sha256']]
new=sorted(set(current)-{r['path'] for r in base})
out={'status':'PASS_NAMED_SDK_SAFETY_SUBSTRATE_UNCHANGED','source_commit':manifest['code_commit'],
 'base_sdk_commit':'2bc71af5457de5d065ff9e771d2fad428c5c6ed9','protected_byte_identical':{p:sha(S/p) for p in protected},
 'modified_existing_paths':delta,'new_paths':new,'features_do_not_read_fault_or_donor_fields':True,
 'not_a_formal_novelty_or_performance_proof':True}
(W/'SOURCE_SCOPE_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='protected_byte_identical'}))
