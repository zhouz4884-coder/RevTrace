import copy,types,unittest
import numpy as np
import torch
from native_bridge import export_cut,restore_cut

class Context:
    def __init__(self):self.text='';self.prefix_token_ids=[5]
    def as_token_ids(self):return self.prefix_token_ids+[ord(x) for x in self.text]

class Engine:
    def __init__(self):
        self.model=types.SimpleNamespace(device=torch.device('cpu'))
        self.decoder_type='beam';self.cfg=types.SimpleNamespace(beam_size=4,language='zh')
        self.detected_language='zh';self.is_warmup=False;self.kv_cache={};self.dec_attns=[]
        self.inference=types.SimpleNamespace(kv_cache={});self.token_decoder=types.SimpleNamespace(finished_sequences=None)
        self.segments=[];self.tokens=[torch.tensor([[1,2]])];self.context=Context()
        self.last_attend_frame=-1500;self.initial_tokens=torch.tensor([[1,2]]);self.initial_token_length=2;self.sot_index=0
    def _clean_cache(self):self.kv_cache={};self.dec_attns=[];self.inference.kv_cache={};self.token_decoder.finished_sequences=None

class Roundtrip(unittest.TestCase):
    def test_complete_state_roundtrip_with_native_audio_tokens_and_context(self):
        e=Engine();audio=np.linspace(-.2,.2,16000,dtype=np.float32)
        e.segments=[torch.from_numpy(audio[:8000]),torch.from_numpy(audio[8000:])]
        e.tokens.append(torch.tensor([[6,7]]));e.context.text='你好';e.last_attend_frame=12
        c=export_cut(e,frontier=16000,transcript='你好',contract={'fixed':1});target=Engine()
        restore_cut(target,c,audio=audio,contract={'fixed':1})
        self.assertTrue(c.same(export_cut(target,frontier=16000,transcript='你好',contract={'fixed':1})))
    def test_audio_hash_rejects_same_length_mutation(self):
        e=Engine();audio=np.zeros(8000,dtype=np.float32);e.segments=[torch.from_numpy(audio)]
        c=export_cut(e,frontier=8000,transcript='',contract={'fixed':1});audio[10]=1
        with self.assertRaises(ValueError):restore_cut(Engine(),c,audio=audio,contract={'fixed':1})
    def test_cached_execution_is_not_a_legal_cut(self):
        for field,value in [('kv_cache',{'hidden':1}),('dec_attns',[1])]:
            e=Engine();setattr(e,field,value)
            with self.subTest(field=field),self.assertRaises(ValueError):export_cut(e,frontier=0,transcript='',contract={})
        e=Engine();e.token_decoder.finished_sequences=[{(1,):1.0}]
        with self.assertRaises(ValueError):export_cut(e,frontier=0,transcript='',contract={})
    def test_external_snapshot_mutation_does_not_change_certificate(self):
        c=export_cut(Engine(),frontier=0,transcript='',contract={});before=c.sha256
        d=c.state;d['tokens'].append([[999]]);d['contract']['injected']=True
        self.assertEqual(c.sha256,before);self.assertNotIn('injected',c.state['contract'])
    def test_tokenizer_context_roundtrip_is_required(self):
        c=export_cut(Engine(),frontier=0,transcript='',contract={});d=c.state;d['context']['token_ids']=[999]
        from feedback_contract import FeedbackCut
        with self.assertRaises(ValueError):restore_cut(Engine(),FeedbackCut(d),audio=np.zeros(0,dtype=np.float32),contract={})

if __name__=='__main__':unittest.main()
