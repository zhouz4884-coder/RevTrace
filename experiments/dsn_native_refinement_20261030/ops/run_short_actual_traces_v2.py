"""Run fixed all-six actual short-pilot traces after root source/noarg gate."""
import datetime,hashlib,json,pathlib,platform,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1]
S=F/'trace_source_v2';M=F/'packages/TRACE_SOURCE_v2.json'
N=F.parent/'dsn_native_resilience_20261030';BANK=N/'SHORT_PILOT_RESULTS_v1';collection=BANK/'COLLECTION_MANIFEST.json'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
 assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
gate=read(F/'ROOT_TRACE_PREFLIGHT_v2.json');assert gate['gate']=='SOURCE_IDENTITY_PASS' and gate['code_commit']=='c4dde9ea9c7abf80fae084bc2293e193262c71e6'
manifest=read(collection);assert manifest['controller_exited'] and manifest['GPU_released'] and manifest['completed_cells']==6
for row in manifest['files']:
 p=BANK/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
plan=read(N/'SHORT_PILOT_v1_FROZEN.json');assert read(BANK/'CONFIG.json')==plan and plan['source_commit']==manifest['source_commit']=='9492d3f9cb35e2b2849ec020817750a221248f0e'
assert len(plan['cells'])==6
C=F/'SHORT_ACTUAL_TRACE_CONFIGS_v2';C.mkdir(exist_ok=False);O=F/'SHORT_ACTUAL_TRACE_RESULTS_v2';O.mkdir(exist_ok=False)
env=F/'SHORT_TRACE_ENVIRONMENT_v2.json';put(env,dict(python=sys.version,executable=sys.executable,platform=platform.platform(),scope='actual recorded native traces, local bounded copies; no new NN',model_calls=0,neural_source_commit=plan['source_commit']))
results=[]
for cell in plan['cells']:
 cid=cell['cell_id'];case=BANK/'cells'/cid;cfg=C/(cid+'.json');dest=O/cid
 eid='TRACE_ACTUAL_SHORT_V2_'+cid
 subprocess.run([sys.executable,'-B',str(F/'ops/bind_actual_trace_v1.py'),'--case-root',str(case),'--runtime-source-commit',plan['source_commit'],'--output-config',str(cfg),'--experiment-id',eid,'--original-raw-root',cell['out'],'--collection-manifest',str(collection),'--checker-version','2'],check=True)
 put(C/(cid+'_PRELAUNCH.json'),dict(experiment_id=eid,code_commit=gate['code_commit'],frozen_config=str(cfg),frozen_config_sha256=sha(cfg),environment_record=str(env),environment_record_sha256=sha(env),raw_result_location=cell['out'],bounded_raw_input_copy=str(case),aggregate_summary_location=str(dest/'SUMMARY.json'),gate_decision_location=str(dest/'GATE.json'),source_manifest_sha256=sha(M),actual_neural_source_commit=plan['source_commit'],source_collection_sha256=sha(collection),new_model_calls=0))
 with (O/(cid+'.stdout.log')).open('x',encoding='utf8') as out,(O/(cid+'.stderr.log')).open('x',encoding='utf8') as err:
  p=subprocess.run([sys.executable,'-B',str(S/'run_trace.py'),'--config',str(cfg),'--manifest',str(M),'--out',str(dest)],stdout=out,stderr=err)
 result=dict(cell_id=cid,returncode=p.returncode,gate=read(dest/'GATE.json'),config_sha256=sha(cfg),gate_sha256=sha(dest/'GATE.json'))
 results.append(result);put(O/(cid+'_EXECUTION_RESULT.json'),result)
 # Preserve all supplied cases even if one schema/control fails.
summary=dict(status='PASS_ALL_SIX_ACTUAL_TRACE_REFINEMENT' if all(x['returncode']==0 for x in results) else 'FAIL_OR_SCHEMA_DIAGNOSIS_REQUIRED_PRESERVED',checker_source_commit=gate['code_commit'],actual_neural_source_commit=plan['source_commit'],cases=6,results=results,source_collection_sha256=sha(collection),new_model_calls=0,executed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
put(O/'SUMMARY.json',summary);put(O/'GATE.json',summary)
print(json.dumps(dict(status=summary['status'],results=[dict(cell_id=x['cell_id'],returncode=x['returncode'],gate_sha256=x['gate_sha256']) for x in results]),indent=2))

