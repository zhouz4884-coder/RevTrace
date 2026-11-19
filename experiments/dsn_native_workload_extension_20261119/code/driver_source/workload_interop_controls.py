"""Cross-source synthetic WAV/tar preparation-to-service contract; no neural calls."""
from __future__ import annotations
import argparse,hashlib,importlib,io,json,pathlib,sys,tarfile,tempfile,wave
from unittest.mock import patch
from confirmation_common import verify_source,need,sha,put,NN4F
import corpus_contract as corpus
from make_workload_plan import freeze_cells
from run_workload_campaign import validate_cell
from ref_common import sources_from_receipt

PREP_COMMIT='dc43456e52568f3b2b5fa6a669a67586c3c91d92'

def run_fixture(prep_root):
    prep_root=pathlib.Path(prep_root).resolve()
    sys.path.insert(0,str(prep_root))
    prep=importlib.import_module('prepare_magicdata'); census=importlib.import_module('census')
    need(pathlib.Path(prep.__file__).resolve()==prep_root/'prepare_magicdata.py','wrong actual preparer module')
    with tempfile.TemporaryDirectory() as tmp:
        root=pathlib.Path(tmp);out=root/'preparation';out.mkdir();archive=root/'test_set.tar.gz'
        items=[];catalog={}
        for speaker,uid,frames in [('38_1','38_1_a',240000),('38_1','38_1_b',260000),
                                    ('38_2','38_2_a',192000),('38_3','38_3_a',320000)]:
            stream=io.BytesIO()
            with wave.open(stream,'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*frames)
            path=f'test/{speaker}/{uid}.wav';items.append((path,stream.getvalue()))
            catalog[uid+'.wav']=dict(speaker_id=speaker,metadata_path='wav/'+path)
        items.append(('test/TRANS.txt',b'38_1_a.wav\t38_1\t\xff\xfe\n'+
            '38_1_b.wav\t38_1\t原始 正文\n38_2_a\t第二来源\n38_3_a.wav\t38_3\t第三来源\n'.encode()))
        with tarfile.open(archive,'w:gz') as tar:
            for name,data in items:
                info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
        summary=census.scan_archive(archive,catalog,out,
            dict(maximum_tar_members=100,maximum_expanded_member_bytes=1024**3,maximum_single_WAV_bytes=10**7),lambda *a,**k:None)
        identity=dict(path=str(archive),sha256=sha(archive),bytes=archive.stat().st_size,official_url=prep.OFFICIAL_URL)
        frozen=prep.freeze_ids(out/'WAV_HEADERS.jsonl',out,identity,summary)
        sources,binding=prep.materialize_selected(archive,identity,frozen,out,
            dict(selected_audio_directory=str(root/'audio')),lambda *a,**k:None)
        receipt=dict(status=corpus.STATUS,corpus='MAGICDATA68',split='test',archive=identity,
            metadata_census=dict(path=str(out/'WAV_HEADERS.jsonl'),sha256=sha(out/'WAV_HEADERS.jsonl')),
            ids_frozen=dict(path=str(out/'IDS_FROZEN.json'),sha256=sha(out/'IDS_FROZEN.json')),transcript_binding=binding,
            metadata_first=True,model_calls=0,no_concat=True,no_trim=True,no_resample=True,
            requested_source_count=4,eligible_speaker_count=frozen['eligible_speaker_count'],
            selection_rule=prep.RULE,sources=sources)
        with patch.object(corpus,'B',root):
            checked=corpus.selected_md68_sources(receipt)
            need(checked==sources_from_receipt(receipt)==sources,'preparer/reference validator objects differ')
        need(len(sources)==3 and sources[0]['raw_source_id']=='38_1_b','actual eligible shortfall/nearest16s choice differs')
        warm=dict(source_id='fixed_original_warmup',path='unchanged')
        template=dict(settings=dict(source_commit=NN4F,corrector_dtype='float32',max_ahead_frames=32000,
            sources=[dict(source_id='old-test')],model_sources=[warm],
            warmup=dict(source_id=warm['source_id'],original_reference_start_state=dict(frontier=24000))))
        reference=dict(reference_details=dict(path='strict-details',sha256='d'*64),reference_gate=dict(path='strict-gate',sha256='g'*64))
        configs=root/'configs';configs.mkdir()
        cells,orders,warmup,warm_source=freeze_cells(template,checked,reference,configs,root/'raw')
        plan=dict(sources=checked,reference_details=reference['reference_details'],warmup=warmup,warmup_source=warm_source)
        for cell in cells:validate_cell(cell,json.loads(pathlib.Path(cell['config']).read_bytes()),plan,dict(source_commit=NN4F))
        need(len(cells)==18 and all('frames' in s and 'duration' in s for s in sources),'actual prepared source cannot enter unchanged original reference/service path')
        need('torch' not in sys.modules and 'transformers' not in sys.modules,'unexpected neural import')
        return dict(status='PASS_ACTUAL_PREPARER_TO_STRICT_REFERENCE_AND_18_SYNTHETIC_SERVICE_CONFIGS',
            source_count=3,synthetic_config_count=len(cells),model_calls=0,GPU_calls=0,
            unselected_invalid_UTF8_value_decoded=False,original_WAV_PCM_archive_and_labels_verified=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--prep-source',required=True);p.add_argument('--prep-manifest',required=True)
    a=p.parse_args();identity=verify_source(a.prep_source,a.prep_manifest,PREP_COMMIT)
    result=run_fixture(a.prep_source);result['actual_preparer']=identity
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
