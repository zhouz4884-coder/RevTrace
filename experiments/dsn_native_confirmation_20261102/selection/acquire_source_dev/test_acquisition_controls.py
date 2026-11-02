"""Technical transport/header/independence controls; no network or models."""
from __future__ import annotations
import copy,io,pathlib,tempfile,unittest,wave,zipfile,importlib.util,zlib
from acquisition_common import (SPLIT_NAMESPACE,SPLIT_DIRECTORY,AcquisitionError,TechnicalHeaderError,IndependenceError,
    validate_metadata,inspect_pcm,check_duration,check_independence,original_reference_map)
from acquire_audio import member_bytes

def wavdata(frames=132000):
    raw=io.BytesIO()
    with wave.open(raw,'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\0\0'*frames)
    return raw.getvalue()
def entry(uid='BAC009S1000W0001'):
    return dict(source_id=uid,speaker_id=uid[6:11],path=SPLIT_DIRECTORY+'/'+uid+'.wav',method=8,bytes=264044,compressed=100,local_offset=0,crc32=0)
def metadata():
    e=entry();g=dict(source_id=e['source_id'],speaker_id=e['speaker_id'],archive_member=e,technical_header_fallback_order=[e,entry('BAC009S1000W0002')])
    return dict(status='PASS_STRICT_SAME_SPLIT_METADATA_SELECTION_PENDING_AUDIO',metadata_first=True,model_calls=0,new_reference_text_read=False,new_WAV_bytes_read=False,selected_speaker_count=1,selected_utterance_count=1,original_split=SPLIT_NAMESPACE,excluded_speakers=[],selected_sources=[g])

class Controls(unittest.TestCase):
    def test_dynamicN_and_cyclic_same_speaker_metadata(self):
        self.assertEqual(len(validate_metadata(metadata(),dict(split_namespace=SPLIT_NAMESPACE,duration_seconds=[8,9]),1)),1)
    def test_unfrozenN_or_wrong_split_rejected(self):
        m=metadata()
        with self.assertRaises(AcquisitionError):validate_metadata(m,dict(split_namespace=SPLIT_NAMESPACE,duration_seconds=[8,9]),2)
        m['original_split']=SPLIT_DIRECTORY
        with self.assertRaises(AcquisitionError):validate_metadata(m,dict(split_namespace=SPLIT_NAMESPACE,duration_seconds=[8,9]),1)
    def test_fallback_cannot_change_speaker(self):
        m=metadata();m['selected_sources'][0]['technical_header_fallback_order'][1]=entry('BAC009S1001W0001')
        with self.assertRaises(AcquisitionError):validate_metadata(m,dict(split_namespace=SPLIT_NAMESPACE,duration_seconds=[8,9]),1)
    def test_full_original_PCM_header_and_strict_duration(self):
        h=inspect_pcm(wavdata());check_duration(h);self.assertEqual(h['frames'],132000);self.assertEqual(h['duration'],8.25)
        for frames in (127999,144001):
            with self.assertRaises(TechnicalHeaderError):check_duration(inspect_pcm(wavdata(frames)))
    def test_crc_is_real_and_not_header_fallback(self):
        spec=importlib.util.spec_from_file_location('vendor1129',pathlib.Path(__file__).parent/'vendor'/'acquire_selected.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
        data=wavdata();buf=io.BytesIO();name=SPLIT_DIRECTORY+'/BAC009S1000W0001.wav'
        with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr(name,data)
        with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as z:info=z.getinfo(name)
        e=dict(path=name,method=8,compressed=info.compress_size,bytes=len(data),crc32=zlib.crc32(data))
        self.assertEqual(v.extract_member(buf.getvalue(),e),data);e['crc32']^=1
        with self.assertRaises(ValueError):v.extract_member(buf.getvalue(),e)
    def test_transport_CRC_retries_only_exact_member(self):
        class BadCRC:
            calls=[]
            @classmethod
            def request_member(cls,url,e):cls.calls.append(e['source_id']);return b'badCRC'
            @staticmethod
            def extract_member(raw,e):raise ValueError('CRC mismatch')
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);(root/'ranges').mkdir();attempts=[];e=entry()
            with self.assertRaises(AcquisitionError):member_bytes(dict(staged_ranges={},network_attempts_per_same_member=3),e,root,attempts,BadCRC)
        self.assertEqual(BadCRC.calls,[e['source_id']]*3);self.assertTrue(all(not r['header_fallback_authorized'] for r in attempts))
    def test_hash_collision_is_STOP_not_technical_fallback(self):
        with self.assertRaises(IndependenceError):check_independence('wav','pcm',{'pcm'},set())
        with self.assertRaises(IndependenceError):check_independence('wav','pcm',set(),{'wav'})
        self.assertFalse(issubclass(IndependenceError,TechnicalHeaderError))
    def test_original_reference_fields_unchanged_and_conflicts_stop(self):
        uid='BAC009S1000W0001';data=[dict(audio_path=uid+'.wav',text_zh='原  文')]
        self.assertEqual(original_reference_map(data,{uid})[uid],'原  文')
        self.assertNotIn('other',original_reference_map(data,{'other'}))
        with self.assertRaises(AcquisitionError):original_reference_map(data+[dict(audio_path=uid+'.wav',text_zh='改文')],{uid})

if __name__=='__main__':unittest.main()

