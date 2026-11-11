"""Synthetic header/transport/archive controls; no corpus or model invocation."""
import gzip,io,pathlib,struct,tarfile,tempfile,types,unittest
from unittest.mock import patch
from census import CensusError,MemberReader,safe_name,wav_header,scan_archive,validate_response

def chunk(kind,body):return kind+struct.pack('<I',len(body))+body+(b'\0' if len(body)&1 else b'')
def wave(frames=100000,sr=16000,channels=1,bits=16,extra=b'',extensible=False):
    align=channels*((bits+7)//8);tag=65534 if extensible else 1
    fmt=struct.pack('<HHIIHH',tag,channels,sr,sr*align,align,bits)
    if extensible:fmt+=struct.pack('<HHI',22,bits,0)+bytes.fromhex('0100000000001000800000aa00389b71')
    else:fmt+=extra
    body=b'WAVE'+chunk(b'JUNK',b'odd')+chunk(b'fmt ',fmt)+chunk(b'data',b'\0'*(frames*align))+chunk(b'LIST',b'ignored')
    return b'RIFF'+struct.pack('<I',len(body))+body
def parse(raw):return wav_header(MemberReader(io.BytesIO(raw),len(raw)))
def make_tar(path,rows):
    with tarfile.open(path,'w:gz') as t:
        for name,raw,kind in rows:
            m=tarfile.TarInfo(name);m.size=len(raw);m.type=kind;t.addfile(m,io.BytesIO(raw) if kind==tarfile.REGTYPE else None)
def scan(path,catalog,out):
    out.mkdir();return scan_archive(path,catalog,out,dict(maximum_tar_members=100,maximum_expanded_member_bytes=1024**3,maximum_single_WAV_bytes=10**7),lambda *a,**k:None)

class HeaderControls(unittest.TestCase):
    def test_non44_header_unknown_odd_chunks_and_extended_fmt(self):
        r=parse(wave(extra=b'\0\0'));self.assertEqual(r['frames'],100000);self.assertEqual(r['duration_seconds'],6.25);self.assertEqual(r['stratum'],'6to12')
    def test_extensible_PCM_and_stratum_boundaries(self):
        self.assertEqual(parse(wave(frames=192000,extensible=True))['stratum'],'12to20')
        self.assertEqual(parse(wave(frames=320000))['stratum'],'12to20')
        self.assertIsNone(parse(wave(frames=320001))['stratum'])
    def test_stereo_and_other_sample_rate_are_not_silently_resampled(self):
        for args in (dict(channels=2),dict(sr=44100)):
            r=parse(wave(**args));self.assertFalse(r['compatible_original_input_format']);self.assertIsNone(r['stratum'])
    def test_truncated_and_oversized_RIFF_are_rejected(self):
        raw=wave()
        for bad in (raw[:-1],raw[:4]+struct.pack('<I',2**32-1)+raw[8:]):
            with self.assertRaises(CensusError):parse(bad)
    def test_duplicate_data_or_bad_alignment_is_rejected(self):
        raw=wave();body=raw[8:]+chunk(b'data',b'\0\0');bad=b'RIFF'+struct.pack('<I',len(body))+body
        with self.assertRaisesRegex(CensusError,'ambiguous_data'):parse(bad)
    def test_paths_cannot_escape_or_mix_splits(self):
        for name in ('../x.wav','/tmp/x.wav','C:/x.wav','test\\x.wav','wav/train/a.wav','dev/a.wav'):
            with self.assertRaises(CensusError):safe_name(name)
    def test_test_only_full_pipeline_counts_alias_once_and_never_opens_TRANS(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);a=root/'tiny.gz';make_tar(a,[('test/s1/a.wav',wave(),tarfile.REGTYPE),('test/s2/b.wav',wave(frames=192000),tarfile.REGTYPE),('test/TRANS.txt',b'NO_REFERENCE_ACCESS',tarfile.REGTYPE)])
            original=tarfile.TarFile.extractfile
            def guarded(obj,member):
                self.assertFalse(member.name.endswith('TRANS.txt'));return original(obj,member)
            with patch.object(tarfile.TarFile,'extractfile',guarded):
                r=scan(a,{'a.wav':dict(speaker_id='s1',metadata_path='wav/test/s1/a.wav'),'b.wav':dict(speaker_id='s2',metadata_path='wav/test/s2/b.wav')},root/'out')
            self.assertEqual(r['WAV_members'],2);self.assertEqual(r['potential_speakers_by_stratum'],{'6to12':1,'12to20':1});self.assertEqual(r['selection_status'],'NO_SPEAKERS_OR_UTTERANCES_SELECTED')
    def test_missing_member_and_speaker_mismatch_fail_census(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);a=root/'tiny.gz';make_tar(a,[('test/s1/a.wav',wave(),tarfile.REGTYPE)])
            for index,cat in enumerate(({'a.wav':dict(speaker_id='s2',metadata_path='x')},{'a.wav':dict(speaker_id='s1',metadata_path='x'),'b.wav':dict(speaker_id='s2',metadata_path='x')})):
                with self.assertRaises(CensusError):scan(a,cat,root/str(index))
    def test_symlink_member_is_never_extracted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);a=root/'tiny.gz';make_tar(a,[('test/link',b'',tarfile.SYMTYPE)])
            with self.assertRaisesRegex(CensusError,'special_tar'):scan(a,{},root/'out')
    def test_full_gzip_EOF_detects_crc_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);a=root/'tiny.gz';make_tar(a,[('test/s1/a.wav',wave(),tarfile.REGTYPE)])
            raw=bytearray(a.read_bytes());raw[-8]^=1;a.write_bytes(raw)
            with self.assertRaises((gzip.BadGzipFile,EOFError)):scan(a,{'a.wav':dict(speaker_id='s1',metadata_path='x')},root/'out')
    def test_resume_requires_matching_range_size_ETag_and_URL(self):
        cfg=dict(archive_bytes=10,allowed_archive_urls=['https://official/test'],expected_ETag='pinned')
        good=types.SimpleNamespace(status=206,url='https://official/test',headers={'Content-Length':'6','Content-Range':'bytes 4-9/10','ETag':'pinned'})
        validate_response(good,4,cfg)
        for change in ({'status':200},{'url':'https://other/test'},{'headers':dict(good.headers,**{'ETag':'changed'})}):
            bad=types.SimpleNamespace(**dict(vars(good),**change))
            with self.assertRaises(CensusError):validate_response(bad,4,cfg)
    def test_member_hash_covers_original_bytes_without_decoding(self):
        import hashlib
        raw=wave();reader=MemberReader(io.BytesIO(raw),len(raw));wav_header(reader);reader.drain();self.assertEqual(reader.h.hexdigest(),hashlib.sha256(raw).hexdigest())

if __name__=='__main__':unittest.main()
