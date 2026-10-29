import copy,math,unittest
from analyze_confirmation import ARMS,RUNTIME,REFERENCE_RUNTIME,digest,normalize,quantile,recount,pair_rows,fidelity,mechanisms,direction,independent_sources,quality_recount

def state(F,commit=RUNTIME):
 return dict(audio_segments=[],tokens=[[[1]]],context=dict(text='',prefix_token_ids=[],token_ids=[]),last_attend_frame=0,
  detected_language='zh',initial_tokens=[[1]],initial_token_length=1,sot_index=0,decoder_type='beam',frontier=F,transcript='fixed',
  contract=dict(source_sha='fixed',stage_execution=dict(protocol='protected_original_asr_ready_only_v1',asr_dtype='float32',corrector_dtype='float32',source_commit=commit)))
def cell(arm,position=0):
 return dict(source_id='s',repeat=0,arm=arm,primary_gpu=0,position=position,settings={'same':True},energy=100.,quality={'fixed':True},
  metrics=dict(offered_audio_seconds=.5,credit=.5,credit_samples=8000,C50=.2,D99=.3,C99=.4,frontiers=[dict(F=8000,audio_seconds=.5,dual_met=True)]))

class AnalysisControls(unittest.TestCase):
 def test_linear_quantile_not_nearest_rank(self):self.assertAlmostEqual(quantile([0,10],.99),9.9)
 def test_missing_offered_infinity_not_dropped(self):self.assertTrue(math.isinf(quantile([1,math.inf],.99)))
 def test_EOS_partial_and_negative_deadline_retained(self):
  sources=[dict(source_id='s',frames=8001)];rows=[dict(source_id='s',observed=1.,visible_frontier=8000,certified_frontier=8000),dict(source_id='s',observed=3.,visible_frontier=8001,certified_frontier=8001)]
  m=recount(sources,rows,0);self.assertEqual(m['offered_frontiers'],2);self.assertAlmostEqual(m['offered_audio_seconds'],8001/16000)
  self.assertEqual(m['credit'],.5);self.assertEqual(m['D2_misses'],1);self.assertTrue(m['frontiers'][-1]['EOS']);self.assertFalse(m['whole_run_D2_C8_pass'])
 def test_no_observation_is_missing_not_success_conditioning(self):
  rows=[dict(source_id='s',observed=1.,visible_frontier=8000,certified_frontier=8000)]
  m=recount([dict(source_id='s',frames=16000)],rows,0);self.assertEqual(m['missing_D'],1);self.assertIsNone(m['D99']);self.assertEqual(m['offered_frontiers'],2)
 def test_complete_same_runtime_tag_is_retained_not_projected(self):
  self.assertEqual(normalize(state(8000),RUNTIME),normalize(state(8000,REFERENCE_RUNTIME),REFERENCE_RUNTIME))
  self.assertEqual(normalize(state(8000),RUNTIME),state(8000))
  different=state(8000);different['contract']['stage_execution']['source_commit']='99e83a466fee7f1d16830b640cc99e0040d2f147'
  with self.assertRaises(ValueError):normalize(different,RUNTIME)
  changed=state(8000);changed['context']['text']='different';self.assertNotEqual(normalize(changed,RUNTIME),normalize(state(8000),RUNTIME))
 def test_unallowed_state_and_precision_tags_rejected(self):
  for mode in ('extra','dtype'):
   s=state(8000)
   if mode=='extra':s['unknown']='cannot ignore'
   else:s['contract']['stage_execution']['asr_dtype']='float16'
   with self.subTest(mode=mode),self.assertRaises(ValueError):normalize(s,RUNTIME)
 def test_paired_negative_differences_are_kept(self):
  b=cell(ARMS[0]);c=cell(ARMS[1],1);c['metrics']['credit']=0;c['metrics']['credit_samples']=0;c['metrics']['C50']=1;c['energy']=200
  r=pair_rows([b,c])[0];self.assertEqual(r['credit_difference'],-.5);self.assertGreater(r['C50_difference'],0);self.assertLess(r['energy_reduction_fraction'],0)
 def test_pair_denominator_role_and_settings_must_match(self):
  for mode in ('denominator','role','settings'):
   b=cell(ARMS[0]);c=cell(ARMS[1],1)
   if mode=='denominator':c['metrics']['offered_audio_seconds']=1
   elif mode=='role':c['primary_gpu']=1
   else:c['settings']['same']=False
   with self.subTest(mode=mode),self.assertRaises(ValueError):pair_rows([b,c])
 def test_worker_owned_is_not_sufficient_for_actual_model_overlap(self):
  p0=state(0);p1=state(8000);p2=state(16000)
  jobs=[dict(job_id='parent',gpu=0,start=p0,end=p1,record=dict(start=0,end=8000,model_start=1.,model_end=2.,worker_job_begin_perf=.9,worker_job_end_perf=2.05,native_model_evaluated=True)),
   dict(job_id='child',gpu=1,start=p1,end=p2,record=dict(start=8000,end=16000,model_start=2.2,model_end=3.,worker_job_begin_perf=1.4,worker_job_end_perf=3.1,native_model_evaluated=True))]
  events=[dict(kind='canonical_install',job_id='parent',observed=2.1),dict(kind='canonical_install',job_id='child',observed=3.2),dict(kind='asr_early',job_id='child',projection=dict(end=p2))]
  hist={'s':[dict(F=8000,state=p1,state_sha256=digest(p1)),dict(F=16000,state=p2,state_sha256=digest(p2))]}
  ledger=dict(promotions=[dict(job_id='child',birth_canonical_sha='old')]);dispatch=[dict(job_id='child',birth_canonical_sha='old')]
  m=mechanisms(jobs,events,ledger,dispatch,hist);self.assertEqual(m['physical_worker_active'],1);self.assertEqual(m['actual_model_path_active'],0);self.assertEqual(m['actual_model_overlaps_parent'],0)
 def fixture(self):
  actual=state(8000);old=state(8000,REFERENCE_RUNTIME);start=state(0);selected={'prompt':'full','candidates':['x','y']}
  jobs=[dict(job_id='j',start=start,end=actual,record=dict(start=0,end=8000,start_state=digest(start),end_state=digest(actual),token_ids=[9],selected_correction=selected))]
  return dict(sources=[dict(source_id='s')],histories={'s':[dict(F=8000,state=actual,state_sha256=digest(actual),token_ids=[9])]},wal=[dict(source_id='s',state=actual,selected=selected)],jobs=jobs,
   events=[dict(kind='canonical_install',source_id='s',job_id='j')],reference=[dict(source_id='s',end=8000,original_full_start_cut=state(0),original_full_cut=old,original_full_result=dict(token_ids=[9],selected_correction=selected))])
 def test_full_original_fidelity_passes(self):self.assertEqual(fidelity(**self.fixture()),1)
 def test_C_or_complete_start_change_rejected_even_same_final(self):
  for mode in ('C','start'):
   f=self.fixture()
   if mode=='C':f['jobs'][0]['record']['selected_correction']={'prompt':'different'}
   else:f['jobs'][0]['start']['context']['text']='different';f['jobs'][0]['record']['start_state']=digest(f['jobs'][0]['start'])
   with self.subTest(mode=mode),self.assertRaises(ValueError):fidelity(**f)
 def test_preregistered_direction_uses_four_speakers_not_eight_repeats(self):
  pairs=[dict(source_id=sid,credit_difference_samples=v) for sid,v in [('a',1),('a',-2),('b',1),('b',1),('c',1),('c',1),('d',1),('d',1)]]
  r=direction(pairs,['a','b','c','d']);self.assertTrue(r['directional_confirmation']);self.assertEqual(r['positive_acoustic_sources'],3)
  pairs[5]['credit_difference_samples']=-2
  self.assertFalse(direction(pairs,['a','b','c','d'])['directional_confirmation'])
 def test_two_positive_speakers_cannot_become_four_by_repeats(self):
  pairs=[dict(source_id=sid,credit_difference_samples=v) for sid,v in [('a',8000),('a',8000),('b',8000),('b',8000),('c',-1),('c',-1),('d',-1),('d',-1)]]
  r=direction(pairs,['a','b','c','d']);self.assertGreater(r['total_paired_credit_difference_samples'],0);self.assertFalse(r['directional_confirmation'])
 def test_official_reference_CER_is_independently_recounted(self):
  s=dict(source_id='s',reference='A B C');hist={'s':[dict(state=dict(transcript='A X C'))]}
  r=quality_recount(s,hist,[dict(source_id='s',text='A X C',reference_characters=3,character_edits=1)]);self.assertAlmostEqual(r['CER'],1/3)
  with self.assertRaises(ValueError):quality_recount(s,hist,[dict(source_id='s',text='A X C',reference_characters=3,character_edits=0)])
 def test_metadata_method_order_and_speaker_units_are_locked(self):
  sources=[dict(source_id=str(i),speaker_id='S'+str(i),technical_fallback_index=0) for i in range(4)]
  r=dict(sources=sources,method_source_commit=RUNTIME,metadata_only_before_neural=True)
  s=dict(selected=[dict(initial_source_id=x['source_id'],speaker_id=x['speaker_id']) for x in sources],excluded_speakers=['old'],selection_created_utc='2026-10-29T02:00Z',metadata_only_before_neural=True)
  a=dict(source_ids=[x['source_id'] for x in sources],speaker_ids=[x['speaker_id'] for x in sources],method_source_commit=RUNTIME);m=dict(method_source_commit=RUNTIME,created_utc='2026-10-29T01:00Z')
  self.assertEqual(independent_sources(r,s,a,m)['acoustic_units'],4)
  for mode in ('order','speaker','time','metadata'):
   rr,ss,aa,mm=copy.deepcopy((r,s,a,m))
   if mode=='order':rr['sources'].reverse()
   if mode=='speaker':rr['sources'][0]['speaker_id']='old'
   if mode=='time':mm['created_utc']='2026-10-29T03:00Z'
   if mode=='metadata':ss['metadata_only_before_neural']=False
   with self.subTest(mode=mode),self.assertRaises(ValueError):independent_sources(rr,ss,aa,mm)

if __name__=='__main__':unittest.main()
