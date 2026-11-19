"""CPU synthetic controls for deterministic original-audio selection and binding."""
import hashlib,io,json,pathlib,tarfile,tempfile,types,unittest
from unittest.mock import patch
from census import CensusError,sha
from test_census import make_tar,wave,scan
from prepare_magicdata import RULE,OFFICIAL_URL,acquire_archive,freeze_ids,materialize_selected,pcm_identity,select_metadata,selected_label,write_new

def row(sid,uid,frames=256000,good=True):
    return dict(utterance_id=uid,speaker_id=sid,frames=frames,header_status='valid_RIFF',compatible_original_input_format=good,
                tar_path=f'test/{sid}/{uid}.wav',metadata_path=f'wav/test/{sid}/{uid}.wav',WAV_bytes=44+frames*2,WAV_sha256='x')

class SelectionControls(unittest.TestCase):
    def test_speakers_sorted_then_nearest_target_not_global_longest(self):
        rows=[row('38_6','38_6_a'),row('38_2','38_2_b',256010),row('38_2','38_2_a',255990),
              row('38_1','38_1_b',256001),row('38_1','38_1_a',256002),row('38_3','38_3_a'),row('38_4','38_4_a'),row('38_5','38_5_a')]
        selected,n=select_metadata(rows);self.assertEqual(n,6)
        self.assertEqual([r['raw_source_id'] for r in selected],['38_1_b','38_2_a','38_3_a','38_4_a'])
        self.assertEqual(selected[0]['speaker_id'],'MD68_38_1')
    def test_inclusive_original_long_boundaries_and_no_format_relaxation(self):
        rows=[row('38_1','38_1_a',192000),row('38_2','38_2_a',320000),row('38_3','38_3_a',191999),
              row('38_4','38_4_a',320001),row('38_5','38_5_a',256000,False)]
        selected,n=select_metadata(rows);self.assertEqual(n,2);self.assertEqual(len(selected),2)
    def test_no_eligible_is_preserved_and_no_reference_tiebreak(self):
        self.assertEqual(select_metadata([]),([],0))
        rows=[dict(row('38_1','38_1_b'),reference='better'),dict(row('38_1','38_1_a'),reference='worse')]
        selected,n=select_metadata(rows);self.assertEqual(selected[0]['raw_source_id'],'38_1_a')
    def test_duplicate_id_or_changed_rule_fails(self):
        r=row('38_1','38_1_a')
        with self.assertRaises(CensusError):select_metadata([r,r])
        with self.assertRaises(CensusError):select_metadata([r],dict(RULE,requested_speakers=8))
    def test_pcm_hash_excludes_container_chunks_but_original_hash_covers_them(self):
        raw=wave(frames=192000);header,digest=pcm_identity(raw)
        self.assertEqual(header['frames'],192000);self.assertEqual(digest,hashlib.sha256(b'\0'*384000).hexdigest())
        self.assertNotEqual(digest,hashlib.sha256(raw).hexdigest())
    def test_label_lookup_does_not_decode_unselected_text(self):
        self.assertIsNone(selected_label(b'other.wav\t\xff\xfe\n',{'38_1_a'}))
        self.assertEqual(selected_label('38_1_a.wav\t38_1\t原始 文本\n'.encode(),{'38_1_a'}),('38_1_a','原始 文本'))
        self.assertEqual(selected_label('38_1_a\t原始 文本\n'.encode(),{'38_1_a'}),('38_1_a','原始 文本'))
    def test_missing_selected_label_is_failure(self):
        with self.assertRaises(CensusError):selected_label(b'38_1_a.wav\n',{'38_1_a'})
    def test_complete_census_then_IDs_then_only_selected_label_original_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=pathlib.Path(tmp);archive=base/'original.gz';out=base/'out'
            a,b=wave(frames=240000),wave(frames=260000)
            rows=[('test/38_1/38_1_a.wav',a,tarfile.REGTYPE),('test/38_1/38_1_b.wav',b,tarfile.REGTYPE),
                  ('test/TRANS.txt','38_1_a.wav\t38_1\t未选择\n38_1_b.wav\t38_1\t原始 正文\n'.encode(),tarfile.REGTYPE)]
            make_tar(archive,rows)
            cat={uid+'.wav':dict(speaker_id='38_1',metadata_path=f'wav/test/38_1/{uid}.wav') for uid in ('38_1_a','38_1_b')}
            original=tarfile.TarFile.extractfile
            def guard(obj,member):
                if member.name.endswith('TRANS.txt'):self.assertTrue((out/'IDS_FROZEN.json').exists())
                return original(obj,member)
            with patch.object(tarfile.TarFile,'extractfile',guard):
                summary=scan(archive,cat,out);identity=dict(path=str(archive),sha256=sha(archive),bytes=archive.stat().st_size,official_url='synthetic')
                frozen=freeze_ids(out/'WAV_HEADERS.jsonl',out,identity,summary)
                sources,binding=materialize_selected(archive,identity,frozen,out,dict(selected_audio_directory=str(base/'audio')),lambda *a,**k:None)
            self.assertEqual(len(sources),1);s=sources[0];self.assertEqual(s['source_id'],'MD68_38_1_b')
            self.assertEqual(s['reference'],'原始 正文');self.assertEqual(pathlib.Path(s['path']).read_bytes(),b)
            self.assertEqual(s['archive_member']['sha256'],hashlib.sha256(b).hexdigest());self.assertEqual(s['split_directory'],'test')
            bound=json.loads(pathlib.Path(binding['path']).read_bytes());self.assertEqual(bound['ids_frozen_sha256'],sha(out/'IDS_FROZEN.json'))
            self.assertEqual(bound['selected']['38_1_b']['text'],s['reference'])
            raw_ids=(out/'IDS_FROZEN.json').read_text();self.assertNotIn('原始',raw_ids);self.assertNotIn('reference',raw_ids)
    def test_incomplete_census_cannot_write_selected_IDs(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp);(p/'rows').write_text('')
            with self.assertRaises(CensusError):freeze_ids(p/'rows',p,dict(sha256='x'),dict(WAV_members=1,all_expected_WAVs_present=False))
            self.assertFalse((p/'IDS_FROZEN.json').exists())
    def test_written_IDs_are_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp)/'IDS_FROZEN.json';write_new(p,dict(selected_source_ids=[]))
            with self.assertRaises(FileExistsError):write_new(p,dict(selected_source_ids=['changed']))

