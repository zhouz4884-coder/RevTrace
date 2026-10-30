import gc,types,unittest,weakref
from memory_release import storage_inventory,generation_storage_report,continuous_transitions_release_g,compare_rows

try:import torch
except ImportError:torch=None
class Box:
 def __init__(self,state):self.state=state
class Generation(dict):pass
class Tokenizer:
 def decode(self,ids):return str(ids[0])+';'
class Engine:
 def __init__(self):self.total=0;self.tokenizer=Tokenizer();self.previous=None;self.calls=[]
 def insert_audio(self,a):self.total+=len(a)
 def infer(self,**kw):
  if self.previous is not None and self.previous() is not None:raise AssertionError('previous returned generation still live at next infer')
  value=Generation(error_corrector={'text':str(self.total)},starting_tokens=True,diagnostic=object());self.previous=weakref.ref(value);self.calls.append(kw['is_last']);return [self.total],value
class Model:
 def __init__(self):self.engine=Engine();self.corrector_model=object();self.corrector_processor=object()
 def initial_for(self,sha):return Box({'contract':{'source_sha':sha}})
def export(engine,*,frontier,transcript,contract):return Box(dict(frontier=frontier,transcript=transcript,contract=contract))

class ReleaseControls(unittest.TestCase):
 def row(self,F=8000):return dict(source_id='s',end=F,original_full_start_cut={'frontier':F-8000,'contract':{'source_commit':'actual'}},original_full_cut={'frontier':F,'contract':{'source_commit':'actual'},'tokens':[3]},original_full_result={'selected_correction':{'text':'a'},'token_ids':[3]},original_model_start=1.,original_model_end=2.)
 def test_strict_common_prefix_ignores_only_outside_semantic_timing(self):
  import copy
  old=[self.row(8000),self.row(16000)];new=copy.deepcopy(old)+[self.row(24000)];new[0]['original_model_start']=99.;r=compare_rows(old,new);self.assertTrue(r['all_old_rows_matched']);self.assertTrue(r['all_common_semantics_equal']);self.assertTrue(r['old_keys_are_contiguous_new_prefix'])
 def test_same_input_repeats_can_both_match_one_new_edge(self):
  r=compare_rows([self.row(16000),self.row(16000)],[self.row(8000),self.row(16000)]);self.assertTrue(r['all_common_semantics_equal']);self.assertEqual(r['compared_pairs'],2)
 def test_state_C_ID_and_source_tag_are_not_ignored(self):
  import copy
  for field in ('start','end','C','IDs','source_tag'):
   a=self.row();b=copy.deepcopy(a)
   if field=='start':b['original_full_start_cut']['frontier']=1
   elif field=='end':b['original_full_cut']['tokens']=[4]
   elif field=='C':b['original_full_result']['selected_correction']={'text':'b'}
   elif field=='IDs':b['original_full_result']['token_ids']=[4]
   else:b['original_full_cut']['contract']['source_commit']='changed'
   self.assertFalse(compare_rows([a],[b])['all_common_semantics_equal'])
 def test_generation_freed_before_yield_and_next_original_call(self):
  m=Model();rows=continuous_transitions_release_g(m,dict(source_id='s',audio_sha256='a',frames=16001),[0]*16001,cut_export=export,to_tensor=lambda x:x,sync=lambda:None,memory_stats=lambda:{'allocated':None,'reserved':None},storage_reporter=lambda *args:{'synthetic':True});first=next(rows);self.assertIsNone(m.engine.previous());rest=list(rows);self.assertEqual([first['end']]+[r['end'] for r in rest],[8000,16000,16001]);self.assertEqual(rest[-1]['original_full_result']['token_ids'],[16001]);self.assertEqual(rest[-1]['original_full_result']['selected_correction'],{'text':'16001'});self.assertEqual(m.engine.calls,[False,False,True])
 @unittest.skipIf(torch is None,'CPU Torch unavailable')
 def test_alias_views_count_one_storage(self):
  t=torch.arange(12,dtype=torch.float32);values,count=storage_inventory({'one':t,'view':t.view(3,4)},cuda_only=False);self.assertEqual(len(values),1);self.assertEqual(sum(v['storage_bytes'] for v in values.values()),48);self.assertEqual(count,2)
 @unittest.skipIf(torch is None,'CPU Torch unavailable')
 def test_shared_engine_and_semantic_storages_excluded(self):
  a=torch.arange(8);b=torch.arange(9);c=torch.arange(10);engine=types.SimpleNamespace(tokens=[a],segments=[],kv_cache={},dec_attns=[],initial_tokens=[]);report=generation_storage_report({'debug':[a,b,c]},engine,{'selected_tensor':b},cuda_only=False);self.assertEqual(report['g_exclusive_storage_bytes'],c.untyped_storage().nbytes());self.assertEqual(report['g_shared_with_engine_or_semantic_result_storage_bytes'],a.untyped_storage().nbytes()+b.untyped_storage().nbytes())
 @unittest.skipIf(torch is None,'CPU Torch unavailable')
 def test_inventory_result_keeps_no_tensor_alive(self):
  t=torch.arange(8);ref=weakref.ref(t);g={'debug':t};engine=types.SimpleNamespace();report=generation_storage_report(g,engine,{},cuda_only=False);del g,t;gc.collect();self.assertIsNone(ref());self.assertGreater(report['g_exclusive_storage_bytes'],0)
 @unittest.skipIf(torch is None,'CPU Torch unavailable')
 def test_author_Logits_tokens_interface(self):
  Logits=type('Logits',(),{'__module__':'simul_whisper.generation_progress'});obj=Logits();obj.tokens=torch.arange(7);values,count=storage_inventory({'logits_starting':obj},cuda_only=False);self.assertEqual(count,1);self.assertEqual(sum(v['storage_bytes'] for v in values.values()),obj.tokens.untyped_storage().nbytes())
if __name__=='__main__':unittest.main()
