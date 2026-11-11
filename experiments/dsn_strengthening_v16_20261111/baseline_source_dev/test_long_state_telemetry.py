import copy,unittest
from state_telemetry import NativeStateObserver,state_counts

class Shape:
 def __init__(self,*shape):self.shape=shape
class Context:
 def __init__(self):self.text='';self.prefix_token_ids=[99]
 def as_token_ids(self):return self.prefix_token_ids+[ord(x) for x in self.text]
class Engine:
 def __init__(self):self.context=Context();self.segments=[];self.tokens=[Shape(4,4)];self.last_attend_frame=50;self.max_text_len=30;self.max_context_tokens=8
 def insert_audio(self,segment=None):
  if segment is not None:self.segments.append(segment)
  removed=0
  while len(self.segments)>1 and sum(s.shape[0] for s in self.segments)>16000:
   removed=self.segments.pop(0).shape[0]/16000;self.last_attend_frame-=int(50*removed)
   if len(self.tokens)>1:self.tokens.pop(1);self.context.text+='ab'
  return removed
 def trim_context(self):
  while len(self.context.text)>self.max_context_tokens or sum(t.shape[1] for t in self.tokens)+len(self.context.text)>self.max_text_len-20:
   if not self.context.text:break
   self.context.text=self.context.text[1:]

class TelemetryControls(unittest.TestCase):
 def test_counts_and_no_observer_state_change(self):
  a=Engine();b=Engine();o=NativeStateObserver(a);o.bind(source_id='s',job_id='j',start_frontier=0,end_frontier=8000)
  self.assertEqual(a.insert_audio(Shape(8000)),b.insert_audio(Shape(8000)));self.assertEqual(state_counts(a),state_counts(b));self.assertEqual(o.recent[-1]['job_id'],'j');o.close()
 def test_shift_tracks_total_not_only_author_last_return(self):
  e=Engine();e.segments=[Shape(8000),Shape(8000)];e.tokens+=[Shape(4,1),Shape(4,2)];o=NativeStateObserver(e);e.insert_audio(Shape(16000));row=o.recent[-1];self.assertEqual(row['removed_samples'],16000);self.assertEqual(row['author_last_removed_seconds'],.5);self.assertEqual(e.last_attend_frame,0);o.close()
 def test_context_change_and_trigger(self):
  e=Engine();e.context.text='abcdefghijkl';o=NativeStateObserver(e);e.trim_context();r=o.recent[-1];self.assertTrue(r['before']['context_trim_triggered']);self.assertTrue(r['context_changed']);self.assertFalse(r['bound_still_exceeded']);o.close()
 def test_does_not_hide_unresolved_original_bound(self):
  e=Engine();e.tokens=[Shape(4,20)];o=NativeStateObserver(e);e.trim_context();self.assertTrue(o.recent[-1]['bound_still_exceeded']);o.close()
 def test_history_bounded_full_log_can_stream(self):
  records=[];e=Engine();o=NativeStateObserver(e,emit=records.append,history_limit=2)
  for _ in range(5):e.trim_context()
  self.assertEqual(len(o.recent),2);self.assertEqual(len(records),5);self.assertEqual(o.summary()['counts']['context_trim'],5);o.close()
 def test_copy_engine_not_misbound_to_original(self):
  e=Engine();o=NativeStateObserver(e);clone=copy.copy(e);clone.segments=[];clone.tokens=list(e.tokens);clone.context=copy.copy(e.context);clone.insert_audio(Shape(8000));self.assertEqual(e.segments,[]);self.assertEqual(len(clone.segments),1);self.assertEqual(len(o.recent),0);o.close()
 def test_restores_class_methods_and_existing_instance_method(self):
  e=Engine();original=e.insert_audio;self.assertNotIn('insert_audio',e.__dict__);o=NativeStateObserver(e);o.close();o.close();self.assertNotIn('insert_audio',e.__dict__);self.assertEqual(e.insert_audio,original)
 def test_invalid_bound_and_closed_observer(self):
  with self.assertRaises(ValueError):NativeStateObserver(Engine(),history_limit=0)
  o=NativeStateObserver(Engine());o.close()
  with self.assertRaises(ValueError):o.bind(source_id='s',job_id='j',start_frontier=0,end_frontier=1)
 def test_two_observed_engines_are_independent(self):
  a=Engine();b=Engine();oa=NativeStateObserver(a);ob=NativeStateObserver(b);a.trim_context();b.trim_context();self.assertEqual(len(oa.recent),1);self.assertEqual(len(ob.recent),1);oa.close();b.trim_context();self.assertEqual(len(ob.recent),2);ob.close()
 def test_control_row_flattens_into_owner_native_state_envelope(self):
  e=Engine();o=NativeStateObserver(e);e.trim_context();row=dict(kind='native_state',owner_epoch=0,**o.recent[-1]);self.assertEqual(row['kind'],'native_state');self.assertEqual(row['boundary'],'context_trim');o.close()
 def test_instance_override_is_explicitly_outside_observer_contract(self):
  e=Engine();e.insert_audio=lambda segment:None
  with self.assertRaises(ValueError):NativeStateObserver(e)
if __name__=='__main__':unittest.main()
