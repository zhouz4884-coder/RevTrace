import copy,json,pathlib,tempfile,unittest
from feedback_contract import FeedbackCut
from resilience_storage import FactStore
from resilience_metrics import analyze_trial,static_reference_state,MetricsIntegrityError,BDFA,power_metrics,recovery_clocks

ACTUAL='f'*40
def dump(path,value):path.write_text(json.dumps(value),encoding='utf8')
def jl(path,rows):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf8')
def cut(F=0,text=''):
 return FeedbackCut(dict(audio_segments=[],tokens=[[F]],context=dict(text='',prefix_token_ids=[1],token_ids=[1]),last_attend_frame=F,detected_language='zh',initial_tokens=[[1]],initial_token_length=1,sot_index=0,decoder_type='beam',contract=dict(source_sha='source',stage_execution=dict(source_commit=ACTUAL,asr_dtype='float32')),frontier=F,transcript=text))

def fixture(root,steps=2):
 root=pathlib.Path(root);source=dict(source_id='s',speaker_id='p',frames=8000*steps,audio_sha256='source',reference='a');cfg=dict(experiment_id='toy',cell_id='toy',source_commit=ACTUAL,arm='fullcall',stage='cpu-control',cohort='synthetic',repeat=0,settings=dict(source_commit=ACTUAL,sources=[source]));dump(root/'CONFIG.json',cfg);dump(root/'ORIGIN.json',dict(origin_perf=100.,original_D=2.,original_C=8.));dump(root/'SERVICE_END.json',dict(service_end_perf=100+steps*.5+.5))
 store=FactStore(root/'facts.wal',{'s':cut().state},{'toy':True});rows=[];facts=[];reference=[];parent=cut()
 for i in range(1,steps+1):
  F=8000*i;end=cut(F,'a');record=dict(start=parent.frontier,end=F,start_state=parent.sha256,end_state=end.sha256,role='authority',candidate_handoff=False,token_ids=[i],selected_correction={'text':'a'},native_model_evaluated=True,model_start=100+i*.5-.1,model_end=100+i*.5+.1);job=dict(job_id=f'e0-j{i}',source_id='s',start=parent.state,end=F,dispatch_epoch=0,worker='full0',worker_incarnation=0);body=dict(kind='original_full_canonical_transition',owner_epoch=0,source_id='s',session_epoch=0,parent_state=parent.state,parent_state_sha256=parent.sha256,next_state=end.state,next_state_sha256=end.sha256,record=record,job=job);receipt=store.commit(body)
  rows.append(dict(kind='canonical',source_id='s',observed=100+i*.5+.2,owner_epoch=0,certified_frontier=F,visible_frontier=F,text='a',canonical_sha=end.sha256,private_job=None,journal_sequence=receipt['sequence'],transition_id=receipt['transition_id'],recovery_replay=False));facts.append(dict(sequence=receipt['sequence'],receipt=receipt,body=dict(body,transition_id=receipt['transition_id']),processed_frontier=F));reference.append(dict(source_id='s',end=F,original_full_start_cut=parent.state,original_full_cut=end.state,original_full_result=dict(token_ids=[i],selected_correction={'text':'a'})));parent=end
 store.close();jl(root/'consumer.jsonl',rows);jl(root/'power.jsonl',[dict(time=99.,watts={'0':100.,'1':200.}),dict(time=110.,watts={'0':100.,'1':200.})]);jl(root/'ingress.jsonl',[dict(source_id='s',accepted=8000*i,observed=100+i*.5,original_offer=100+i*.5) for i in range(1,steps+1)]);dump(root/'REFERENCE.json',reference);cfg.update(reference_details=str(root/'REFERENCE.json'),reference_kind='continuous_original');dump(root/'CONFIG.json',cfg);return cfg,rows,facts,{'s':source}

