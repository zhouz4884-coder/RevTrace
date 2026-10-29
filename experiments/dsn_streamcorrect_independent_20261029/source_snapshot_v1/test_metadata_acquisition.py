import copy,io,struct,unittest,wave,zipfile,zlib
from select_metadata import choose
from acquire_selected import extract_member,inspect_wave
def entries(high=8.5):
    return [dict(path=f'StreamCorrect/aishell1_testset/BAC009S{i:04d}W{j:04d}.wav',bytes=int(high*32000)+44,compressed=123,local_offset=i*1000+j,method=8,crc32=123) for i in range(1,7) for j in range(1,4)]
class SelectionTests(unittest.TestCase):
    def test_deterministic_four_unique_speakers(self):
        a=choose(entries(),seed=2026102931,excluded={'S0001'});b=choose(entries(),seed=2026102931,excluded={'S0001'})
        self.assertEqual(a,b);self.assertEqual(len(a['selected']),4);self.assertNotIn('S0001',{x['speaker_id'] for x in a['selected']})
    def test_prefer_initial_band(self):self.assertEqual(choose(entries(),seed=1,excluded=set())['selected_estimated_duration_band'],[8,9])
    def test_single_widen_to10(self):self.assertEqual(choose(entries(9.5),seed=1,excluded=set())['selected_estimated_duration_band'],[8,10])
    def test_widen_to15(self):self.assertEqual(choose(entries(12),seed=1,excluded=set())['selected_estimated_duration_band'],[8,15])
    def test_no_data_dependent_unbounded_widen(self):
        with self.assertRaises(ValueError):choose(entries(16),seed=1,excluded=set())
    def test_no_transcript_or_quality_selection(self):
        a=entries();b=copy.deepcopy(a)
        for i,r in enumerate(b):r.update(text_zh='x'*i,model_CER=i/100,compatible=i%2)
        ids=lambda rows:[r['initial_source_id'] for r in choose(rows,seed=4,excluded=set())['selected']]
        self.assertEqual(ids(a),ids(b))
    def test_fallback_is_fixed_rotation_same_speaker(self):
        for g in choose(entries(),seed=3,excluded=set())['selected']:
            self.assertEqual(len(g['technical_fallback_order']),3)
            self.assertEqual(g['technical_fallback_order'][0]['source_id'],g['initial_source_id'])
            self.assertEqual({x['speaker_id'] for x in g['technical_fallback_order']},{g['speaker_id']})
class BytesTests(unittest.TestCase):
    def wav(self,channels=1,rate=16000,seconds=8.5):
        b=io.BytesIO()
        with wave.open(b,'wb') as w:w.setnchannels(channels);w.setsampwidth(2);w.setframerate(rate);w.writeframes(b'\0'*(int(seconds*rate)*2*channels))
        return b.getvalue()
    def zip(self):
        data=self.wav();b=io.BytesIO();name='StreamCorrect/aishell1_testset/BAC009S0001W0001.wav'
        with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_STORED) as z:z.writestr(name,data)
        with zipfile.ZipFile(b) as z:i=z.infolist()[0];entry=dict(path=name,method=i.compress_type,compressed=i.compress_size,bytes=i.file_size,crc32=i.CRC)
        return b.getvalue(),entry,data
    def test_zip_crc_and_exact_WAV(self):
        raw,e,data=self.zip();self.assertEqual(extract_member(raw,e),data);self.assertEqual(inspect_wave(data)['frames'],136000)
    def test_corrupt_payload_does_not_trigger_source_reselection(self):
        raw,e,_=self.zip();p=30+len(e['path'].encode())+100;bad=raw[:p]+bytes([raw[p]^1])+raw[p+1:]
        with self.assertRaises(ValueError):extract_member(bad,e)
    def test_wrong_archive_name(self):
        raw,e,_=self.zip();e['path']+='x'
        with self.assertRaises(ValueError):extract_member(raw,e)
    def test_reject_stereo_no_resample(self):
        with self.assertRaises(ValueError):inspect_wave(self.wav(channels=2))
    def test_reject_wrong_rate_no_resample(self):
        with self.assertRaises(ValueError):inspect_wave(self.wav(rate=8000))
    def test_reference_generator_duration_boundary(self):
        with self.assertRaises(ValueError):inspect_wave(self.wav(seconds=7.9))
if __name__=='__main__':unittest.main()