class AssetControls(unittest.TestCase):
    def config(self,path):
        return dict(experiment_id='synthetic',archive_path=str(path),archive_bytes=10,archive_url=OFFICIAL_URL,
            allowed_archive_urls=[OFFICIAL_URL],expected_ETag='fixed',maximum_download_attempts=2)
    def test_existing_original_asset_verified_without_network_or_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=pathlib.Path(tmp);a=base/'test_set.tar.gz';a.write_bytes(b'0123456789');out=base/'out';out.mkdir()
            with patch('prepare_magicdata.OFFICIAL_BYTES',10),patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')):
                path,identity=acquire_archive(self.config(a),out,lambda *a,**k:None)
            self.assertEqual(path.read_bytes(),b'0123456789');self.assertEqual(identity['sha256'],sha(a))
    def test_existing_wrong_size_is_preserved_and_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=pathlib.Path(tmp);a=base/'test_set.tar.gz';a.write_bytes(b'wrong');out=base/'out';out.mkdir()
            with patch('prepare_magicdata.OFFICIAL_BYTES',10),self.assertRaisesRegex(CensusError,'archive_size'):
                acquire_archive(self.config(a),out,lambda *a,**k:None)
            self.assertEqual(a.read_bytes(),b'wrong')
    def test_simulated_HTTP_stream_sanitizes_headers_and_preserves_transport(self):
        class Response(io.BytesIO):
            status=200;url=OFFICIAL_URL
            headers={'Content-Length':'10','ETag':'fixed','Set-Cookie':'secret-not-retained'}
        with tempfile.TemporaryDirectory() as tmp:
            base=pathlib.Path(tmp);a=base/'test_set.tar.gz';out=base/'out';out.mkdir()
            with patch('prepare_magicdata.OFFICIAL_BYTES',10),patch('urllib.request.urlopen',return_value=Response(b'0123456789')):
                _,identity=acquire_archive(self.config(a),out,lambda *a,**k:None)
            self.assertEqual(a.read_bytes(),b'0123456789');self.assertTrue(pathlib.Path(identity['preserved_transport_path']).exists())
            self.assertNotIn('secret-not-retained',(out/'DOWNLOAD_ATTEMPTS.json').read_text())
    def test_simulated_resume_uses_exact_range_and_ETag(self):
        class Response(io.BytesIO):
            status=206;url=OFFICIAL_URL
            headers={'Content-Length':'6','Content-Range':'bytes 4-9/10','ETag':'fixed'}
        with tempfile.TemporaryDirectory() as tmp:
            base=pathlib.Path(tmp);a=base/'test_set.tar.gz';a.with_name(a.name+'.part.synthetic').write_bytes(b'0123');out=base/'out';out.mkdir()
            def opening(req,**kwargs):
                self.assertEqual(req.get_header('Range'),'bytes=4-');return Response(b'456789')
            with patch('prepare_magicdata.OFFICIAL_BYTES',10),patch('urllib.request.urlopen',side_effect=opening):
                acquire_archive(self.config(a),out,lambda *a,**k:None)
            self.assertEqual(a.read_bytes(),b'0123456789')

if __name__=='__main__':unittest.main()
