"""Bind complete actual36 inputs, then invoke frozen 038 table/figure CLI.

The wrapper materializes declarative input/config records; all table/plot numeric
logic is in the separately frozen helper commit. No CURRENT/model/NN mutation.
"""
from __future__ import annotations
import datetime, hashlib, importlib.util, json, pathlib, platform, subprocess, sys
sys.dont_write_bytecode = True
F=pathlib.Path(__file__).resolve().parents[1]; R=F.parents[1]
SOURCE=F/'figure_tools_source_v4'; COMMIT='2ab6036b9c481d562575919a6832d6159742c528'
BOUNDED=F/'BOUNDED_FORMAL36_RESULTS_v3'; AUDIT=F/'FORMAL_ACTUAL36_TRACE_RESULTS_v1'
PREFIX=F/'FIGURE_TABLE_FORMAL36_v4'; OUT=F/'FIGURE_TABLE_FORMAL36_v4_results'
def read(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):
 if p.exists(): raise ValueError('Never overwrite actual input/result evidence: '+str(p))
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def name(s): return F/('FIGURE_TABLE_FORMAL36_v4_'+s)
if OUT.exists(): raise ValueError('New result directory required')
b=read(BOUNDED/'GATE.json'); a=read(AUDIT/'GATE.json')
if b['status']!='PASS_ALL36_BOUNDED_SERIES_AND_ORIGINAL_ENDPOINT_RECOUNTS' or b['cases']!=36 or b['code_commit']!='038ea6eb58a790fd11910ce8030604b5b1097705': raise ValueError('Wrong complete bounded bank')
if a['status']!='PASS_ALL_FORMAL36_ACTUAL_ORIGINAL_FULLCALL_REFINEMENT' or a['cases']!=36: raise ValueError('Wrong complete independent trace bank')
byid={r['cell_id']:r['gate'] for r in a['results']}
spec=importlib.util.spec_from_file_location('figure_explicit_identity',R/'experiments/repository_identity_20261027/preflight.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
identity=p.check(SOURCE,F/'packages/FIGURE_TOOLS_SOURCE_v4.json')
if identity['code_commit']!=COMMIT: raise ValueError('Wrong analysis source')
put(name('EXPLICIT_ANALYSIS_SOURCE_PREFLIGHT.json'),identity)
plans=[]; trials=[]; inputs=[BOUNDED/'GATE.json',BOUNDED/'COLLECTION_MANIFEST.json',AUDIT/'GATE.json',F/'NATIVE_WORK_RECOUNT_RESULTS_v1/results/SUMMARY.json',F/'NATIVE_WORK_RECOUNT_RESULTS_v1/results/GATE.json']
total=0
for planfile,cfgdir in [('FORMAL_SHORT28_v1_FROZEN.json','formal_short28_v1_configs'),('FORMAL_SUSTAINED8_v1_FROZEN.json','formal_sustained8_v1_configs')]:
 path=F/planfile; plan=read(path);inputs.append(path)
 plans.append(dict(path=planfile,sha256=sha(path),frozen_configs_dir=cfgdir))
 for cell in plan['cells']:
  cid=cell['cell_id']; gate=byid[cid]; folder=BOUNDED/'cells'/cid
  config=read(folder/'CONFIG.json'); expected=sum((s['frames']+7999)//8000 for s in config['settings']['sources'])
  gatepath=AUDIT/'cases'/cid/'GATE.json'
  if gate!=read(gatepath): raise ValueError('Independent per-case gate differs from aggregate')
  if gate['status']!='PASS_ACTUAL_ORIGINAL_FULLCALL_DURABLE_AND_CONSUMER_REFINEMENT' or gate['durable_original_transitions']!=expected or gate['actual_runtime_source_commit']!=plan['source_commit']: raise ValueError('Incomplete structural refinement premise')
  if gate['local_rejection_audit']['insufficient_rejection_snapshots']!=0 or gate['legal_progress_wrong_rejections']!=0: raise ValueError('Rejection audit incomplete or negative; preserve unknown/negative instead of zero')
  total+=expected
  cohort='sustained' if plan['campaign_kind']=='formal_sustained8' else 'short_regression' if cell.get('tier')=='fixed_prior_source_regression' else 'short_main'
  trials.append(dict(bounded_dir=str(folder.resolve()),cohort=cohort,condition=cell['fault_kind'],semantic_audit=dict(
   illegal_installs=0,legal_progress_wrong_rejections=gate['legal_progress_wrong_rejections'],
   checker_source_commit=gate['checker_source_commit'],checker_summary_sha256=sha(gatepath),checker_summary_path=str(gatepath.resolve()),
   checked_durable_transitions=expected,
   scope='Zero observed structural Canonical refinement violations after independent fail-closed validation of every supplied durable transition/full-call/Consumer application. Trusted host/source and complete adapter-state premise; not GPU arithmetic attestation, natural prevalence or an unbounded proof.')))
  inputs.extend([gatepath,folder/'COLLECTION_METADATA.json',F/cfgdir/(cid+'.json')])
if len(trials)!=36 or total!=3976: raise ValueError('Exact 36/3976 coverage required')
index=name('INDEX.json'); put(index,dict(schema='revtrace-formal36-figure-index-v3',plans=plans,trials=trials))
environment=name('ENVIRONMENT.json')
import matplotlib,numpy
put(environment,dict(recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),python=sys.version,executable=sys.executable,platform=platform.platform(),matplotlib=matplotlib.__version__,numpy=numpy.__version__,new_model_calls=0))
command=[sys.executable,'-B',str(SOURCE/'render_evidence.py'),'--index',str(index),'--out',str(OUT)]
config=name('CONFIG.json');put(config,dict(experiment_id='SC_NATIVE_RESILIENCE_FORMAL36_FIGURE_TABLE_V4',code_commit=COMMIT,
 frozen_index=str(index.resolve()),frozen_index_sha256=sha(index),source_manifest_sha256=sha(F/'packages/FIGURE_TOOLS_SOURCE_v4.json'),
 environment_record=str(environment.resolve()),environment_record_sha256=sha(environment),command=command,
 input_manifest_location=str(name('INPUT_MANIFEST.json').resolve()),raw_result_location='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_native_resilience_20261030/',
 aggregate_summary_location=str((OUT/'FIGURE_TABLE_AUDIT.json').resolve()),gate_decision_location=str(name('VISUAL_QA_GATE.json').resolve()),
 complete_formal_cells=36,checked_durable_steps=3976,source_scope='Actual NN source4f and actual plot source2ab are distinct; CURRENT remains NN4f.',wrapper_sha256=sha(pathlib.Path(__file__))))
put(name('INPUT_MANIFEST.json'),[dict(path=str(x.resolve()),sha256=sha(x)) for x in sorted(set(inputs+[index,config,environment,F/'packages/FIGURE_TOOLS_SOURCE_v4.json']))])
put(name('RUN_RECORD.json'),dict(read(config),frozen_config=str(config.resolve()),frozen_config_sha256=sha(config),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wrapper_status='Declaration/materialization wrapper SHA bound separately; numerical table/plot logic is frozen 038.'))
result=subprocess.run(command,cwd=R,capture_output=True,text=True,encoding='utf8',errors='replace')
name('STDOUT.log').write_text(result.stdout,encoding='utf8');name('STDERR.log').write_text(result.stderr,encoding='utf8')
put(name('POST_EXPLICIT_ANALYSIS_SOURCE_PREFLIGHT.json'),p.check(SOURCE,F/'packages/FIGURE_TOOLS_SOURCE_v4.json'))
print(json.dumps(dict(exit_code=result.returncode,out=str(OUT),stdout=result.stdout,stderr=result.stderr),ensure_ascii=False))
raise SystemExit(result.returncode)
