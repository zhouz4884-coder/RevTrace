"""Frozen sequential fresh-process campaign, full-task audit and finite pilot gate."""
import argparse,copy,datetime,hashlib,json,math,os,pathlib,platform,subprocess,sys,time,traceback
R=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):pathlib.Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def lines(p):return [json.loads(x) for x in pathlib.Path(p).read_text(encoding='utf8').splitlines() if x.strip()]
def task(state):
 s=copy.deepcopy(state);tag=s['contract'].pop('stage_execution')
 assert tag['protocol']=='protected_original_asr_ready_only_v1' and tag['asr_dtype']=='float32' and tag['corrector_dtype']=='float32'
 return s
def medians(config,out):
 from original_primary_quantiles import quantile,finite
 origin=read(out/'ORIGIN.json')['origin_perf'];events=lines(out/'consumer.jsonl');D=[];C=[]
 for source in config['settings']['sources']:
  observed=[r for r in events if r['source_id']==source['source_id']];n=source['frames']
  for F in list(range(8000,n,8000))+[n]:
   ready=origin+F/16000
   D.append(next((r['observed']-ready for r in observed if r['observed']>=ready and r['visible_frontier']>=F),math.inf))
   C.append(next((r['observed']-ready for r in observed if r['observed']>=ready and r['certified_frontier']>=F),math.inf))
 return dict(all_offered_D50=finite(quantile(D,.5)),all_offered_C50=finite(quantile(C,.5)))
def audit_cell(config,out,reference):
 histories=read(out/'CANONICAL_HISTORIES.json');wal=lines(out/'canonical_wal.jsonl');checked=0
 for source in config['settings']['sources']:
  sid=source['source_id'];expected=[r for r in reference if r['source_id']==sid];actual=histories[sid]
  assert len(actual)==len(expected),'full Canonical history length changed'
  commits=[r for r in wal if r['source_id']==sid];assert len(commits)==len(expected)
  for a,w,e in zip(actual,commits,expected):
   assert a['F']==e['end'] and task(a['state'])==task(e['original_full_cut']),'complete task state differs from frozen original full reference'
   assert task(w['state'])==task(e['original_full_cut']),'WAL/actual history mismatch'
   assert a['token_ids']==e['original_full_result']['token_ids'],'original returned IDs changed'
   assert w['selected']==e['original_full_result']['selected_correction'],'original neural C selection changed'
   checked+=1
 return dict(status='PASS_COMPLETE_CANONICAL_STATE_SELECTED_C_AND_IDS',checked_steps=checked,projection='remove only explicit stage_execution contract tag from both reference and service state; all old task fields remain exact')
