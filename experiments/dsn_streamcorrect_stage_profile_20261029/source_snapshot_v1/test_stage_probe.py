import pathlib,tempfile,types,unittest,time
import torch
from stage_probe import StageProbe,packet_input_signature

class Engine:
    def __init__(self):
        self.tokens=[];self.segments=[torch.arange(8,dtype=torch.float32)];self.context=types.SimpleNamespace(text='prior',prefix_token_ids=[1]);self.last_attend_frame=2;self.detected_language='zh';self.initial_tokens=torch.tensor([[1,2,3,4]]);self.initial_token_length=4;self.sot_index=0;self.decoder_type='beam';self.cfg=types.SimpleNamespace(beam_size=4);self.is_warmup=False;self.kv_cache={'dirty':torch.ones(2)};self.dec_attns=[torch.ones(2)];self.inference=types.SimpleNamespace(kv_cache=self.kv_cache);self.token_decoder=types.SimpleNamespace(finished_sequences={});self.model=types.SimpleNamespace(device='cpu');self.calls=[];self.result={'corrected_appended_text':'chosen'}
    def _run_SpeechLM_error_corrector(self,**kwargs):self.calls.append(kwargs);return self.result
    def _clean_cache(self):self.kv_cache={};self.dec_attns=[];self.inference.kv_cache={}
    def infer(self,skip=False):
        current_tokens=torch.tensor([[1,2,3,4,7],[1,2,3,4,8],[1,2,3,4,9],[1,2,3,4,10]]);token_len_before_decoding=4;fire_detected=False;is_last=True;generation={'frame_delay':False};use_error_corrector=not skip
        r=None if skip else self._run_SpeechLM_error_corrector(input_audio=self.segments[0],current_tokens=current_tokens,token_len_before_decoding=token_len_before_decoding,corrector_model=self.model,corrector_processor=None)
        if r is not None:r['corrected_appended_token_ids']=[99];self.tokens.append(torch.tensor([[99]]))
        self._clean_cache();return r,current_tokens

class ProbeControls(unittest.TestCase):
    def run_probe(self,mode='full',skip=False):
        root=tempfile.TemporaryDirectory();self.addCleanup(root.cleanup);e=Engine();p=StageProbe(e,pathlib.Path(root.name),__file__,sync=lambda:None,capture_mode=mode);p.begin({'step_id':'fixed'});begin=time.perf_counter();r,t=e.infer(skip);end=time.perf_counter();row=p.end(dict(model_start=begin,model_end=end,model_seconds=end-begin),types.SimpleNamespace(sha256='closed',state={'chosen':r}));p.close();return e,r,t,row
    def test_original_objects_and_result_are_unchanged(self):
        e,r,t,row=self.run_probe();self.assertIs(e.calls[0]['current_tokens'],t);self.assertIs(r,e.result);self.assertEqual(r['corrected_appended_token_ids'],[99])
    def test_ordered_full_beams_and_predecode_length(self):
        _,_,t,row=self.run_probe();packet=row['calls'][0]['packet'];blob=packet['corrector_input']['current_tokens'];self.assertTrue(torch.equal(torch.load(blob['tensor_blob'],weights_only=True),t));self.assertEqual(packet['corrector_input']['token_len_before_decoding'],4)
    def test_open_state_is_not_a_closed_cut(self):
        _,_,_,row=self.run_probe();s=row['calls'][0]['packet']['post_asr_open_state'];self.assertTrue(s['open_state']);self.assertFalse(s['closed_cut']);self.assertTrue(s['ephemeral_cache_metadata']['kv_cache']['0']['payload_omitted'])
    def test_original_cleanup_and_fallback_locals_preserved(self):
        e,_,_,row=self.run_probe();self.assertEqual(e.kv_cache,{});self.assertIn('fire_detected',row['preclean'][0]['caller']['fallback_locals']);self.assertTrue(row['preclean'][0]['caller']['fallback_locals']['is_last'])
    def test_no_corrector_path_not_fabricated_as_packet(self):
        _,r,_,row=self.run_probe(skip=True);self.assertIsNone(r);self.assertFalse(row['C_called']);self.assertFalse(row['candidate_packet_admitted']);self.assertEqual(row['stage_seconds']['C'],0)
    def test_deferred_capture_has_same_full_input_signature(self):
        *_,a=self.run_probe('full');*_,b=self.run_probe('deferred');self.assertEqual(packet_input_signature(a['calls'][0]['packet']),packet_input_signature(b['calls'][0]['packet']))
    def test_same_input_with_different_selected_end_not_filtered(self):
        *_,row=self.run_probe();sig=packet_input_signature(row['calls'][0]['packet']);row['closed_end_state']={'different':True};self.assertEqual(packet_input_signature(row['calls'][0]['packet']),sig)
    def test_cleanup_outside_infer_is_not_captured(self):
        with tempfile.TemporaryDirectory() as d:
            e=Engine();p=StageProbe(e,d,__file__,sync=lambda:None);p.begin({'step_id':'x'});e._clean_cache();self.assertEqual(p.active['preclean'],[]);p.close()
    def test_configuration_values_are_captured(self):
        *_,row=self.run_probe();self.assertEqual(row['calls'][0]['packet']['post_asr_open_state']['cfg']['beam_size'],4)
    def test_generation_flags_are_compared(self):
        *_,row=self.run_probe();p=row['calls'][0]['packet'];before=packet_input_signature(p);p['caller']['native_generation_flags']['no_speech']=True;self.assertNotEqual(before,packet_input_signature(p))
    def test_first_actual_corrector_call_is_explicit(self):
        *_,row=self.run_probe();self.assertTrue(row['calls'][0]['first_actual_corrector_call_in_process']);self.assertEqual(row['calls'][0]['corrector_call_index_in_process'],1)

if __name__=='__main__':unittest.main()
