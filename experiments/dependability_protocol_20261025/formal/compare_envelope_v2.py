from pathlib import Path
import argparse,hashlib,json
p=argparse.ArgumentParser();p.add_argument('--python',type=Path,required=True);p.add_argument('--javascript',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
x=json.loads(a.python.read_text());y=json.loads(a.javascript.read_text());assert len(x['results'])==len(y['results'])==20
for l,r in zip(x['results'],y['results']):
    for field in ['config','complete','states','transitions','reachable_sha256','violations']:assert l[field]==r[field],(l['config'],field)
assert not a.output.exists()
out=dict(status='PASS_COMPLETE_CDE_FINITE_BFS_DFS_REACHABLE_STATE_CROSSCHECK',configurations=20,
    summed_state_visits=sum(r['states'] for r in x['results']),summed_edges=sum(r['transitions'] for r in x['results']),
    bounds=x['bounds'],limits=x['limits'],
    python_sha256=hashlib.sha256(a.python.read_bytes()).hexdigest(),javascript_sha256=hashlib.sha256(a.javascript.read_bytes()).hexdigest(),
    independence='separate Python BFS and JavaScript DFS implementations, same shared specification, not independent authors or implementation refinement proof',
    positive_control='correct policy/manifest-based reservation reconstruction also preserves invariants; explicit reservation logging is not uniquely necessary',results=y['results'])
a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='results'}))
