"""Pure stdlib CPU controls. No model package/import, GPU, data access or ZIP."""
import copy,unittest
from original_full_reference import METHOD_COMMIT,DISK,digest,full_rows,validate_selection,validate_original_bindings

def source(n,frames=128001):
 return dict(source_id='BAC009S'+str(8000+n)+'W0001',speaker_id='S'+str(8000+n),
  path=DISK+'/datasets/revtrace/new/audio/'+str(n)+'.wav',audio_sha256=str(n)*64,frames=frames,reference='official text')
def selected():
 sources=[source(i) for i in (1,2,3,4)]
 return dict(metadata_only_before_neural=True,method_source_commit=METHOD_COMMIT,selection_created_utc='2026-10-29T12:00:00Z',
  excluded_speakers=['S0764','S0765','S0767','S0768','S0766','S0769'],sources=sources),sources

class FakeCut:
 def __init__(self,state):self.state=copy.deepcopy(state);self.frontier=state['frontier'];self.sha256=digest(self.state)
class FakeOriginalFull:
 def __init__(self):self.calls=[]
 def initial_for(self,sha):return FakeCut(dict(frontier=0,transcript='',contract=dict(source_sha=sha)))
 def full_step(self,**kw):
  self.calls.append(kw);start=kw['start'];end=kw['end'];cut=FakeCut(dict(frontier=end,transcript='fixed',contract=start.state['contract']))
  return cut,dict(start=start.frontier,end=end,start_state=start.sha256,end_state=cut.sha256,role='authority',candidate_handoff=False,
   token_ids=[] if end==8000 else [9],selected_correction=None if end==8000 else dict(prompt='original',choice='actual C'))

class ReferenceControls(unittest.TestCase):
 def test_four_metadata_locked_new_speakers_pass(self):
  receipt,sources=selected();self.assertEqual(validate_selection(receipt,sources)['distinct_speakers'],4)
 def test_used_speaker_or_duplicate_speaker_rejected(self):
  for mode in ('used','duplicate'):
   receipt,sources=selected()
   if mode=='used':receipt['excluded_speakers'].append(sources[0]['speaker_id'])
   else:sources[1]=copy.deepcopy(sources[0])
   with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,'used|duplicate'):validate_selection(receipt,sources)
 def test_plan_cannot_change_locked_source_order_or_data(self):
  receipt,sources=selected();other=copy.deepcopy(sources);other.reverse()
  with self.assertRaisesRegex(ValueError,'locked'):validate_selection(receipt,other)
 def test_method_frozen_before_selection_required(self):
  receipt,sources=selected();receipt['method_source_commit']='different'
  with self.assertRaisesRegex(ValueError,'method must be frozen'):validate_selection(receipt,sources)
 def test_outcome_based_or_unlocked_selection_rejected(self):
  receipt,sources=selected();receipt['metadata_only_before_neural']=False
  with self.assertRaisesRegex(ValueError,'metadata-only'):validate_selection(receipt,sources)
 def test_old_native_speaker_exclusion_is_mandatory(self):
  receipt,sources=selected();receipt['excluded_speakers'].remove('S0764')
  with self.assertRaisesRegex(ValueError,'exclusions incomplete'):validate_selection(receipt,sources)
 def test_original_source_identity_and_duration_required(self):
  for key,value in [('frames',127999),('speaker_id','wrong'),('audio_sha256','not-sha'),('path','/tmp/new.wav')]:
   receipt,sources=selected();sources[0][key]=value
   with self.subTest(field=key),self.assertRaises(ValueError):validate_selection(receipt,sources)
 def test_all_full_EOS_and_empty_early_return_entries_preserved(self):
  s=source(1,16001);m=FakeOriginalFull();rows=full_rows(m,{s['source_id']:[0]*16001},[s])
  self.assertEqual([r['end'] for r in rows],[8000,16000,16001]);self.assertIsNone(rows[0]['original_full_result']['selected_correction'])
  self.assertEqual(rows[0]['original_full_result']['token_ids'],[]);self.assertTrue(rows[-1]['reference_only']);self.assertTrue(rows[-1]['not_serving'])
  self.assertEqual([r['is_last'] for r in m.calls],[False,False,True])
 def test_no_early_projection_capture_speculation_or_callback(self):
  s=source(1,8000);m=FakeOriginalFull();full_rows(m,{s['source_id']:[0]*8000},[s])
  self.assertIsNone(m.calls[0]['on_asr']);self.assertIs(m.calls[0]['capture_required'],False);self.assertIsNone(m.calls[0]['before_corrector'])
 def test_each_source_starts_fresh_with_its_own_immutable_identity(self):
  sources=[source(1,8000),source(2,8000)];m=FakeOriginalFull();rows=full_rows(m,{s['source_id']:[0]*8000 for s in sources},sources)
  self.assertEqual([r['start'] for r in rows],[0,0]);self.assertNotEqual(rows[0]['full_input_sha'],rows[1]['full_input_sha'])
 def test_same_input_repeat_preserves_reference_values(self):
  s=source(1,16000);audio={s['source_id']:[0]*16000}
  self.assertEqual(full_rows(FakeOriginalFull(),audio,[s]),full_rows(FakeOriginalFull(),audio,[s]))
 def test_wrong_original_result_hash_or_path_is_rejected(self):
  s=source(1,8000)
  for mode in ('hash','handoff'):
   m=FakeOriginalFull();original=m.full_step
   def bad(**kw):
    c,r=original(**kw)
    if mode=='hash':r['end_state']='wrong'
    else:r['candidate_handoff']=True
    return c,r
   m.full_step=bad
   with self.subTest(mode=mode),self.assertRaises(ValueError):full_rows(m,{s['source_id']:[0]*8000},[s])
 def test_original_backend_and_old_warmup_cannot_be_replaced(self):
  old=dict(source_id='BAC009S0764W0209',path='fixed',audio_sha256='fixed');state=dict(frontier=24000)
  cfg=dict(settings=dict(source_commit=METHOD_COMMIT,corrector_dtype='float32',backend=dict(model='original'),sources=[old],warmup=dict(original_reference_start_state=state)))
  plan=dict(backend=dict(model='original'),fixed_old_warmup=dict(source_id=old['source_id'],fixed_start=24000,fixed_end=32000,audio_source=old,original_reference_start_state=state))
  validate_original_bindings(plan,cfg)
  for mode in ('backend','warmup'):
   p=copy.deepcopy(plan)
   if mode=='backend':p['backend']['model']='replacement'
   else:p['fixed_old_warmup']['original_reference_start_state']['frontier']=16000
   with self.subTest(mode=mode),self.assertRaises(ValueError):validate_original_bindings(p,cfg)

if __name__=='__main__':unittest.main()
