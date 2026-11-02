import pathlib,unittest,types
from unittest.mock import patch
from candidate_bridge import CandidateBridge,KnownInvalidASRPrefix
from native_bridge import NativeBridge

class Engine:
 def __init__(self):self.C_calls=0;self.result=object()
 def _run_SpeechLM_error_corrector(self):self.C_calls+=1;return self.result
 def infer(self):return self._run_SpeechLM_error_corrector()

class CEntryGuardControls(unittest.TestCase):
 def make(self):
  b=CandidateBridge.__new__(CandidateBridge);b.engine=Engine();b.author_file=pathlib.Path(__file__);b.stage_role='authority';b.key=lambda **kwargs:'fixed';b.project_open=lambda **kwargs:dict(end={'transcript':'early'},token_ids=[1]);return b
 def fake_step(self,bridge,**kwargs):return bridge.engine.infer(),{}
 def test_known_invalid_stops_before_C_and_restores_original_binding(self):
  b=self.make();original=b.engine._run_SpeechLM_error_corrector
  def stop():raise KnownInvalidASRPrefix({'actual_start_witness':'different'})
  with patch.object(NativeBridge,'step',lambda instance,**kwargs:self.fake_step(instance,**kwargs)),self.assertRaises(KnownInvalidASRPrefix):b.full_step(audio=None,start=types.SimpleNamespace(transcript=''),end=1,is_last=False,before_corrector=stop)
  self.assertEqual(b.engine.C_calls,0);self.assertIs(b.engine._run_SpeechLM_error_corrector.__func__,original.__func__)
 def test_unconfirmed_parent_does_not_stop_or_replace_C_result(self):
  b=self.make();start=types.SimpleNamespace(transcript='',state={},sha256='start')
  with patch.object(NativeBridge,'step',lambda instance,**kwargs:self.fake_step(instance,**kwargs)):result,_=b.full_step(audio=None,start=start,end=1,is_last=False,before_corrector=lambda:None)
  self.assertEqual(b.engine.C_calls,1);self.assertIs(result,b.engine.result)

if __name__=='__main__':unittest.main()
