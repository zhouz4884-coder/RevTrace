"""Source/metadata freeze only during pilot. Never imports tests or raw readers."""
from pathlib import Path
import ast,datetime,hashlib,json,shutil,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1];D=E/'opportunity_audit_dev_v1';S=E/'opportunity_audit_source_v1';P=E/'opportunity_packages_v1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
    with Path(p).open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.STDOUT).strip()
contract=E/'plans/PILOT_OPPORTUNITY_AND_INTERPRETATION_v5.json';plan=E/'baseline_ops/PILOT_PREPARATION_V2/SERVICE_PLAN.json'
assert sha(contract)=='32fcbdf1cac6f74326b9569a874d3d6d7b80b12757e4dd0e61b91d72ce0e4989'
assert sha(plan)=='2ceea09f423987faf1b9b3343c15e69ab2f3c437d9e40deb31d6512c30380ed6'
assert sha(D/'job_accounting.py')=='c98a7777274a12e491f05cfcbf11cfa558d9f8aa4dca93f305e77399f7d230b0'
assert git(R,'cat-file','-t','de0936b2e30179d63aeef6e235cd1af685578c58')=='commit'
assert git(R,'cat-file','-t','f367c4e1068a9391a0e99d8537c94995a3388e13')=='commit'
tests=[]
for path in D.glob('*.py'):
    tree=ast.parse(path.read_text(encoding='utf8'),filename=str(path))
    if path.name=='test_opportunities.py':tests=[n.name for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
assert len(tests)==22
S.mkdir(exist_ok=False);P.mkdir(exist_ok=False)
for path in sorted(D.iterdir()):
    if path.is_file():shutil.copyfile(path,S/path.name)
(S/'.gitattributes').write_text('* -text\n',encoding='utf8');(S/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf8')
put(S/'ANALYSIS_BINDINGS.json',dict(record_type='AUTHORED_IMPLEMENTATION_BINDING_NOT_EXPERIMENT_RESULT',
    metric_contract_sha256=sha(contract),pilot_plan_sha256=sha(plan),actual_NN_source_commit='de0936b2e30179d63aeef6e235cd1af685578c58',
    actual_NN_manifest_sha256='ce99ca421f5f8b416a1545c57a600ee6a28f43e7d2c10294caa00f0d6636a7c9',
    actual_driver_source_commit='f367c4e1068a9391a0e99d8537c94995a3388e13',
    actual_driver_manifest_sha256='c9c0fa0c14424fae51d3e822f35286ba69c28b11233fa6c2aef848a231ec724b',
    intended_experiment_id='REVTRACE-V16-PILOT-OPPORTUNITY-AUDIT-20261111-V1',expected_cells=24,expected_speaker_clusters=2,
    source_authored_during_timed_pilot=True,source_not_claimed_frozen_before_first_serving_cell=True,
    metric_contract_declared_before_serving=True,author_observed_serving_outcomes=False,
    tests_authored=tests,tests_executed=False,raw_input_freeze_not_yet_performed=True,new_model_calls=0))
git(S,'init');git(S,'config','core.autocrlf','false');git(S,'checkout','-b','codex/v16-pilot-opportunity-audit-v1');git(S,'add','.');git(S,'commit','-m','Freeze actual-trace opportunity predicates and post-pilot-only CPU audit')
commit=git(S,'rev-parse','HEAD');assert not git(S,'status','--porcelain','--untracked-files=all')
files=git(S,'ls-files').splitlines();manifest=dict(code_commit=commit,source_commit=commit,
    external_execution_dependencies=dict(NN='de0936b2e30179d63aeef6e235cd1af685578c58',driver='f367c4e1068a9391a0e99d8537c94995a3388e13'),
    scope='Authored/frozen post-pilot-only actual-trace CPU opportunity audit; no tests/raw audit/model runs at freeze',
    files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in files])
mp=P/'SOURCE.json';put(mp,manifest);bundle=P/'SOURCE.bundle';git(S,'bundle','create',str(bundle),'HEAD');git(R,'bundle','verify',str(bundle));git(R,'fetch',str(bundle),'HEAD:refs/revtrace/execution/v16-pilot-opportunity-audit-v1')
assert git(R,'cat-file','-t',commit)=='commit'
receipt=dict(record_type='SOURCE_FREEZE_ONLY_NOT_CPU_ANALYSIS_OR_TEST',code_commit=commit,source_root=str(S),source_files=len(files),
    source_manifest=str(mp),source_manifest_sha256=sha(mp),bundle=str(bundle),bundle_sha256=sha(bundle),
    root_execution_ref='refs/revtrace/execution/v16-pilot-opportunity-audit-v1',tests_authored=len(tests),tests_run=False,
    live_serving_outcome_files_read=False,raw_inputs_frozen=False,models_loaded=False,GPU_launches=0,CURRENT_modified=False,
    Root_idle_window_required_before_any_test_or_raw_read=True,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
put(P/'FREEZE_RECEIPT.json',receipt);print(json.dumps(receipt))
