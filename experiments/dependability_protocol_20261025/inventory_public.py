"""Read Git objects, never the dirty historical worktree, for evidence discovery."""
from pathlib import Path
import hashlib,json,subprocess
W=Path(__file__).resolve().parent;repo=W.parent/'online_admission_20261022/git_delivery_stage_v1';ref='d800523139d30486ca9158f06e750a2d80fcb9fc'
prefixes=['phase_n_20261021','phase_d_20261021','online_admission_20261022','online_admission_c2_audit_20261022','causal_row_completion_20261023','research_opportunity_20261022','causal_evidence_scheduling_20261023','ces_v5_closed_loop_20261025','ces_v6_abcd_20261025']
raw=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--long','-z',ref,'--',*[f'experiments/{p}' for p in prefixes]])
records=[]
for row in raw.split(b'\0'):
 if not row:continue
 meta,name=row.split(b'\t',1);mode,kind,oid,size=meta.decode().split();path=name.decode()
 records.append({'path':path,'bytes':int(size),'git_blob':oid,'mode':mode,'kind':kind})
out=W/'PUBLIC_TREE_INDEX.json';assert not out.exists();out.write_text(json.dumps({'commit':ref,'files':records},indent=2)+'\n')
selected=[r for r in records if r['path'].lower().endswith('.md') and any(t in r['path'].lower() for t in ['report','readme','e0','e1','r5','claim','boundary','scope','protocol'])]
print(json.dumps({'commit':ref,'files':len(records),'reports':[{'path':r['path'],'bytes':r['bytes']} for r in selected if r['bytes']<200000]},ensure_ascii=False))
