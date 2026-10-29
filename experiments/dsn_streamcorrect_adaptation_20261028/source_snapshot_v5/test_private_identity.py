import types,unittest,torch
from native_bridge import identity_prediction
class Tokenizer:
    def decode(self,ids):return ''.join(chr(x) for x in ids)
class Prediction(unittest.TestCase):
    def test_prediction_uses_actual_first_beam_without_future_selection(self):
        engine=types.SimpleNamespace(tokenizer=Tokenizer());tokens=torch.tensor([[1,2,3,4,*map(ord,'你好')],[1,2,3,4,*map(ord,'你们')]])
        x=identity_prediction(engine,input_audio=None,current_tokens=tokens,token_len_before_decoding=5)
        self.assertEqual(x['previous_transcription'],'你');self.assertEqual(x['corrected_appended_text'],'好')
        self.assertEqual(x['candidates'],['你好']);self.assertTrue(x['private_identity_prediction'])
    def test_empty_first_beam_continuation_is_not_replaced_with_an_alternative(self):
        engine=types.SimpleNamespace(tokenizer=Tokenizer());tokens=torch.tensor([[1,2,3,4,*map(ord,'你')]])
        x=identity_prediction(engine,input_audio=None,current_tokens=tokens,token_len_before_decoding=5)
        self.assertEqual(x['corrected_appended_text'],'')
    def test_unrepresentable_prefix_stops_instead_of_manufacturing_same_root(self):
        class Broken:
            def decode(self,ids):return '甲' if len(ids)==1 else '乙丙'
        engine=types.SimpleNamespace(tokenizer=Broken());tokens=torch.tensor([[1,2,3,4,5,6]])
        with self.assertRaises(ValueError):identity_prediction(engine,input_audio=None,current_tokens=tokens,token_len_before_decoding=5)
if __name__=='__main__':unittest.main()
