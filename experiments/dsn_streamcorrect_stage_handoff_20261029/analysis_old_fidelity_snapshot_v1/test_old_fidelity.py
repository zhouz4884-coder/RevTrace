"""Synthetic CPU negatives for the exact projection/comparison, no neural call."""
import copy,unittest
from old_fidelity import compare_bank,digest,projected_cut

STAGE=dict(protocol='protected_original_asr_ready_only_v1',asr_dtype='float32',corrector_dtype='float32',source_commit='a'*40)
def state(sid,F,text=''):
 return dict(audio_segments=[dict(samples=F,dtype='float32',sha256='audio-'+str(F))] if F else [],
  tokens=[[[1,2,3,4]]*4,[[10]]*4] if F else [[[1,2,3,4]]*4],
  context=dict(text='context',prefix_token_ids=[9],token_ids=[9,8]),last_attend_frame=F//100,
  detected_language='zh',initial_tokens=[[1,2,3,4]],initial_token_length=4,sot_index=0,decoder_type='beam',
  contract=dict(source_sha='sha-'+sid,precision='float32',immutable='preserve'),frontier=F,transcript=text)
def tagged(s):
 s=copy.deepcopy(s);s['contract']['stage_execution']=copy.deepcopy(STAGE);return s
def fixture():
 sources=[dict(source_id=sid,frames=16000,audio_sha256='sha-'+sid) for sid in ('s0','s1')]
 h={};w=[];jobs=[];details=[];initials={};audit={}
 for s in sources:
  sid=s['source_id'];previous=state(sid,0);new_previous=tagged(previous);initials[sid]=new_previous;h[sid]=[];audit[sid]=[]
  for F in (8000,16000):
   end=state(sid,F,'old text '+str(F));new=tagged(end);ids=[10] if F==8000 else []
   selected=dict(prompt='full original prompt',previous_transcription='p',candidates=['x','y'],corrected_appended_text='x',corrected_appended_token_ids=ids) if F==8000 else None
   oldrecord=dict(role='authority',start=previous['frontier'],end=F,start_state=digest(previous),end_state=digest(end),token_ids=ids,selected_correction=selected,text='delta',native_model_evaluated=F==8000)
   h[sid].append(dict(F=F,state=end,state_sha256=digest(end),token_ids=ids));audit[sid].append(digest(end))
   w.append(dict(source_id=sid,state=end,state_sha256=digest(end),selected=selected))
   jobs.append(dict(role='authority-0',source_id=sid,start=previous,end=end,record=oldrecord))
   record=copy.deepcopy(oldrecord);record.update(start_state=digest(new_previous),end_state=digest(new),authority_ASR_executed=True)
   details.append(dict(source_id=sid,start=previous['frontier'],end=F,full_input_sha=digest(new_previous),original_full_result=record,original_full_cut=new))
   previous=end;new_previous=new
 return dict(histories=h,wals=w,jobs=jobs,details=details,initials=initials,sources=sources,stage=copy.deepcopy(STAGE),audit_histories=audit)

