"""Prepare immutable cost inputs using the committed observer source; no model launch."""
from pathlib import Path
import hashlib,json
from remote import Remote,E,B,P,O,PY

M=E/'packages/COST_V1_SOURCE.json';commit=json.loads(M.read_bytes())['code_commit']
control=E/'cost/plan_v1';control.mkdir(exist_ok=False)
params=dict(source=P+'/cost_v1',manifest=P+'/COST_V1_SOURCE.json',commit=commit,
    paired=B+'/projects/revtrace_dsn_strengthening_20261031/PAIRED32_v2_FROZEN.json',
    configs=P+'/cost_configs_v1',raw=O+'/cost_v1',python=PY)
script='C='+repr(params)+'\n'+r'''
from pathlib import Path
import hashlib,json,os,subprocess
s=Path(C['source']);m=json.loads(Path(C['manifest']).read_bytes())
assert subprocess.check_output(['git','-C',str(s),'rev-parse','HEAD'],text=True).strip()==C['commit']
assert not subprocess.check_output(['git','-C',str(s),'status','--porcelain','--untracked-files=all'],text=True).strip()
for r in m['files']:assert (s/r['path']).stat().st_size==r['bytes'] and hashlib.sha256((s/r['path']).read_bytes()).hexdigest()==r['sha256']
cmd=[C['python'],'-B',str(s/'build_plan.py'),'--paired-plan',C['paired'],'--observer-commit',C['commit'],'--observer-manifest',C['manifest'],'--out',C['configs'],'--raw-root',C['raw']]
r=subprocess.run(cmd,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'),capture_output=True)
if r.returncode:raise RuntimeError((r.stdout+r.stderr).decode(errors='replace'))
plan=json.loads((Path(C['configs'])/'PLAN.json').read_bytes())
print(json.dumps(dict(plan=str(Path(C['configs'])/'PLAN.json'),cells=len(plan['cells']),cpu=len(plan['cpu_cases']),dependency=plan['original_dependency'],environment_python=plan['environment_python'],runtime_environment=plan['runtime_environment'],no_model_calls=True)))
'''
with Remote() as c:
    raw=c.python(script);(control/'PREPARATION_RECEIPT.json').write_bytes(raw)
    plan=json.loads(c.get(params['configs']+'/PLAN.json',control/'PLAN.json'))
    for cell in plan['cells']:
        c.get(cell['config'],control/Path(cell['config']).name)
    print(raw.decode())
