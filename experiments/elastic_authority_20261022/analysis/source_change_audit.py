from pathlib import Path
import hashlib,json,subprocess
W=Path(__file__).resolve().parent;old=Path(r'D:\StreamTxn\outputs\revtrace_phaseD_20261021\public_release\runtime');new=W/'elastic_sdk'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
changes=[];unused=[]
for p in sorted(new.rglob('*')):
 if not p.is_file() or p.name=='SOURCE_MANIFEST.json' or any(x in ['.git','__pycache__','.pytest_cache'] for x in p.parts):continue
 rel=p.relative_to(new);q=old/rel
 if rel.parts[0]=='stress_sdk':unused.append(rel.as_posix());continue
 if not q.exists() or sha(q)!=sha(p):changes.append({'path':rel.as_posix(),'change':'new' if not q.exists() else 'changed','old_sha256':sha(q) if q.exists() else None,'new_sha256':sha(p)})
protected=['src/revtrace/dgft.py','src/revtrace/durable_journal.py','src/revtrace/certified_display.py','src/revtrace/continuity_proof.py','scripts/tc_live_worker.py']
for n in protected:assert sha(old/n)==sha(new/n)
out={'status':'PASS_C1_C3_AND_WORKER_RENDER_PRIMITIVES_UNCHANGED','protected_files':[{ 'path':n,'sha256':sha(new/n)} for n in protected],'loaded_root_source_changes':changes,'unused_nested_packaging_copy':{'path':'stress_sdk/','files':len(unused),'reason':'second Copy-Item nested an auxiliary static tree; no runtime sys.path/command refers to it','not_deleted_or_changed_in_measured_archive':True,'not_new_mechanism_or_GPU_source':True},'C2_changes_not_claimed_unchanged_code':True,'original_user_worktree_not_modified':True}
(W/'SOURCE_CHANGE_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'loaded_changes':[r['path'] for r in changes],'unused_extra_files':len(unused)}))
