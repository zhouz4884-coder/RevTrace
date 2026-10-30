"""Apply only the evidenced oracle-wrapper lifetime/persistence repair to dev."""
import argparse,hashlib,json,pathlib
F=pathlib.Path(__file__).resolve().parents[1];S=F/'source_dev';p=argparse.ArgumentParser();p.add_argument('--gate',type=pathlib.Path,required=True);a=p.parse_args();gate=json.loads(a.gate.read_bytes())
assert gate['status']=='PASS_RELEASE_G96_AND_ALL_FIXED_ACTUAL_PREFIX_AND_INPUT_CONTROLS' and gate['all_fixed_actual_complete_state_C_IDs_equal'] is True and gate['complete_rows']==96
assert gate['imported_neural_source_commit']=='9492d3f9cb35e2b2849ec020817750a221248f0e' and gate['allocator_conf'] in (None,'expandable_segments:True')
path=S/'long_reference.py';text=path.read_text(encoding='utf8');old=text
def change(before,after):
 global text
 assert text.count(before)==1,before
 text=text.replace(before,after)
change('observer=None,stop_at=None):','observer=None,stop_at=None,before_infer=None):')
change("  start=cut_export(engine,frontier=previous,transcript=text,contract=contract)\n", "  start=cut_export(engine,frontier=previous,transcript=text,contract=contract)\n  if before_infer:before_infer(dict(source_id=source['source_id'],end=end,original_full_start_cut=start.state,reference_only=True))\n")
change("  result=dict(token_ids=list(ids),selected_correction=g.get('error_corrector'),appended_text=appended,native_model_evaluated='starting_tokens' in g)\n", "  result=dict(token_ids=list(ids),selected_correction=g.get('error_corrector'),appended_text=appended,native_model_evaluated='starting_tokens' in g)\n  # Returned GPU diagnostics are not feedback state. Release them before the\n  # generator pauses so the next original infer cannot overlap their lifetime.\n  del g\n")
change("def put(path,value):pathlib.Path(path).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\\n').encode('utf8'))", "def put(path,value):pathlib.Path(path).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\\n').encode('utf8'))\ndef put_durable(path,value):\n with pathlib.Path(path).open('wb') as f:f.write((json.dumps(value,ensure_ascii=False,indent=2)+'\\n').encode('utf8'));f.flush();os.fsync(f.fileno())")
change(" def __init__(self,path):self.file=pathlib.Path(path).open('xb');self.count=0\n def write(self,row):self.file.write(canonical_bytes(row)+b'\\n');self.file.flush();self.count+=1", " def __init__(self,path,durable=False):self.file=pathlib.Path(path).open('xb');self.count=0;self.durable=durable\n def write(self,row):\n  self.file.write(canonical_bytes(row)+b'\\n');self.file.flush()\n  if self.durable:os.fsync(self.file.fileno())\n  self.count+=1")
before="""   with NativeStateObserver(model.engine,emit=telemetry.write) as observer:
    for row in continuous_transitions(model,source,audio[sid],cut_export=export_cut,to_tensor=lambda x:torch.from_numpy(np.asarray(x,dtype=np.float32).copy()),sync=torch.cuda.synchronize,observer=observer):
     rows.append(row);put(out/'PROGRESS.json',dict(stage='continuous_original_no_restore',source_id=sid,completed=len(rows),expected=len(frontiers(source['frames']))))
    continuous_summary=observer.summary()
"""
after="""   complete_stream=JsonLines(folder/'CONTINUOUS_EDGES.jsonl',durable=True)
   try:
    with NativeStateObserver(model.engine,emit=telemetry.write) as observer:
     for row in continuous_transitions(model,source,audio[sid],cut_export=export_cut,to_tensor=lambda x:torch.from_numpy(np.asarray(x,dtype=np.float32).copy()),sync=torch.cuda.synchronize,observer=observer,before_infer=lambda entry:put_durable(folder/'LAST_ORIGINAL_INPUT.json',entry)):
      complete_stream.write(row);rows.append(row);put(out/'PROGRESS.json',dict(stage='continuous_original_no_restore',source_id=sid,completed=len(rows),expected=len(frontiers(source['frames']))))
     continuous_summary=observer.summary()
   finally:complete_stream.close()
"""
change(before,after);path.write_bytes(text.encode('utf8'))
env_fields="PYTORCH_CUDA_ALLOC_CONF=os.environ.get('PYTORCH_CUDA_ALLOC_CONF'),PYTORCH_ALLOC_CONF=os.environ.get('PYTORCH_ALLOC_CONF')"
text=path.read_text(encoding='utf8');needle="scope='Offline neural continuous-author/restore equivalence only, not serving'";assert text.count(needle)==1;text=text.replace(needle,needle+','+env_fields);needle="autocast=torch.is_autocast_enabled(),reference_only=True";assert text.count(needle)==1;text=text.replace(needle,"autocast=torch.is_autocast_enabled(),"+env_fields+",reference_only=True");path.write_bytes(text.encode())
trial=S/'resilience_trial.py';text=trial.read_text(encoding='utf8');needle="failure_domain='Owner+model workers; Supervisor/ingress/actualConsumer/power/storage survive'";assert text.count(needle)==1;trial.write_bytes(text.replace(needle,needle+','+env_fields).encode())
worker=S/'stage_worker.py';text=worker.read_text(encoding='utf8');needle="CUDA_VISIBLE_DEVICES=os.environ['CUDA_VISIBLE_DEVICES']";assert text.count(needle)==1;worker.write_bytes(text.replace(needle,needle+','+env_fields).encode())
test=S/'test_long_reference.py';addition=r'''

class OracleLifetimeAndDurabilityControls(unittest.TestCase):
 def test_generation_is_dead_at_yield_and_before_next_original_infer(self):
  import weakref
  class Generation(dict):pass
  class CheckedEngine(Engine):
   old_generation=None
   def infer(self,**kw):
    if self.old_generation is not None:assert self.old_generation() is None
    ids,g=super().infer(**kw);g=Generation(g);self.old_generation=weakref.ref(g);return ids,g
  m=Model();m.engine=CheckedEngine();iterator=continuous_transitions(m,dict(source_id='s',audio_sha256='x',frames=16001),[0]*16001,cut_export=export,to_tensor=lambda a:a,sync=lambda:None)
  first=next(iterator);self.assertIsNone(m.engine.old_generation());rest=list(iterator);self.assertEqual(first['end'],8000);self.assertEqual(rest[-1]['original_full_cut']['transcript'],'8000;16000;16001;')
 def test_complete_original_start_callback_precedes_input_and_preserves_EOS(self):
  m=Model();seen=[]
  def checkpoint(row):seen.append((copy.deepcopy(row),m.engine.frames))
  rows=list(continuous_transitions(m,dict(source_id='s',audio_sha256='x',frames=16001),[0]*16001,cut_export=export,to_tensor=lambda a:a,sync=lambda:None,before_infer=checkpoint))
  self.assertEqual([v for _,v in seen],[0,8000,16000]);self.assertEqual([r['end'] for r,_ in seen],[8000,16000,16001]);self.assertEqual(seen[1][0]['original_full_start_cut'],rows[0]['original_full_cut']);self.assertEqual(m.engine.calls[-1],('infer',True))
 def test_streamed_complete_rows_are_exclusive_and_fsynced(self):
  import json,pathlib,tempfile
  from unittest.mock import patch
  from long_reference import JsonLines
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'complete.jsonl'
   with patch('long_reference.os.fsync') as sync:
    writer=JsonLines(p,durable=True);writer.write({'complete':1});writer.write({'complete':2});self.assertEqual(writer.count,2);self.assertEqual(sync.call_count,2);writer.close()
   self.assertEqual([json.loads(x) for x in p.read_bytes().splitlines()],[{'complete':1},{'complete':2}])
   with self.assertRaises(FileExistsError):JsonLines(p,durable=True)
 def test_last_original_input_is_fsynced_before_return(self):
  import json,pathlib,tempfile
  from unittest.mock import patch
  from long_reference import put_durable
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'start.json'
   with patch('long_reference.os.fsync') as sync:put_durable(p,{'original_full_start_cut':{'frontier':752000}});self.assertEqual(sync.call_count,1)
   self.assertEqual(json.loads(p.read_bytes()),{'original_full_start_cut':{'frontier':752000}})
'''
content=test.read_text(encoding='utf8');assert 'OracleLifetimeAndDurabilityControls' not in content;assert "if __name__=='__main__':unittest.main()" in content;test.write_bytes(content.replace("if __name__=='__main__':unittest.main()",addition+"\nif __name__=='__main__':unittest.main()\n").encode())
receipt=F/'LONG_REFERENCE_REPAIR_EVIDENCE_v2.json';assert not receipt.exists();receipt.write_bytes((json.dumps(dict(repair='Returned generation GPU-diagnostic lifetime and durable original-edge/start checkpoints; actual allocator ENV/ready diagnostic fields only',actual_gate=str(a.gate.resolve()),actual_gate_sha256=hashlib.sha256(a.gate.read_bytes()).hexdigest(),files_changed=['long_reference.py','test_long_reference.py','resilience_trial.py','stage_worker.py'],original_NativeBridge_C_U_protocol_guards_unmodified=True,model_precision_cadence_EOS_unchanged=True,allocator_control=gate['allocator_conf']),indent=2)+'\n').encode());print('Applied evidenced narrow reference repair to source_dev; source not yet frozen or launched')
