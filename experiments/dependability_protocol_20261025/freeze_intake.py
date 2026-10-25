"""P0 byte identity and complete N1 baseline source, excluding CES policies."""
from pathlib import Path
import csv,hashlib,json,shutil,subprocess
W=Path(__file__).resolve().parent;root=W.parents[1];repo=W.parent/'online_admission_20261022/git_delivery_stage_v1';ref='d800523139d30486ca9158f06e750a2d80fcb9fc';idx=json.loads((W/'PUBLIC_TREE_INDEX.json').read_text());lookup={r['path']:r for r in idx['files']}
def blob(path):
 r=lookup[path];d=subprocess.check_output(['git','-C',str(repo),'cat-file','blob',r['git_blob']]);assert hashlib.sha1(b'blob '+str(len(d)).encode()+b'\0'+d).hexdigest()==r['git_blob'];return d
def sha(d):return hashlib.sha256(d).hexdigest()
base='experiments/causal_row_completion_20261023/runtime';m=json.loads(blob(base+'/SOURCE_MANIFEST.json'));S=W/'runtime';assert not S.exists();S.mkdir();files=[]
for r in m['files']:
 d=blob(base+'/'+r['path']);assert sha(d)==r['sha256'],r['path'];p=S/r['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(d);files.append({'path':r['path'],'bytes':len(d),'sha256':sha(d)})
(W/'N1_BASELINE_SOURCE.json').write_text(json.dumps({'public_commit':ref,'original_measured_code_commit':m['code_commit'],'files':files,'no_CES_scheduler_added':True},indent=2)+'\n')
core=['src/revtrace/live_qwen.py','src/revtrace/dgft.py','src/revtrace/durable_journal.py','src/revtrace/certified_display.py','src/revtrace/continuity_proof.py','scripts/tc_live_worker.py']
rows=[]
for name in core:
 hashes={}
 for tag,prefix in [('phaseN','experiments/phase_n_20261021/runtime'),('phaseD','experiments/phase_d_20261021/runtime'),('row150',base),('v6_public','experiments/ces_v6_abcd_20261025/runtime_D')]:
  p=prefix+'/'+name;hashes[tag]=sha(blob(p)) if p in lookup else 'NOT_PRESENT'
 for tag,prefix in [('dirty_root',root),('v6_local',W.parent/'ces_v6_abcd_20261025/runtime_D')]:
  p=prefix/name;hashes[tag]=sha(p.read_bytes()) if p.exists() else 'NOT_PRESENT'
 rows.append({'path':name,**hashes,'v6_local_equals_public':hashes['v6_local']==hashes['v6_public'],'row_equals_latest_v6':hashes['row150']==hashes['v6_public']})
with (W/'P0_CORE_SOURCE_COMPARISON.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
E0=Path(r'D:\StreamTxn\outputs\revtrace_dsn_sixweek_20261018\sources\E0_invariant_audit_20261015.md');target=W/'baseline/E0_invariant_audit_20261015.md';assert not target.exists();shutil.copy2(E0,target)
v6files=['RESEARCH_REPORT.zh.md','D_SOURCE_MANIFEST.json','FINAL_DECISIONS.json'];v6=[]
for name in v6files:
 local=W.parent/'ces_v6_abcd_20261025'/name;public='experiments/ces_v6_abcd_20261025/'+name
 v6.append({'path':name,'local_sha256':sha(local.read_bytes()),'public_sha256':sha(blob(public)),'equal':local.read_bytes()==blob(public)})
result={'status':'PASS_P0_CORE_AND_BASELINE_SOURCE_IDENTITIES','paper':json.loads((W/'baseline/PDF_IDENTITY.json').read_text()),'public_main':ref,'N1_base_measured_commit':m['code_commit'],'N1_base_files':len(files),'core':rows,'v6_frozen_materials':v6,'E0_sha256':sha(target.read_bytes()),'local_v6_newer_scope':'Publication receipt/ACTIVE_STATE only; measured source, research report and final decisions equal public snapshot','dirty_root_is_not_measured_runtime':True}
(W/'P0_IDENTITY_AUDIT.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8');print(json.dumps({'status':result['status'],'base_files':len(files),'base_commit':m['code_commit'],'v6_frozen_equal':all(r['equal'] for r in v6),'core_equal_row_vs_v6':[r['path'] for r in rows if r['row_equals_latest_v6']]}))
