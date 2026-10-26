"""Frozen source delta and no-paper-touch evidence; no external writes."""
from pathlib import Path
import json,hashlib,sys
W=Path(__file__).resolve().parent;BASE=W.parent/'dependability_protocol_20261025'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((BASE/'N5_SOURCE_MANIFEST_v3.json').read_text())
new=json.loads((W/'SOURCE_v6.json').read_text())
a={r['path']:r for r in old['files']};b={r['path']:r for r in new['files']}
assert all(sha(W/'runtime'/n)==r['sha256'] for n,r in b.items())
assert all(sha(BASE/'runtime_n5_v3'/n)==r['sha256'] for n,r in a.items())
delta=dict(base_commit=old['code_commit'],new_commit=new['code_commit'],
    base_files=len(a),new_files=len(b),added=sorted(set(b)-set(a)),deleted=sorted(set(a)-set(b)),
    changed=[dict(path=n,before=a[n]['sha256'],after=b[n]['sha256']) for n in a.keys()&b.keys() if a[n]['sha256']!=b[n]['sha256']],
    unchanged=sum(a[n]['sha256']==b[n]['sha256'] for n in a.keys()&b.keys()))
assert not delta['deleted']
candidate=BASE/'candidate_20261026/main.pdf'
assert sha(candidate)=='aa16d677097c2b5c14e55d3a51fc314e38eaecb44cb363413a8f60a99bf7c3c5'
delta['frozen_paper_sha256']=sha(candidate);delta['no_paper_rewrite']=True
tag=sys.argv[1] if len(sys.argv)>1 else 'v1';p=W/('SOURCE_DELTA_'+tag+'.json');assert not p.exists()
p.write_text(json.dumps(delta,indent=2)+'\n');print(json.dumps(delta))