def opportunity(candidate,control,thresholds):
 cp=candidate['primary'];bp=control['primary'];credit=cp['dual_deadline_audio_credit_seconds']-bp['dual_deadline_audio_credit_seconds']
 same_credit=abs(credit)<1e-8
 same_pass=cp['complete_coverage_and_original_quantile_pass']==bp['complete_coverage_and_original_quantile_pass']
 cm=candidate['latency_medians']['all_offered_C50'];bm=control['latency_medians']['all_offered_C50']
 latency=same_credit and same_pass and cm is not None and bm is not None and bm-cm>=thresholds['certified_median_absolute_seconds'] and bm>0 and (bm-cm)/bm>=thresholds['certified_median_relative_fraction']
 cj=candidate['service_board_joules'];bj=control['service_board_joules']
 energy=same_credit and same_pass and bj>0 and (bj-cj)/bj>=thresholds['service_energy_relative_fraction']
 return dict(candidate=candidate['arm'],control=control['arm'],credit_difference_seconds=credit,certified_median_difference_seconds=None if cm is None or bm is None else bm-cm,energy_reduction_fraction=(bj-cj)/bj if bj else None,credit_opportunity=credit>=thresholds['credit_absolute_audio_seconds']-1e-9,latency_opportunity=latency,energy_opportunity=energy,engineering_GO=credit>=thresholds['credit_absolute_audio_seconds']-1e-9 or latency or energy,scope='predeclared development opportunity screen; not a significance test or independent confirmation')
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
 from native_service import verify_source
 identity=verify_source(a.manifest);plan=read(a.plan);assert plan['source_commit']==identity['source_commit'];assert sha(a.manifest)==plan['source_manifest_sha256'];assert pathlib.Path(plan['source_root']).resolve()==R
 assert sha(plan['environment_record'])==plan['environment_sha256'];assert sha(plan['reference_details'])==plan['reference_details_sha256'];assert sha(plan['old_task_fidelity_gate'])==plan['old_task_fidelity_gate_sha256']
 assert read(plan['old_task_fidelity_gate'])['status'].startswith('PASS')
 refs=read(plan['reference_details']);configs=[]
 for cell in plan['cells']:
  assert sha(cell['config'])==cell['config_sha256'];cfg=read(cell['config']);assert cfg['cell_id']==cell['cell_id'] and cfg['arm']==cell['arm'];assert cfg['settings']['source_commit']==plan['source_commit'];configs.append(cfg)
 assert len(configs)==plan['expected_cells'];assert not a.out.exists();a.out.mkdir()
 put(a.out/'CONFIG.json',plan);put(a.out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),source=identity,prior_verified_environment=plan['environment_record'],prior_verified_environment_sha256=plan['environment_sha256'],actual_workers='per-cell READY.json; full source/config, all actual model packages and dtypes recorded'))
 put(a.out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id'],code_commit=identity['source_commit'],frozen_config=str(a.out/'CONFIG.json'),frozen_config_sha256=sha(a.out/'CONFIG.json'),environment_record=str(a.out/'ENVIRONMENT.json'),environment_record_sha256=sha(a.out/'ENVIRONMENT.json'),raw_result_location=plan['raw_result_location'],aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json')))
 results=[]
 try:
  for cell,cfg in zip(plan['cells'],configs):
   assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'GPU occupied before fresh-process cell'
   out=pathlib.Path(cell['out']);assert not out.exists();log=pathlib.Path(cell['log']);assert not log.exists()
   put(a.out/'PROGRESS.json',dict(completed=len(results),planned=len(configs),current=cell['cell_id'],stage='loading_then_actual_service',updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
   command=[sys.executable,'-B',str(R/'stage_service.py'),'--config',cell['config'],'--manifest',str(a.manifest),'--out',str(out)]
   with log.open('x',encoding='utf8') as stream:
    subprocess.run(command,check=True,stdout=stream,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
   assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'cell returned before actual model workers released'
   summary=read(out/'SUMMARY.json');assert summary['status']=='PASS_ACTUAL_NATIVE_SERVICE_EXECUTION';audit=audit_cell(cfg,out,refs);put(out/'COMPLETE_TASK_FIDELITY.json',audit)
   result=dict(cell_id=cell['cell_id'],arm=cell['arm'],repeat=cfg['repeat'],sources=[s['source_id'] for s in cfg['settings']['sources']],primary=summary['primary'],latency_medians=medians(cfg,out),service_board_joules=summary['energy']['service']['total_joules'],quality=summary['quality'],actual_ready_hits=summary['actual_ready_hits'],authority_dispatches=summary['authority_dispatches'],producer_dispatches=summary['producer_dispatches'],matching_inflight_fallbacks=summary['matching_inflight_fallbacks'],fullspec_inflight_promotions=summary['fullspec_inflight_promotions'],fullspec_known_invalid_C_skips=summary['fullspec_known_invalid_C_skips'],fullspec_discarded_full_results=summary['fullspec_discarded_full_results'],wire_total_bytes=summary['wire_total_bytes'],wall_seconds=summary['wall_seconds'],fidelity=audit,summary_sha256=sha(out/'SUMMARY.json'),config_sha256=sha(cell['config']))
   results.append(result);put(a.out/'PARTIAL_RESULTS.json',results);put(a.out/'PROGRESS.json',dict(completed=len(results),planned=len(configs),current=None,updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
  decisions=[]
  if plan.get('pilot_thresholds'):
   by={r['arm']:r for r in results};assert len(by)==len(results)==3
   for candidate,control in [('two_full_spec_early','two_full_early'),('ready_handoff','two_full_early'),('ready_handoff','two_full_spec_early')]:decisions.append(opportunity(by[candidate],by[control],plan['pilot_thresholds']))
  result=dict(status='PASS_ALL_FROZEN_NATIVE_SERVICE_CELLS_AND_COMPLETE_TASK_FIDELITY',experiment_id=plan['experiment_id'],source_commit=identity['source_commit'],completed_cells=len(results),planned_cells=len(configs),all_full_task_histories_selected_C_and_IDs_equal=True,old_task_fidelity_projection='only stage_execution contract tag',cells=results,development_opportunity_screen=decisions,screen_is_not_statistical_confirmation=True,scope=plan['scope'])
  put(a.out/'SUMMARY.json',result);put(a.out/'GATE.json',dict(status=result['status'],completed_cells=len(results),planned_cells=len(configs),all_full_task_fidelity_pass=True,summary_sha256=sha(a.out/'SUMMARY.json')));print(json.dumps({k:v for k,v in result.items() if k!='cells'},indent=2))
 except BaseException:
  (a.out/'failure.txt').write_text(traceback.format_exc(),encoding='utf8');put(a.out/'GATE.json',dict(status='FAIL_NATIVE_SERVICE_CAMPAIGN_PRESERVED',completed_cells=len(results),planned_cells=len(configs),no_automatic_retry=True));raise
if __name__=='__main__':main()
