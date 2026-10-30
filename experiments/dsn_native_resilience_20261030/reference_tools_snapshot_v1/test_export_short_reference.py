import copy,unittest
from export_short_reference import extract,combine,digest,BDFA

def state(F=0,text='',sid='audio'):
 return dict(audio_segments=[],tokens=[],context=dict(text='',prefix_token_ids=[1],token_ids=[1]),last_attend_frame=0,detected_language='zh',initial_tokens=[[1]],initial_token_length=1,sot_index=0,decoder_type='beam',contract=dict(source_sha=sid,stage_execution=dict(source_commit=BDFA)),frontier=F,transcript=text)
def fixture():
 source=dict(source_id='old',speaker_id='speaker',frames=16001,audio_sha256='audio');jobs=[];hist={'old':[]};wal=[];dispatch=[];events=[];previous=state()
 for i,F in enumerate((8000,16000,16001),1):
  end=state(F,str(i));jid='j'+str(i);record=dict(role='authority',candidate_handoff=False,start=previous['frontier'],end=F,start_state=digest(previous),end_state=digest(end),token_ids=[i],selected_correction={'choice':i},model_start=i+.1,model_end=i+.2)
  jobs.append(dict(kind='completed',mode='authority',source_id='old',worker='full0',physical_channel_worker='full0',job_id=jid,dispatch_epoch=0,start=previous,end=end,record=record,received_perf=i+.3));hist['old'].append(dict(F=F,state=end,state_sha256=digest(end),token_ids=[i]));wal.append(dict(state=end,state_sha256=digest(end),selected={'choice':i},dispatch_epoch=0));dispatch.append(dict(job_id=jid,worker='full0',source_id='old',start=previous['frontier'],end=F,start_sha=digest(previous),dispatch_epoch=0,dispatched_perf=i));events.append(dict(kind='canonical_install',job_id=jid,observed=i+.4));previous=end
 return source,jobs,hist,wal,dispatch,events,{'raw':'hash'}

class ExportControls(unittest.TestCase):
 def test_exact_complete_calls_preserved(self):
  args=fixture();rows=extract(*args);self.assertEqual([r['end'] for r in rows],[8000,16000,16001]);self.assertEqual(rows[0]['original_full_start_cut'],args[1][0]['start']);self.assertEqual(rows[-1]['original_full_result'],args[1][-1]['record']);self.assertEqual(rows[-1]['provenance']['actual_execution_source_commit'],BDFA)
 def test_missing_EOS_rejected(self):
  a=list(fixture());a[3]=a[3][:-1]
  with self.assertRaises(ValueError):extract(*a)
 def test_wrong_C_not_hidden_by_same_text(self):
  a=copy.deepcopy(list(fixture()));a[3][1]['selected']={'choice':99}
  with self.assertRaises(ValueError):extract(*a)
 def test_wrong_IDs_rejected(self):
  a=copy.deepcopy(list(fixture()));a[2]['old'][1]['token_ids']=[99]
  with self.assertRaises(ValueError):extract(*a)
 def test_incomplete_state_rejected(self):
  a=copy.deepcopy(list(fixture()));del a[1][0]['start']['context']
  with self.assertRaises(ValueError):extract(*a)
 def test_old99_marker_never_relabelled(self):
  a=copy.deepcopy(list(fixture()));a[1][0]['start']['contract']['stage_execution']['source_commit']='99'*20
  with self.assertRaises(ValueError):extract(*a)
 def test_changed_frozen_input_even_if_bound_consistently_rejected(self):
  a=copy.deepcopy(list(fixture()));s=a[1][1]['start'];s['context']['text']='changed';a[1][1]['record']['start_state']=digest(s);a[4][1]['start_sha']=digest(s)
  with self.assertRaises(ValueError):extract(*a)
 def test_foreign_physical_channel_rejected(self):
  a=copy.deepcopy(list(fixture()));a[1][0]['physical_channel_worker']='full1'
  with self.assertRaises(ValueError):extract(*a)
 def test_candidate_handoff_cannot_be_called_original_full(self):
  a=copy.deepcopy(list(fixture()));a[1][0]['record']['candidate_handoff']=True
  with self.assertRaises(ValueError):extract(*a)
 def test_duplicate_target_or_job_id_rejected(self):
  a=copy.deepcopy(list(fixture()));a[1][1]=copy.deepcopy(a[1][0])
  with self.assertRaises(ValueError):extract(*a)
 def test_combine_disjoint_preserves_objects_and_adds_only_provenance(self):
  old=extract(*fixture());new=copy.deepcopy(old[:1]);new[0]['source_id']='new';merged=combine(old,new,{'input_sha':'fixed'});self.assertEqual(merged[-1],old[-1]);self.assertEqual(merged[0]['original_full_cut'],new[0]['original_full_cut']);self.assertEqual(merged[0]['original_full_cut']['contract']['stage_execution']['source_commit'],BDFA)
 def test_combine_overlapping_source_rejected(self):
  old=extract(*fixture())
  with self.assertRaises(ValueError):combine(old,old,{})
 def test_existing_reference_hash_mutation_rejected(self):
  old=extract(*fixture());new=copy.deepcopy(old[:1]);new[0]['source_id']='new';new[0]['full_input_sha']='bad'
  with self.assertRaises(ValueError):combine(old,new,{})
if __name__=='__main__':unittest.main()
