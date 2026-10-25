from pathlib import Path
import hashlib,json,subprocess
W=Path(__file__).resolve().parent;repo=W.parent/'online_admission_20261022/git_delivery_stage_v1'
idx=json.loads((W/'PUBLIC_TREE_INDEX.json').read_text());O=W/'public_tables';O.mkdir(exist_ok=False)
chosen=[r for r in idx['files'] if r['path'].endswith('.csv') and r['bytes']<500000 and
    (r['path'].startswith('experiments/phase_n_20261021/tables/') or
     r['path'].startswith('experiments/phase_d_20261021/tables/') or
     r['path'].startswith('experiments/causal_row_completion_20261023/reports/') or
     r['path'].endswith('GROUPS.csv'))]
files=[]
for r in chosen:
    data=subprocess.check_output(['git','-C',str(repo),'cat-file','blob',r['git_blob']])
    assert len(data)==r['bytes'] and hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==r['git_blob']
    p=O/r['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    files.append(dict(r,sha256=hashlib.sha256(data).hexdigest()))
(W/'PUBLIC_TABLE_MANIFEST.json').write_text(json.dumps({'commit':idx['commit'],'files':files},indent=2)+'\n')
print(json.dumps({'files':len(files),'bytes':sum(r['bytes'] for r in files)}))
