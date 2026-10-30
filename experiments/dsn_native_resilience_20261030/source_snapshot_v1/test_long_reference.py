import ast,copy,inspect,unittest
from feedback_contract import FeedbackCut
from long_reference import frontiers,continuous_transitions,compare_edge

def cut(frontier=0,text='',contract=None,tokens=None):
 return FeedbackCut(dict(audio_segments=[],tokens=tokens or [],context=dict(text='',prefix_token_ids=[1],token_ids=[1]),last_attend_frame=frontier,detected_language='zh',initial_tokens=[[1]],initial_token_length=1,sot_index=0,decoder_type='beam',contract=contract or {'source_sha':'x'},frontier=frontier,transcript=text))
class Tokenizer:
 def decode(self,ids):return ''.join(str(i)+';' for i in ids)
class Engine:
 def __init__(self):self.frames=0;self.calls=[];self.tokenizer=Tokenizer()
 def insert_audio(self,a):self.frames+=len(a);self.calls.append(('insert',len(a)))
 def infer(self,**kw):self.calls.append(('infer',kw['is_last']));return [self.frames],dict(error_corrector={'selected':str(self.frames)},starting_tokens=True)
class Model:
 def __init__(self):self.engine=Engine();self.corrector_model=object();self.corrector_processor=object()
 def initial_for(self,sha):return cut(contract={'source_sha':sha})
 def full_step(self,*a,**kw):raise AssertionError('continuous oracle must not share the restore path')
def export(engine,*,frontier,transcript,contract):
 assert engine.frames==frontier
 return cut(frontier,transcript,contract,tokens=[[engine.frames]])

class LongReferenceControls(unittest.TestCase):
 def test_original_cadence_keeps_partial_and_exact_EOS(self):
  self.assertEqual(frontiers(16001),[8000,16000,16001]);self.assertEqual(frontiers(16000),[8000,16000]);self.assertEqual(frontiers(1),[1])
 def test_invalid_source_frames_rejected(self):
  for value in (0,-1,1.5,None):
   with self.assertRaises(ValueError):frontiers(value)
 def test_continuous_original_engine_not_restore(self):
  m=Model();rows=list(continuous_transitions(m,dict(source_id='s',audio_sha256='x',frames=16001),[0]*16001,cut_export=export,to_tensor=lambda a:a,sync=lambda:None));self.assertEqual([r['end'] for r in rows],[8000,16000,16001]);self.assertEqual(m.engine.calls,[('insert',8000),('infer',False),('insert',8000),('infer',False),('insert',1),('infer',True)]);self.assertEqual(rows[-1]['original_full_cut']['transcript'],'8000;16000;16001;');self.assertEqual(rows[1]['original_full_start_cut'],rows[0]['original_full_cut'])
 def test_diagnostic_prefix_does_not_create_fake_EOS(self):
  m=Model();rows=list(continuous_transitions(m,dict(source_id='s',audio_sha256='x',frames=16001),[0]*16001,cut_export=export,to_tensor=lambda a:a,sync=lambda:None,stop_at=8000));self.assertEqual(len(rows),1);self.assertEqual(m.engine.calls[-1],('infer',False))
 def test_continuous_loop_statically_has_no_restore_or_bridge_step(self):
  tree=ast.parse(inspect.getsource(continuous_transitions));names=[n.func.id if isinstance(n.func,ast.Name) else n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))];self.assertNotIn('restore_cut',names);self.assertNotIn('full_step',names);self.assertIn('infer',names)
 def setup_compare(self):
  start=cut();end=cut(8000,'a');reference=dict(source_id='s',end=8000,original_full_start_cut=start.state,original_full_cut=end.state,original_full_result=dict(token_ids=[7],selected_correction={'choice':'a'}));record=dict(start_state=start.sha256,end_state=end.sha256,token_ids=[7],selected_correction={'choice':'a'});return reference,end,record
 def test_equal_full_edge_passes(self):
  a,b,c=self.setup_compare();self.assertTrue(compare_edge(a,b,c)['all_equal'])
 def test_full_contract_tag_is_not_projected_away(self):
  a,b,c=self.setup_compare();s=b.state;s['contract']['stage_execution']='changed';changed=FeedbackCut(s);c['end_state']=changed.sha256;result=compare_edge(a,changed,c);self.assertFalse(result['all_equal']);self.assertEqual(result['different_complete_cut_fields'],['contract'])
 def test_each_original_C_and_ID_and_start_binding_is_required(self):
  for field,value in [('selected_correction',{'choice':'b'}),('token_ids',[8]),('start_state','wrong'),('end_state','wrong')]:
   a,b,c=self.setup_compare();c[field]=value;self.assertFalse(compare_edge(a,b,c)['all_equal'])
if __name__=='__main__':unittest.main()
