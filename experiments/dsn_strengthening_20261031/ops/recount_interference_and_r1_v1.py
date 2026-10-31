"""After NN stops, independently recount all original selected transitions."""
import hashlib,json,pathlib,shlex,sys
E=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_20261031';O=B+'/results/revtrace/dsn_strengthening_20261031';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
script=r'''import pathlib,sys,subprocess,json,os,hashlib,platform,traceback
P=pathlib.Path(__PROJECT__);O=pathlib.Path(__OUTPUT__);S=P/'interference_source_v1';M=P/'INTERFERENCE_SOURCE_v1.json';sys.path.insert(0,str(S));from common import read,put,sha,verify_checkout,lines,need,canonical
identity=verify_checkout(S,M);need(not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=5).strip(),'raw audit requires idle GPU boundary');plan=read(P/'interference_inputs_v1/INTERFERENCE_OPPORTUNITY4_v1_FROZEN.json');root=pathlib.Path(plan['raw_result_location']);gate=read(root/'GATE.json');summary=read(root/'SUMMARY.json');need(gate['status'] in ('GO_REAL_SHARED_RESOURCE_ADMISSION_OPPORTUNITY','NO_GO_FIXED_TWO_CLIENT_ADMISSION_OPPORTUNITY'),'probe not scientifically settled');need(summary['attempted_cells']==summary['completed_cells']==4,'expected all fixed4 actual trials')
out=O/'interference_independent_recount_v1';out.mkdir();config=dict(experiment_id='SC_INTERFERENCE_AND_R1_INDEPENDENT_RAW_RECOUNT_V1',source_commit=identity['source_commit'],source_manifest_sha256=sha(M),probe_plan=str(P/'interference_inputs_v1/INTERFERENCE_OPPORTUNITY4_v1_FROZEN.json'),probe_plan_sha256=sha(P/'interference_inputs_v1/INTERFERENCE_OPPORTUNITY4_v1_FROZEN.json'),new_neural_calls=0,original_raw_roots=[str(O/n) for n in ('paired32_v2','resident4_v2','buffer4_v1','interference_opportunity4_v1')]);put(out/'CONFIG.json',config);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),source=identity,CUDA_VISIBLE_DEVICES='',trained_model_calls=0));put(out/'RUN_RECORD.json',dict(experiment_id=config['experiment_id'],code_commit=identity['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
def inventory(paths):
 result={}
 for r in paths:
  r=pathlib.Path(r);result[str(r)]=[dict(path=p.relative_to(r).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(r.rglob('*')) if p.is_file()]
 return result
before=inventory(config['original_raw_roots']);put(out/'ALL_RAW_BEFORE.json',before)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='');probe=[]
try:
 for cell in plan['cells']:
  raw=pathlib.Path(cell['out']);target=out/(cell['cell_id']+'_INDEPENDENT.json');command=[sys.executable,'-B',str(S/'audit_interference.py'),'--out',str(raw),'--audit-output',str(target)];r=subprocess.run(command,capture_output=True,env=env,timeout=120);(out/(cell['cell_id']+'.stdout.log')).write_bytes(r.stdout);(out/(cell['cell_id']+'.stderr.log')).write_bytes(r.stderr);need(r.returncode==0,'independent raw probe audit failed');a=read(target);need(canonical(a['summary'])==canonical(read(raw/'SUMMARY.json')),'independent raw recount differs from original result');probe.append(dict(cell_id=cell['cell_id'],status=a['status'],summary=a['summary']))
 sys.path.insert(0,plan['dependencies']['final']['source_root']);from audit_results import selected_trace;from endpoints import recount
 prior=[]
 for filename in ('PAIRED32_v2_FROZEN.json','RESIDENT4_v2_FROZEN.json','BUFFER4_v1_FROZEN.json'):
  q=P/filename;old=read(q);references=read(old['reference_details']);cells=[]
  for cell in old['cells']:
   raw=pathlib.Path(cell['out']);cfg=read(raw/'CONFIG.json');a=selected_trace(raw,cfg,references,cfg['settings']['source_commit']);sources={s['source_id']:s for s in cfg['settings']['sources']};origins=read(raw/'REQUEST_ORIGINS.json') if (raw/'REQUEST_ORIGINS.json').exists() else {sid:read(raw/'ORIGIN.json')['origin_perf'] for sid in sources};metric=recount(lines(raw/'consumer.jsonl'),sources,origins);stored=read(raw/'SUMMARY.json')['primary']
   for key in ('offered_frontiers','offered_audio_seconds','primary_linear_all_offered_D99','primary_linear_all_offered_C99','dual_deadline_audio_credit_seconds','D2_misses_all_offered','C8_misses_all_offered'):need(metric[key]==stored[key],'R1 raw metric recomputation differs: '+key)
   cells.append(dict(cell_id=cell['cell_id'],reference=a,primary={k:v for k,v in metric.items() if k!='frontiers'}))
  prior.append(dict(plan=filename,cells=cells,checked_transitions=sum(c['reference']['checked_steps'] for c in cells)))
 after=inventory(config['original_raw_roots']);put(out/'ALL_RAW_AFTER.json',after);need(before==after,'raw bytes changed during independent read');verify_checkout(S,M)
 result=dict(status='PASS_INDEPENDENT_ALL1190_STATE_C_IDS_CLOCK_DISPATCH_RAW_RECOUNT',source_commit=identity['source_commit'],new_neural_calls=0,original_raw_bytes_unchanged=True,raw_files=sum(len(v) for v in before.values()),raw_bytes=sum(r['bytes'] for rows in before.values() for r in rows),R1_selected_transitions=sum(r['checked_transitions'] for r in prior),probe_selected_transitions=sum(r['summary']['integrity']['original_reference']['checked_steps'] for r in probe),probe_actual_dispatches=sum(r['summary']['dispatch_observation']['actual_dispatches_checked'] for r in probe),probe_cases=probe,R1_raw_recounts=prior,original_probe_opportunity_gate=gate,scope='Fresh CPU process full raw recount with frozen2198 checker; no added NN, no new policy, all original gates untouched. Selected original transitions are not measured kernel-call counts.')
 need(result['R1_selected_transitions']==918 and result['probe_selected_transitions']==272,'selected-transition count differs');put(out/'SUMMARY.json',result);put(out/'GATE.json',{k:v for k,v in result.items() if k not in ('probe_cases','R1_raw_recounts')});print(json.dumps({k:v for k,v in result.items() if k not in ('probe_cases','R1_raw_recounts')}))
except BaseException:
 if not (out/'ALL_RAW_AFTER.json').exists():put(out/'ALL_RAW_AFTER.json',inventory(config['original_raw_roots']))
 put(out/'GATE.json',dict(status='FAIL_INDEPENDENT_RAW_RECOUNT_PRESERVED',failure=traceback.format_exc(),new_neural_calls=0));raise
'''.replace('__PROJECT__',repr(P)).replace('__OUTPUT__',repr(O));compile(script,'independent_1190_raw_recount','exec')
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=480);i.write(script);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();rc=o.channel.recv_exit_status();(E/'INTERFERENCE_INDEPENDENT_RECOUNT_STDOUT_v1.json').write_bytes(b);(E/'INTERFERENCE_INDEPENDENT_RECOUNT_STDERR_v1.txt').write_bytes(err);print(b.decode());assert rc==0,err.decode()
finally:c.close()
