from pathlib import Path
import json,os,subprocess,sys,datetime
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_dsn_writing_closure_20261031'
PY=str(B/'envs/revtrace-streamcorrect-20261028/bin/python')
S=P/'content_source_v4'
sys.path.insert(0,str(S))
from evidence_io import read,sha,put,source_gate
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=10).strip(),'GPU queue not empty before CPU audit'
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
configs=[]
for mode in ('controls','complete20'):
 path=P/('CONTENT_'+mode.upper()+'_v4_FROZEN.json');cfg=read(path)
 identity=source_gate(S,P/'CONTENT_SOURCE_v4.json',cfg['analysis_source_manifest_sha256'],cfg['analysis_source_commit'])
 assert sha(cfg['environment_record'])==cfg['environment_record_sha256'] and sha(cfg['root_noarg_preflight'])==cfg['root_noarg_preflight_sha256']
 assert not Path(cfg['intended_output']).exists() and not Path(cfg['lease_path']).exists()
 record=dict(experiment_id=cfg['experiment_id'],code_commit=cfg['analysis_source_commit'],source_manifest=str(P/'CONTENT_SOURCE_v4.json'),source_manifest_sha256=sha(P/'CONTENT_SOURCE_v4.json'),frozen_config=str(path),frozen_config_sha256=sha(path),environment_record=cfg['environment_record'],environment_record_sha256=sha(cfg['environment_record']),root_noarg_preflight=cfg['root_noarg_preflight'],root_noarg_preflight_sha256=sha(cfg['root_noarg_preflight']),raw_result_location=cfg['intended_output'],raw_input_locations=[c['raw_root'] for c in cfg['cells']],raw_input_files=len(cfg['inputs']),raw_input_bytes=sum(x['bytes'] for x in cfg['inputs']),aggregate_summary_location=cfg['aggregate_summary_location'],gate_decision_location=cfg['gate_decision_location'],stdout_location=cfg['stdout_path'],stderr_location=cfg['stderr_path'],actual_NN_execution_commit='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',new_model_calls=0,frozen_before_any_CLI_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_gate=identity)
 put(P/('PRELAUNCH_'+mode.upper()+'_v4.json'),record);configs.append((mode,path,cfg))
results=[]
for mode,path,cfg in configs:
 with open(cfg['stdout_path'],'xb') as out,open(cfg['stderr_path'],'xb') as err:
  command=[PY,'-B',str(S/'run_content_recount.py'),'--config',str(path),'--manifest',str(P/'CONTENT_SOURCE_v4.json'),'--out',cfg['intended_output']]
  completed=subprocess.run(command,env=env,stdout=out,stderr=err)
 gate=Path(cfg['gate_decision_location'])
 entry=dict(mode=mode,returncode=completed.returncode,actual_CLI=command,gate=read(gate) if gate.exists() else None)
 results.append(entry)
 if completed.returncode:
  entry['stderr_tail']=Path(cfg['stderr_path']).read_text()[-9000:]
  break
 assert entry['gate']['gate'].startswith('PASS'),entry
result=dict(status='COMPLETE_FORMAL_CONTENT_CPU_CLI_SEQUENCE' if len(results)==2 and all(x['returncode']==0 for x in results) else 'FORMAL_CONTENT_CPU_FAILURE_PRESERVED',results=results,new_model_calls=0)
put(P/'FORMAL_CONTENT_CPU_EXECUTION_RECEIPT_v4.json',result)
print(json.dumps(result))