class MetricsControls(unittest.TestCase):
 def test_original_endpoints_complete_and_energy_interval(self):
  with tempfile.TemporaryDirectory() as d:
   fixture(pathlib.Path(d));s=analyze_trial(d);self.assertEqual(s['gate'],'PASS_COMPLETE_TRIAL_TASK_AND_ORIGINAL_ENDPOINT_RECOUNT');self.assertEqual(s['primary']['dual_deadline_audio_credit_seconds'],1.);self.assertEqual(s['primary']['offered_frontiers'],2);self.assertAlmostEqual(s['energy']['service']['total_joules'],450.);self.assertEqual(s['quality'][0]['character_edits'],0);self.assertEqual(s['integrity']['original_reference']['checked_steps'],2)
 def test_static_source_map_only_not_other_fields(self):
  old=cut(8000,'a').state;old['contract']['stage_execution']['source_commit']=BDFA;new=cut(8000,'a').state;self.assertEqual(static_reference_state(old,'short_bdfa_static_source_mapping',ACTUAL),static_reference_state(new,'short_bdfa_static_source_mapping',ACTUAL));new['last_attend_frame']+=1;self.assertNotEqual(static_reference_state(old,'short_bdfa_static_source_mapping',ACTUAL),static_reference_state(new,'short_bdfa_static_source_mapping',ACTUAL));self.assertNotEqual(static_reference_state(old,'continuous_original',ACTUAL),static_reference_state(cut(8000,'a').state,'continuous_original',ACTUAL))
 def test_unexpected_mapping_marker_fails(self):
  state=cut().state;state['contract']['stage_execution']['source_commit']='e'*40
  with self.assertRaises(MetricsIntegrityError):static_reference_state(state,'short_bdfa_static_source_mapping',ACTUAL)
 def test_posterior_text_support_does_not_replace_primary(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);_,rows,_,_=fixture(p);rows.insert(1,dict(rows[0],kind='private',visible_frontier=16000,text='b',observed=101.1));jl(p/'consumer.jsonl',rows);s=analyze_trial(p);self.assertEqual(s['primary']['dual_deadline_audio_credit_seconds'],1.);self.assertEqual(s['posterior_whole_text_support']['raw']['original_credit_supported_seconds'],.5);self.assertEqual(s['posterior_whole_text_support']['raw']['original_credit_mismatching_seconds'],.5)
 def test_wrong_consumer_durable_binding_fails(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);_,rows,_,_=fixture(p);rows[-1]['canonical_sha']='wrong';jl(p/'consumer.jsonl',rows);self.assertEqual(analyze_trial(p)['gate'],'FAIL_OFFLINE_TRIAL_RECOUNT_PRESERVED')
 def test_changed_original_C_reference_fails_task(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);fixture(p);ref=json.loads((p/'REFERENCE.json').read_text());ref[0]['original_full_result']['selected_correction']={'text':'changed'};dump(p/'REFERENCE.json',ref);s=analyze_trial(p);self.assertEqual(s['integrity']['original_reference']['mismatches'],1);self.assertEqual(s['gate'],'FAIL_OR_INCOMPLETE_TRIAL_TASK_PRESERVED')
 def test_input_clock_reset_is_not_hidden(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);fixture(p);jl(p/'ingress.jsonl',[dict(source_id='s',accepted=16000,observed=101.,original_offer=201.)]);s=analyze_trial(p);self.assertEqual(s['gate'],'FAIL_OFFLINE_TRIAL_RECOUNT_PRESERVED');self.assertIn('clock',s['reason'])
 def test_no_actual_consumer_is_not_fake_success(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);fixture(p);jl(p/'consumer.jsonl',[]);s=analyze_trial(p);self.assertEqual(s['gate'],'FAIL_OFFLINE_TRIAL_RECOUNT_PRESERVED')
 def test_power_needs_explicit_service_end(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);fixture(p);self.assertEqual(power_metrics(p,100.,None)['status'],'UNAVAILABLE')
 def test_history_retained_entries_separate_output_and_RSS(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);fixture(p);jl(p/'owner_e0/state_sizes.jsonl',[dict(history=dict(live_jobs=2,canonical_witnesses=5),current_cut_bytes=1000,current_text_bytes=100,immutable_audio_bytes=8000,owner_RSS_bytes=20000),dict(history=dict(live_jobs=1,canonical_witnesses=4),current_cut_bytes=2000,current_text_bytes=500,immutable_audio_bytes=8000,owner_RSS_bytes=25000)]);h=analyze_trial(p)['history'];self.assertEqual(h['coordination_entry_maxima']['live_jobs'],2);self.assertEqual(h['application_and_process_data']['current_text_bytes']['max'],500);self.assertIn('not establish constant',h['scope'])
 def test_replay_old_fact_not_first_new_inference(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);_,rows,facts,sources=fixture(p,steps=3);rows[1]['recovery_replay']=True;rows[1]['observed']=101.4;rows[2]['observed']=102.8;facts[2]['body']['record']['model_end']=102.7
   jl(p/'owner_e0/owner_events.jsonl',[dict(kind='durable_sync',owner_epoch=0,observed=100.65,receipt=dict(sequence=2)),dict(kind='durable_sync',owner_epoch=0,observed=101.1,receipt=dict(sequence=3)),dict(kind='owner_fault_ready',owner_epoch=0,observed=101.15,site='after_durable')]);jl(p/'supervisor.jsonl',[dict(kind='owner_death_confirmed',observed=101.2),dict(kind='owner_ready',owner_epoch=1,observed=102.5)]);r=recovery_clocks(p,rows,facts,sources,100.,103.)['events'][0];self.assertEqual(r['first_actual_old_fact_replay_perf'],101.4);self.assertEqual(r['first_new_model_completed_after_fault_and_certified_consume_perf'],102.8);self.assertLess(r['fault_to_old_fact_replay'],r['fault_to_replacement_ready'])
 def test_surviving_work_can_clear_debt_before_replacement_ready(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);_,rows,facts,sources=fixture(p,steps=3);jl(p/'owner_e0/owner_events.jsonl',[dict(kind='durable_sync',owner_epoch=0,observed=100.65,receipt=dict(sequence=2)),dict(kind='fault_triggered',owner_epoch=0,observed=101.05,site='worker_after_ASR'),dict(kind='replacement_neural_ready',owner_epoch=0,observed=102.5)]);r=recovery_clocks(p,rows,facts,sources,100.,103.)['events'][0];self.assertEqual(r['uncertified_debt_before_fault_samples']['s'],8000);self.assertEqual(r['debt_clear_actual_certified_consume_perf'],101.2);self.assertLess(r['fault_to_new_certified_result'],r['fault_to_replacement_ready'])
 def test_mirror_owner_event_not_extra_fault_and_owner_group_death_seen(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);_,rows,facts,sources=fixture(p,steps=3);jl(p/'supervisor.jsonl',[dict(kind='owner_event',observed=101.06,event=dict(kind='owner_fault_ready',site='after_durable',owner_epoch=0,job_id='j',observed=101.05)),dict(kind='fault_triggered',site='after_durable',owner_epoch=0,job_id='j',observed=101.07),dict(kind='owner_group_death_confirmed',observed=101.2)]);r=recovery_clocks(p,rows,facts,sources,100.,103.);self.assertEqual(r['observed_fault_records'],1);self.assertEqual(r['events'][0]['physical_death_confirmed_perf'],101.2)
 def test_unexpected_owner_code_error_cannot_be_hidden_by_eventual_completion(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);fixture(p);jl(p/'supervisor.jsonl',[dict(kind='writes_frozen_owner_error',observed=100.7,traceback='Traceback\nTypeError: integration defect')]);s=analyze_trial(p);self.assertEqual(s['integrity']['unexpected_owner_error_records'],1);self.assertEqual(s['gate'],'FAIL_OR_INCOMPLETE_TRIAL_TASK_PRESERVED')
if __name__=='__main__':unittest.main()
