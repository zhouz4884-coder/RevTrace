import ast,hashlib,json,subprocess
from pathlib import Path
F=Path(__file__).resolve().parent;R=F.parents[1];S=F/'analysis_source_v1'
def git(*args,cwd=S):return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
def h(p):
    b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
for p in S.glob('*.py'):ast.parse(p.read_text(encoding='utf8'),filename=p.name)
plan=json.loads((F/'PLAN_v1.json').read_bytes());assert len(plan['cells'])==12
assert h(F/'PLAN_v1.json')['sha256']=='fb344f88774b8cdae15af213e66f296adcaf4632fa982383e730f92a18023b84'
git('init','-b','codex/midpoint-analysis-v1');git('config','core.autocrlf','false');git('add','.');git('commit','-m','Freeze one midpoint analysis, original recounters, strong-witness controls and allocated launch')
commit=git('rev-parse','HEAD');files=[dict(path=p,**h(S/p)) for p in git('ls-files').splitlines()]
put(F/'ANALYSIS_SOURCE_v1.json',dict(code_commit=commit,files=files))
git('bundle','create',str(F/'ANALYSIS_SOURCE_v1.bundle'),'--all');git('fetch',str(F/'ANALYSIS_SOURCE_v1.bundle'),'HEAD:refs/heads/codex/midpoint-analysis-v1',cwd=R)
put(F/'CPU_CONFIG_v1.json',dict(experiment_id='REVTRACE-DSN-MIDPOINT-PREPARATION-CPU-20261029-V1',
    expected_tests=17,analysis_source_commit=commit,source_manifest_sha256=h(F/'ANALYSIS_SOURCE_v1.json')['sha256'],
    frozen_plan_sha256=h(F/'PLAN_v1.json')['sha256'],source_selection_sha256=h(F/'SOURCE_SELECTION_v1.json')['sha256'],
    tests='six timely-continuity + eleven strong-witness/non-EOS controls',no_runtime_or_models_imported=True,GPU_calls=0,
    output=str(F/'CPU_TESTS_v1'),raw_result_location=str(F/'CPU_TESTS_v1/RAW.log'),
    aggregate_summary_location=str(F/'CPU_TESTS_v1/SUMMARY.json'),gate_decision_location=str(F/'CPU_TESTS_v1/GATE.json')))
put(F/'ANALYSIS_FREEZE_RECEIPT_v1.json',dict(code_commit=commit,files=len(files),manifest=h(F/'ANALYSIS_SOURCE_v1.json'),
    frozen_plan=h(F/'PLAN_v1.json'),CPU_config=h(F/'CPU_CONFIG_v1.json'),remote_staging='NOT_PERFORMED',GPU_calls=0))
print(json.dumps(dict(code_commit=commit,files=len(files),manifest_sha256=h(F/'ANALYSIS_SOURCE_v1.json')['sha256'])))
