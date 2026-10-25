from pathlib import Path
import argparse,hashlib,json
p=argparse.ArgumentParser();p.add_argument('--python',type=Path,required=True);p.add_argument('--javascript',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
assert not a.output.exists()
x=json.loads(a.python.read_text());y=json.loads(a.javascript.read_text());assert len(x['results'])==len(y['results'])==63
for left,right in zip(x['results'],y['results']):
    for key in ['config','complete','states','transitions','reachable_state_sha256','violations']:
        assert left[key]==right[key],(left['config'],key,left[key],right[key])
out={'status':'PASS_TWO_IMPLEMENTATION_COMPLETE_FINITE_STATE_CROSSCHECK',
    'configurations':63,'full_guard_configurations':7,
    'states_over_configurations_not_unique_global_states':sum(r['states'] for r in x['results']),
    'transitions_over_configurations':sum(r['transitions'] for r in x['results']),
    'python_sha256':hashlib.sha256(a.python.read_bytes()).hexdigest(),
    'javascript_sha256':hashlib.sha256(a.javascript.read_bytes()).hexdigest(),
    'independence_scope':'separately implemented Python BFS and JS DFS against one specification; not independent authors or an unbounded proof',
    'limits':x['bounds'],'results':[{'config':r['config'],'states':r['states'],'violations':r['violations']} for r in x['results']]}
a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='results'}))
