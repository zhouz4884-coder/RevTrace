"""Freeze reviewed CPU source and preregister all29 raw/110metadata/new8 inputs."""
from pathlib import Path
import ast,hashlib,json,shutil,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1];H=E/'history_ops'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_dsn_strengthening_v16_20261111/history_cpu_v1'
O=B+'/results/revtrace/dsn_strengthening_v16_20261111/history_cpu_v1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 with Path(p).open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def run(args):return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT).strip()
pointer=R/'experiments/repository_identity_20261027/CURRENT.json';before=sha(pointer)
rootgate=H/'ROOT_DEFAULT_PREFLIGHT_v1.json'
run(['python','-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--output',str(rootgate)])
assert sha(pointer)==before
S=H/'source_v1';S.mkdir(exist_ok=False)
for p in sorted((E/'history_source').iterdir()):
 if p.is_file():
  if p.suffix=='.py':ast.parse(p.read_text(encoding='utf8'))
  shutil.copyfile(p,S/p.name)
(S/'.gitattributes').write_text('* -text\n',encoding='utf8')
(S/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf8')
run(['git','-C',str(S),'init']);run(['git','-C',str(S),'config','core.autocrlf','false'])
run(['git','-C',str(S),'checkout','-b','codex/v16-history-cpu-v1'])
run(['git','-C',str(S),'add','.']);run(['git','-C',str(S),'commit','-m','Freeze Unicode actual Consumer edit and paired historical CPU analysis'])
commit=run(['git','-C',str(S),'rev-parse','HEAD']);assert not run(['git','-C',str(S),'status','--porcelain','--untracked-files=all'])
files=run(['git','-C',str(S),'ls-files']).splitlines()
manifest=dict(code_commit=commit,scope='Offline CPU actual-Consumer content29, all110 frozen metadata and exactnew8 paired sensitivity; zero new model calls',
 files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in files])
mp=H/'SOURCE_v1.json';put(mp,manifest)
bundle=H/'SOURCE_v1.bundle';run(['git','-C',str(S),'bundle','create',str(bundle),'HEAD'])
run(['git','-C',str(R),'bundle','verify',str(bundle)])
run(['git','-C',str(R),'fetch',str(bundle),'HEAD:refs/heads/codex/v16-history-cpu-v1'])
assert run(['git','-C',str(R),'cat-file','-t',commit])=='commit'
explicit=H/'EXPLICIT_SOURCE_PREFLIGHT_v1.json'
run(['python','-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--source',str(S),'--manifest',str(mp),'--output',str(explicit)])
inventory=json.loads((H/'INPUT_AVAILABILITY.json').read_bytes());assert len(inventory['cells'])==29 and all(c['exists'] for c in inventory['cells'])
ops=R/'experiments/physical_retirement_20261028/H3_RESULTS_v2/opportunities/SOURCE_OPPORTUNITIES.json'
oprows=json.loads(ops.read_bytes())
oldrecord=json.loads((R/'experiments/dsn_native_content_20261029/RESULTS_v1/INPUT_HASHES.json').read_bytes())
h3record=json.loads((R/'experiments/physical_retirement_20261028/H3_RESULTS_v2/opportunities/ANALYSIS_RECORD.json').read_bytes())['inputs']
cells=[]
for c in inventory['cells']:
 original=oldrecord if c['schema']=='native' else h3record
 assert original[c['consumer_path']]['sha256']==c['consumer_sha256']
 assert original[c['consumer_path']]['bytes']==c['bytes']
 cell={k:c[k] for k in ('cell_id','bank','stage','arm','cohort','repeat','consumer_path','consumer_sha256','schema')}
 if c['schema']=='core':
  cell['session_source_map']={str(x['session_id']):x['source_id'] for x in oprows if x['cell_id']==c['cell_id'] and x['clock_scope']=='consumer_apply'}
  assert len(cell['session_source_map'])==8
 cells.append(cell)
meta_paths=dict(h3_runs=R/'experiments/physical_retirement_20261028/H3_RESULTS_v2/aggregate/RUNS.json',
 h3_opportunities=ops,h3_sources=R/'experiments/physical_retirement_20261028/H3_RESULTS_v2/aggregate/SOURCE_METRICS.json',
 old14_lcp_runs=R/'experiments/dsn_native_content_20261029/RESULTS_v1/RUNS.json',
 new8_report=R/'experiments/dsn_native_confirmation_20261102/results/RESULTS_REPORT_RUN_V2/SUMMARY.json')
metadata=H/'metadata_v1';metadata.mkdir(exist_ok=False)
for name,path in meta_paths.items():shutil.copyfile(path,metadata/(name+'.json'))
cfg=dict(experiment_id='REVTRACE-V16-HISTORICAL-CONTENT-PAIRS-20261111-V1',designated_experiment_disk_prefix=B,
 age_threshold_seconds=2.0,expected_controls=16,cells=cells,metadata_inputs={n:dict(path=P+'/metadata/'+n+'.json',sha256=sha(p)) for n,p in meta_paths.items()},
 raw_result_location=O,actual_analysis_source=commit,measured_neural_sources=dict(native_old14='61c9afac00561f7ff1351f3eba9fd95adb239e8c',
 H3='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf',new8='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'),
 evidence_tier='New frozen offline CPU analysis of historical real service observations; not new GPU evidence',
 no_deadline_or_service_clock_change=True,stages_banks_separate=True)
cp=H/'CONFIG_v1.json';put(cp,cfg)
env=H/'ENVIRONMENT_v1.json';put(env,dict(**inventory['environment'],CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',
 standard_library_only=True,model_imports=False,new_model_calls=0))
pre=dict(experiment_id=cfg['experiment_id'],code_commit=commit,frozen_config_sha256=sha(cp),source_manifest_sha256=sha(mp),environment_sha256=sha(env),
 root_preflight_path=P+'/ROOT_DEFAULT_PREFLIGHT_v1.json',root_preflight_sha256=sha(rootgate),raw_result_location=O,
 aggregate_summary_location=O+'/SUMMARY.json',gate_decision_location=O+'/GATE.json',
 frozen_config=P+'/CONFIG_v1.json',environment_record=P+'/ENVIRONMENT_v1.json',
 source_bundle_sha256=sha(bundle),remote_source=P+'/source_v1',local_resolvable_ref='refs/heads/codex/v16-history-cpu-v1')
put(H/'PRELAUNCH_v1.json',pre)
put(H/'LOCAL_FREEZE_RECEIPT_v1.json',dict(**pre,source_files=len(files),raw_consumer_cells=29,raw_consumer_bytes=sum(c['bytes'] for c in inventory['cells']),
 original_raw_hashes_match_historical_records=True,local_default_pointer_sha256_before=before,local_default_pointer_sha256_after=sha(pointer),
 tests_executed_yet=False,GPU_or_model_launches=0))
print(json.dumps(dict(commit=commit,files=len(files),manifest_sha256=sha(mp),config_sha256=sha(cp),raw_cells=29,
 source=str(S),prelaunch=str(H/'PRELAUNCH_v1.json'),tests_executed_yet=False,CURRENT_unchanged=sha(pointer)==before)))