class OldTaskFidelityControls(unittest.TestCase):
 def test_only_declared_stage_tag_differs_and_raw_hashes_are_not_equal(self):
  rows=compare_bank(**fixture());self.assertEqual(len(rows),4)
  self.assertTrue(all(not r['old_raw_and_new_raw_hashes_equal'] for r in rows))
  self.assertTrue(all(r['original_old_cut_sha256']==r['new_projected_cut_sha256'] for r in rows))
 def test_same_bank_repeat_is_exact(self):
  bank=fixture();self.assertEqual(compare_bank(**bank),compare_bank(**copy.deepcopy(bank)))
 def test_unallowed_state_field_mutations_rejected_even_after_valid_rehash(self):
  mutations=[lambda c:c['context'].__setitem__('text','different'),lambda c:c['tokens'][0][0].__setitem__(0,99),
   lambda c:c['audio_segments'][0].__setitem__('sha256','wrong'),lambda c:c.__setitem__('last_attend_frame',999),
   lambda c:c.__setitem__('detected_language','en'),lambda c:c['initial_tokens'][0].__setitem__(0,99),
   lambda c:c.__setitem__('initial_token_length',3),lambda c:c.__setitem__('sot_index',1),
   lambda c:c.__setitem__('decoder_type','greedy'),lambda c:c.__setitem__('transcript','different'),
   lambda c:c['contract'].__setitem__('precision','float16'),lambda c:c['contract'].__setitem__('unknown_tag','ignore-me')]
  for mutate in mutations:
   with self.subTest(mutation=mutations.index(mutate)):
    bank=fixture();n=bank['details'][0];mutate(n['original_full_cut']);n['original_full_result']['end_state']=digest(n['original_full_cut'])
    with self.assertRaisesRegex(ValueError,'complete original end differs'):compare_bank(**bank)
 def test_source_binding_never_removed(self):
  bank=fixture();n=bank['details'][0];n['original_full_cut']['contract']['source_sha']='wrong';n['original_full_result']['end_state']=digest(n['original_full_cut'])
  with self.assertRaisesRegex(ValueError,'source bytes binding'):compare_bank(**bank)
 def test_stage_projection_requires_exact_full_expected_binding(self):
  for field,value in [('source_commit','b'*40),('asr_dtype','float16'),('corrector_dtype','bfloat16'),('protocol','different'),('unknown','extra')]:
   with self.subTest(field=field):
    c=tagged(state('s0',8000));c['contract']['stage_execution'][field]=value
    with self.assertRaisesRegex(ValueError,'unallowed stage_execution'):projected_cut(c,STAGE)
 def test_absent_stage_tag_rejected(self):
  with self.assertRaisesRegex(ValueError,'stage_execution absent'):projected_cut(state('s0',0),STAGE)
 def test_unknown_or_missing_cut_fields_rejected(self):
  for operation in ('extra','missing'):
   with self.subTest(operation=operation):
    c=tagged(state('s0',0))
    if operation=='extra':c['safe_looking_tag']='cannot ignore'
    else:c.pop('context')
    with self.assertRaisesRegex(ValueError,'state fields'):projected_cut(c,STAGE)
 def test_selected_C_compared_in_full_including_prompt_candidates_and_empty(self):
  for key,value in [('prompt','different prompt'),('previous_transcription','wrong prefix'),('candidates',['y','x']),('corrected_appended_text',''),('corrected_appended_token_ids',[])]:
   with self.subTest(field=key):
    bank=fixture();bank['details'][0]['original_full_result']['selected_correction'][key]=value
    with self.assertRaisesRegex(ValueError,'complete selected C differs'):compare_bank(**bank)
 def test_none_corrector_is_not_ignored(self):
  bank=fixture();bank['details'][1]['original_full_result']['selected_correction']={}
  with self.assertRaisesRegex(ValueError,'complete selected C differs'):compare_bank(**bank)
 def test_returned_IDs_not_inferred_from_text(self):
  bank=fixture();bank['details'][0]['original_full_result']['token_ids']=[777]
  with self.assertRaisesRegex(ValueError,'returned token IDs differ'):compare_bank(**bank)
 def test_text_not_inferred_from_IDs(self):
  bank=fixture();bank['details'][0]['original_full_result']['text']='different'
  with self.assertRaisesRegex(ValueError,'appended text differs'):compare_bank(**bank)
 def test_raw_record_hash_bindings_must_match_actual_unprojected_states(self):
  for target in ('full_input_sha','start_state','end_state'):
   with self.subTest(field=target):
    bank=fixture();n=bank['details'][0]
    if target=='full_input_sha':n[target]='incorrect'
    else:n['original_full_result'][target]='incorrect'
    with self.assertRaisesRegex(ValueError,'binding differs|input hash differs'):compare_bank(**bank)
 def test_missing_extra_or_duplicate_new_calls_rejected(self):
  for mode in ('missing','duplicate','foreign'):
   with self.subTest(mode=mode):
    bank=fixture()
    if mode=='missing':bank['details'].pop()
    elif mode=='duplicate':bank['details'].append(copy.deepcopy(bank['details'][0]))
    else:bank['details'][0]['source_id']='foreign'
    with self.assertRaisesRegex(ValueError,'duplicate|missing/extra'):compare_bank(**bank)
 def test_prior_audit_anchor_is_independent(self):
  bank=fixture();bank['audit_histories']['s0'][0]='different'
  with self.assertRaisesRegex(ValueError,'prior frozen audit'):compare_bank(**bank)
 def test_old_wal_and_actual_job_must_agree(self):
  bank=fixture();bank['jobs'][0]['record']['selected_correction']=None
  with self.assertRaisesRegex(ValueError,'old actual C/WAL differs'):compare_bank(**bank)
 def test_original_root_is_compared_in_full(self):
  bank=fixture();bank['initials']['s0']['context']['text']='different';n=bank['details'][0];n['full_input_sha']=digest(bank['initials']['s0']);n['original_full_result']['start_state']=n['full_input_sha']
  with self.assertRaisesRegex(ValueError,'complete original start differs'):compare_bank(**bank)
 def test_early_model_evaluated_path_must_be_preserved(self):
  bank=fixture();bank['details'][1]['original_full_result']['native_model_evaluated']=True
  with self.assertRaisesRegex(ValueError,'model-evaluated path'):compare_bank(**bank)

if __name__=='__main__':unittest.main()
