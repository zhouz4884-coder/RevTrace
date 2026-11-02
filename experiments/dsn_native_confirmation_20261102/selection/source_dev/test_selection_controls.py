"""Metadata-only controls. No historical corpus/model/remote calls."""
import copy,io,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from metadata_census import inspect_object,extract_lineage,catalog_file,metadata_tier,resolve_lineage
from freeze_candidates import member_pool,choose
from selection_common import SelectionError,MemoryPath,put,sha

def member(speaker,number,seconds=8.5):
    uid=f'BAC009{speaker}W{number:04d}'
    return dict(path='StreamCorrect/aishell1_testset/'+uid+'.wav',bytes=44+round(seconds*32000),
                crc32=number,compressed=1000,local_offset=number*2000,method=8)
def rule():
    return dict(duration_seconds=[8,9],member_prefix='StreamCorrect/aishell1_testset/',seed=2026110241,target_speakers_maximum=12)

class Controls(unittest.TestCase):
    def test_catalog_pool_is_not_historical_model_usage(self):
        data=dict(eligible_pool=[dict(source_id='BAC009S0914W0001',speaker_id='S0914')],
                  selected=[dict(source_id='BAC009S0908W0369',speaker_id='S0908')])
        speakers={s for row in inspect_object(data) for s in row['speaker_ids']}
        self.assertEqual(speakers,{'S0908'})
        self.assertTrue(catalog_file('/old/ARCHIVE_ENTRIES_0.json'))
        self.assertTrue(catalog_file('/old/reference.json'))
        self.assertTrue(catalog_file('/old/public_asset_metadata_v3/SUMMARY.json'))

    def test_technical_fallback_list_does_not_count_as_used(self):
        data=dict(source_id='BAC009S0908W0369',technical_fallback_order=[dict(source_id='BAC009S0914W0001')])
        self.assertEqual({u for row in inspect_object(data) for u in row['utterance_ids']},{'BAC009S0908W0369'})

    def test_concatenated_alias_excludes_all_recorded_component_speakers(self):
        data=dict(source_id='chinese-00',path='/old/chinese-00.wav',language='Chinese',
                  sources=[dict(sample_id='aishell-BAC009S0726W0423',path='/old/BAC009S0726W0423.wav'),
                           dict(sample_id='aishell-BAC009S0740W0330',path='/old/BAC009S0740W0330.wav')])
        parent=next(row for row in extract_lineage(data) if row['pointer']=='$')
        self.assertEqual(set(parent['speaker_ids']),{'S0726','S0740'})

    def test_WAV_and_PCM_keys_are_preserved_not_assumed_same_encoding(self):
        data=dict(source_id='BAC009S0908W0369',audio_sha256='a'*64,header=dict(PCM_sha256='b'*64))
        keys={key for row in inspect_object(data) for key in row['audio_hashes']}
        self.assertEqual(keys,{'audio_sha256','PCM_sha256'})

    def test_exclusion_is_at_speaker_not_only_utterance(self):
        entries=[member('S0914',1),member('S0914',2),member('S0915',1)]
        self.assertEqual(set(member_pool(entries,{'S0914'},rule())),{'S0915'})

    def test_full_original_duration_band_never_trimmed_or_silently_widened(self):
        entries=[member('S0914',1,7.99),member('S0914',2,8),member('S0915',1,9),member('S0915',2,9.01)]
        pool=member_pool(entries,set(),rule())
        self.assertEqual([row['source_id'] for rows in pool.values() for row in rows],['BAC009S0914W0002','BAC009S0915W0001'])

    def test_budget12_is_not_fabricated_when_only_two_speakers_exist(self):
        pool=member_pool([member('S0914',1),member('S0914',2),member('S0915',1)],set(),rule())
        selected=choose(pool,rule())
        self.assertEqual(len(selected),2)
        self.assertEqual(len({row['speaker_id'] for row in selected}),2)
        self.assertTrue(all(row['audio_sha256'] is None for row in selected))

    def test_fixed_seed_and_no_model_result_selection(self):
        entries=[member('S0914',i) for i in range(1,5)]+[member('S0915',i) for i in range(1,5)]
        left=choose(member_pool(entries,set(),rule()),rule())
        changed=copy.deepcopy(entries)
        for i,row in enumerate(changed):row.update(CER=100-i,latency=100+i,compatibility=(i%2==0))
        right=choose(member_pool(changed,set(),rule()),rule())
        self.assertEqual([(r['speaker_id'],r['source_id']) for r in left],[(r['speaker_id'],r['source_id']) for r in right])

    def test_different_split_not_merged_to_fill_budget(self):
        entry=member('S0914',1);other=member('S0010',1);other['path']=other['path'].replace('aishell1_testset','aishell1_trainset')
        self.assertEqual(set(member_pool([entry,other],set(),rule())),{'S0914'})

    def test_conflicting_original_member_stops(self):
        one=member('S0914',1);two=dict(one,crc32=999)
        with self.assertRaises(SelectionError):member_pool([one,two],set(),rule())

    def test_recorded_execution_and_frozen_plan_are_not_same_evidence_tier(self):
        self.assertEqual(metadata_tier('/results/cells/run/CONFIG.json'),'recorded_case_config')
        self.assertEqual(metadata_tier('/old/PLAN_FROZEN.json'),'frozen_selection_or_plan')

    def test_exact_path_hash_lineage_resolves_across_multiple_metadata_hops(self):
        def record(path,hashes,speakers,origin):
            return dict(audio_paths=[path],audio_hashes=hashes,speaker_ids=speakers,utterance_ids=[],source_aliases=[],origin_sha256=origin)
        rows=[record('/old/a.wav',{'audio_sha256':'a'*64},[],'1'),
              record('/old/b.wav',{'audio_sha256':'a'*64},[],'2'),
              record('/old/b.wav',{},['S0914'],'3')]
        resolved=resolve_lineage(rows)
        self.assertTrue(all(row['speaker_ids']==['S0914'] for row in resolved))

    def test_generic_source0_alias_does_not_join_unrelated_files(self):
        rows=[dict(audio_paths=[],audio_hashes={},speaker_ids=[speaker],utterance_ids=[],source_aliases=['source0'],origin_sha256=origin)
              for speaker,origin in [('S0914','a'),('S0915','b')]]
        resolved=resolve_lineage(rows)
        self.assertEqual(resolved[0]['speaker_ids'],['S0914'])
        self.assertEqual(resolved[1]['speaker_ids'],['S0915'])

    def test_RAM_stream_bundle_preserves_exact_file_bytes_and_hashes(self):
        memory=MemoryPath('/media/user/experiment/selection_census');memory.mkdir()
        obj=dict(label='原始元数据',destination=str(memory),model_calls=0)
        put(memory/'CONFIG.json',obj)
        with (memory/'OBSERVATIONS.jsonl').open('x',encoding='utf8',newline='\n') as stream:stream.write('{"speaker_id":"S0914"}\n')
        with tempfile.TemporaryDirectory() as tmp:
            real=Path(tmp)
            put(real/'CONFIG.json',obj)
            with (real/'OBSERVATIONS.jsonl').open('x',encoding='utf8',newline='\n') as stream:stream.write('{"speaker_id":"S0914"}\n')
            packed=memory.zip_bytes()
            self.assertEqual(packed,memory.zip_bytes())
            with zipfile.ZipFile(io.BytesIO(packed)) as archive:
                for name in ['CONFIG.json','OBSERVATIONS.jsonl']:
                    self.assertEqual(archive.read(name),(real/name).read_bytes())
                    self.assertEqual(sha(memory/name),sha(real/name))

    def test_RAM_stream_keeps_POSIX_root_and_never_writes_local_files(self):
        with (patch.object(Path,'open',side_effect=AssertionError('local file write/read forbidden')),
              patch.object(Path,'mkdir',side_effect=AssertionError('local directory forbidden'))):
            memory=MemoryPath('/media/user/disk/results/local_history');memory.mkdir()
            self.assertEqual(str(memory),'/media/user/disk/results/local_history')
            put(memory/'RUN_RECORD.json',dict(raw_result_location=str(memory),actual_execution='Windows'))
            self.assertEqual(str(memory/'RUN_RECORD.json'),'/media/user/disk/results/local_history/RUN_RECORD.json')
            self.assertTrue(memory.zip_bytes().startswith(b'PK'))

if __name__=='__main__':unittest.main(verbosity=2)
