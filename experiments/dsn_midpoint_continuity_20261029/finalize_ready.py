import hashlib,json,subprocess,sys
from pathlib import Path
F=Path(__file__).resolve().parent;R=F.parents[1]
def h(p):
    b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
preflight=R/'experiments/repository_identity_20261027/preflight.py'
for name,args in [('CURRENT_SOURCE_GATE_LOCAL_v1.json',[]),('ANALYSIS_SOURCE_GATE_LOCAL_v1.json',['--source',str(F/'analysis_source_v1'),'--manifest',str(F/'ANALYSIS_SOURCE_v1.json')])]:
    r=subprocess.run([sys.executable,'-B',str(preflight),*args],cwd=R,capture_output=True,text=True,check=True)
    report=json.loads(r.stdout);assert report['gate']=='SOURCE_IDENTITY_PASS';put(F/name,report)
cpu=json.loads((F/'CPU_TESTS_v1/GATE.json').read_bytes());assert cpu['gate']=='PASS_17_SYNTHETIC_CPU_CONTROLS'
source=json.loads((F/'ANALYSIS_SOURCE_v1.json').read_bytes())
put(F/'READY_v1.json',dict(status='FROZEN_LOCAL_READY_WAIT_ROOT_ALLOCATION',planned_GPU_cells=12,actual_new_GPU_calls=0,
    remote_staging_performed=False,CURRENT_modified=False,runtime_source_changed=False,
    analysis_source_commit=source['code_commit'],source_manifest=h(F/'ANALYSIS_SOURCE_v1.json'),
    plan=h(F/'PLAN_v1.json'),source_selection=h(F/'SOURCE_SELECTION_v1.json'),CPU_controls=cpu,
    actual_neural_source_commit='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf',
    execution_order=['joint24 and CPU analysis','native prescribed gated scope and CPU analysis','this midpoint12'],
    decision='Only one midpoint; low opportunity or unmet strong conditions still STOP; no10/11/additional repeats',
    legacy_checkout_HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),
    local_preflight_scope='current preparation identity only; fresh no-argument preflight required again at actual launch'))
print(json.dumps(dict(status='FROZEN_LOCAL_READY_WAIT_ROOT_ALLOCATION',plan_sha256=h(F/'PLAN_v1.json')['sha256'],analysis_source_commit=source['code_commit'],GPU_calls=0)))
