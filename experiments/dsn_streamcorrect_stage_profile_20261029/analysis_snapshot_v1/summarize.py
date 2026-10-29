"""Bounded offline stage evidence; never estimates deployed serving gains."""
import pathlib,json,hashlib,statistics,argparse,sys,subprocess,platform,collections
R=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2))
def stats(xs):return dict(n=len(xs),mean=statistics.mean(xs) if xs else None,median=statistics.median(xs) if xs else None,minimum=min(xs) if xs else None,maximum=max(xs) if xs else None)
def main():
 p=argparse.ArgumentParser();p.add_argument('--campaign',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--prior-ready',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
 commit=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip();assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain','--untracked-files=all'],text=True)
 plan=read(a.campaign/'FROZEN_PLAN.json');summary=read(a.campaign/'SUMMARY.json');assert summary['status']=='PASS_BOUNDED_ORIGINAL_STAGE_PROFILE_AND_PACKET_CONTROLS'
 put(a.out/'CONFIG.json',dict(experiment_id='SC_STAGE_PROFILE_OFFLINE_EVIDENCE_V1',campaign=str(a.campaign),campaign_summary_sha256=sha(a.campaign/'SUMMARY.json'),frozen_plan_sha256=sha(a.campaign/'FROZEN_PLAN.json'),prior_ready_summary=str(a.prior_ready),prior_ready_summary_sha256=sha(a.prior_ready),no_gpu=True,no_new_inference=True));put(a.out/'ENVIRONMENT.json',dict(python=sys.version,platform=platform.platform(),dependencies='stdlib; CPU torch only to load captured ordered candidate token tensor'))
 put(a.out/'RUN_RECORD.json',dict(experiment_id='SC_STAGE_PROFILE_OFFLINE_EVIDENCE_V1',code_commit=commit,frozen_config=str(a.out/'CONFIG.json'),frozen_config_sha256=sha(a.out/'CONFIG.json'),environment_record=str(a.out/'ENVIRONMENT.json'),environment_record_sha256=sha(a.out/'ENVIRONMENT.json'),raw_result_location=str(a.campaign),aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json')))
 import torch
 native=read(plan['native_plan']);prior=read(a.prior_ready);byinput=collections.defaultdict(list);inputs=[]
 for cell in native['cells']:
  relevant=[p for p in prior['pairs'] if p['cell_id']==cell['cell_id'] and p['both_native_model_evaluated']]
  if not relevant:continue
  jobs_path=pathlib.Path(cell['out'])/'native_jobs.jsonl';jobs={j['job_id']:j for j in map(json.loads,jobs_path.read_text().splitlines())};inputs.append(dict(path=str(jobs_path),sha256=sha(jobs_path)))
  for pair in relevant:
   j=jobs[pair['authority_job']];r=j['record'];byinput[(j['source_id'],r['start_state'],r['end'],r['is_last'])].append(pair)
 steps=[];warm=[];control=[]
 for run in plan['runs']:
  base=a.campaign/run['run_id'];rs=read(base/'SUMMARY.json');assert all(x['reference_equal'] for x in rs['results'])
  if run['capture']=='off':control.append(dict(run=run,model_seconds=rs['results'][0]['model_seconds'],stage_seconds=None));continue
  traces=[read(p) for p in sorted((base/'trace').glob('*.json'))]
  nn=[t for t in traces if t['calls'] and t['calls'][0]['packet']['original_corrector_result'] is not None];first=min(nn,key=lambda t:t['calls'][0]['corrector_call_index_in_process']) if nn else None
  for t in traces:
   iswarm=t['step']['step_id']=='warmup';record=t['native_record'];call=t['calls'][0] if t['calls'] else None;packet=call['packet'] if call else None;selected=record['selected_correction'];same=byinput.get((t['step']['source_id'],record['start_state'],record['end'],record['is_last']),[])
   blob=packet['corrector_input'].get('current_tokens') if packet else None;ordered=torch.load(blob['tensor_blob'],map_location='cpu',weights_only=True).tolist() if blob else None
   row=dict(run_id=run['run_id'],kind=run['kind'],source_id=t['step']['source_id'],start=record['start'],end=record['end'],full_start_sha=record['start_state'],full_end_sha=record['end_state'],warmup=iswarm,native_model_evaluated=record['native_model_evaluated'],C_API_called=bool(call),C_nonNone_result=packet is not None and packet['original_corrector_result'] is not None,first_nonNone_C_in_process=t is first,stage_seconds=t['stage_seconds'],post_model_materialize_seconds=t['post_model_materialize_seconds'],capture_mode=t['capture_mode'],ordered_full_beam_tokens=ordered,predecode_prefix_length=packet['corrector_input'].get('token_len_before_decoding') if packet else None,raw_feedback_changed=record['selection_changed'],selected_text=record['selected_full_text'],top1_text=record['top1_full_text'],selected_nonempty=bool(record['text'].strip()),prior_same_full_input_pairs=len(same),prior_end_equal_pairs=sum(x['complete_end_state_equal'] for x in same),prior_end_different_pairs=sum(not x['complete_end_state_equal'] for x in same),prior_controller_ready_pairs=sum(x['controller_received_before_authority_dispatch'] for x in same),open_packet=True if packet else False,KV_payload_handoff_proven=False)
   if iswarm:warm.append(row)
   elif run['kind']=='full':steps.append(row)
   else:control.append(dict(run=run,**row))
 fullnn=[x for x in steps if x['C_nonNone_result']];timing={k:stats([r['stage_seconds'][k] for r in fullnn]) for k in ['A','C','H','capture','instrumented_model_total']};timing['post_model_materialize']=stats([r['post_model_materialize_seconds'] for r in fullnn])
 groups=[]
 for sid in [s['source_id'] for s in native['sources']]:
  rows=[r for r in fullnn if r['source_id']==sid];groups.append(dict(source_id=sid,steps=len(rows),timing={k:stats([r['stage_seconds'][k] for r in rows]) for k in ['A','C','H','capture']},raw_changed=sum(r['raw_feedback_changed'] is True for r in rows),raw_unchanged=sum(r['raw_feedback_changed'] is False for r in rows)))
 result=dict(status='PASS_BOUNDED_STAGE_COMPONENT_EVIDENCE',runtime_source_commit=plan['source_commit'],analysis_source_commit=commit,full_sources=4,full_profile_steps=len(steps),full_profile_neural_C_calls=len(fullnn),total_captured_warmup_calls=len(warm),full_ordered_candidate_packet_saved=sum(r['ordered_full_beam_tokens'] is not None for r in steps),timing_seconds=timing,per_source=groups,warmup_first_C_and_controls=warm,short_controls=control,all_reference_histories_equal=True,packet_equivalence_controls_pass=True,actual_precision='ASR and corrector FP32; no autocast/TF32',raw_paths_remain_on_B=True,source_inputs=inputs,full_steps=steps,scope='Offline component evidence only; no serving/handoff/IPC claim. First nonNone C is identified separately. Original open KV/attention payload is not a resumable handoff state. Same-input old pairs include selected-feedback changes; not filtered by final end equality.')
 put(a.out/'SUMMARY.json',result);put(a.out/'GATE.json',dict(status=result['status'],full_sources=4,whole_history_equivalence=True,packet_controls=True));print(json.dumps({k:v for k,v in result.items() if k not in ['full_steps','source_inputs','warmup_first_C_and_controls','short_controls']},indent=2))
if __name__=='__main__':main()
