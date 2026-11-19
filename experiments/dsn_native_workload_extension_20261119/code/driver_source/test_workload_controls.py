"""Real synthetic WAV/tar receipts and controller mutation controls; CPU only."""
import copy,hashlib,io,json,pathlib,sys,tarfile,tempfile,unittest,wave
from unittest.mock import patch
import corpus_contract as corpus
from confirmation_common import GateError,canonical,sha,put,selected_sources
from ref_common import sources_from_receipt
from workload_conditions import CONDITIONS,CONDITION_SETTINGS,workload_blocks,validate_matrix
from make_workload_plan import freeze_cells,main as make_plan_main
from run_workload_campaign import aggregate,validate_cell
from confirmation_common import NN4F

def digest(data):return hashlib.sha256(data).hexdigest()

def fixture(root, speakers=4):
    root=pathlib.Path(root); rows=[]; files={}; source_map={}
    specs=[('A','a14',224000),('A','a16',256000),('B','b15',240000),('B','b17',272000),
           ('C','c12',192000),('D','d20',320000),('E','e16',256000)]
    allowed=set('ABCDE'[:speakers])
    for spk,uid,frames in specs:
        if spk not in allowed:continue
        stream=io.BytesIO()
        with wave.open(stream,'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\x01\x00'*frames)
        data=stream.getvalue(); p=root/(uid+'.wav');p.write_bytes(data)
        path=f'test/{spk}/{uid}.wav'; files[path]=data
        rows.append(dict(utterance_id=uid,speaker_id=spk,tar_path=path,metadata_path=path,
            WAV_bytes=len(data),WAV_sha256=digest(data),header_status='valid_RIFF',compatible_original_input_format=True,
            sample_rate=16000,channels=1,bits_per_sample=16,frames=frames,duration_seconds=frames/16000))
        source_map[uid]=(p,data)
    transcript='\n'.join(f'{r["utterance_id"]}.wav\t{r["speaker_id"]}\t测试{r["utterance_id"]}' for r in rows)+'\n'
    files['test/TRANS.txt']=transcript.encode()
    tarpath=root/'test_set.tar.gz'
    with tarfile.open(tarpath,'w:gz') as tar:
        for name,data in files.items():
            info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
    census=root/'WAV_HEADERS.jsonl';census.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf8')
    chosen,eligible=corpus.metadata_choice(rows)
    frozen=[];sources=[];selected={}
    trans_member=dict(path='test/TRANS.txt',bytes=len(files['test/TRANS.txt']),sha256=digest(files['test/TRANS.txt']))
    for r in chosen:
        uid=r['utterance_id'];spk=r['speaker_id'];p,data=source_map[uid]
        fr=copy.deepcopy(r);fr.update(raw_source_id=uid,raw_speaker_id=spk,source_id='MD68_'+uid,speaker_id='MD68_'+spk)
        frozen.append(fr)
        text='测试'+uid;raw=f'{uid}.wav\t{spk}\t{text}'.encode()
        selected[uid]=dict(text=text,archive_member=trans_member,layout='key_speaker_text',raw_row_sha256=digest(raw))
        sources.append(dict(source_id='MD68_'+uid,speaker_id='MD68_'+spk,raw_source_id=uid,raw_speaker_id=spk,
            path=str(p),reference=text,frames=r['frames'],duration=r['duration_seconds'],audio_sha256=digest(data),
            original_split='MD68/test@'+sha(tarpath),split_directory='test',
            archive_member=dict(path=r['tar_path'],bytes=len(data),sha256=digest(data)),
            header=dict(sample_rate=16000,channels=1,sample_width=2,frames=r['frames'],PCM_sha256=digest(b'\x01\x00'*r['frames']))))
    ids=root/'IDS_FROZEN.json';put(ids,dict(corpus=corpus.CORPUS,split='test',metadata_first=True,
        access_phase='ID_SELECTION_COMPLETE_BEFORE_LABEL_ACCESS',model_calls=0,selected_source_ids=[s['source_id'] for s in sources],
        selected=frozen,selection_rule=corpus.RULE,full_census_sha256=sha(census),archive_sha256=sha(tarpath)))
    labels=root/'SELECTED_TRANSCRIPTS.json';put(labels,dict(ids_frozen_sha256=sha(ids),model_calls=0,selected=selected))
    receipt=dict(status=corpus.STATUS if sources else corpus.NO_GO,corpus=corpus.CORPUS,split='test',
        metadata_first=True,model_calls=0,no_concat=True,no_trim=True,no_resample=True,
        requested_source_count=4,selection_rule=corpus.RULE,eligible_speaker_count=eligible,
        archive=dict(path=str(tarpath),bytes=tarpath.stat().st_size,sha256=sha(tarpath),
            official_url='https://openslr.magicdatatech.com/resources/68/test_set.tar.gz'),
        metadata_census=dict(path=str(census),sha256=sha(census)),
        ids_frozen=dict(path=str(ids),sha256=sha(ids)),transcript_binding=dict(path=str(labels),sha256=sha(labels)),sources=sources)
    return receipt

def cell_matrix(sources):
    cells=[]
    for block in workload_blocks(sources)[0]:
        for condition in block['conditions']:
            arm,retain=CONDITION_SETTINGS[condition];n=len(cells);s=block['source']
            cells.append(dict(cell_id='cell'+str(n),source_id=s['source_id'],speaker_id=s['speaker_id'],
                condition=condition,strategy=arm,consumer_retain_views=retain,repeat=block['repeat'],
                primary_gpu=block['primary_gpu'],position=n,config='cfg'+str(n),out='out'+str(n),
                log='log'+str(n),external_power='pwr'+str(n)))
    return cells

def synthetic_results(sources):
    result=[]
    for c in cell_matrix(sources):
        credit={'conservative_s1':5.,'r1s0':10.,'r1s1':9.}[c['condition']]
        result.append(dict(c,primary=dict(offered_audio_seconds=next(s['frames']/16000 for s in sources if s['source_id']==c['source_id']),
            dual_deadline_audio_credit_seconds=credit,complete_coverage_and_original_quantile_pass=False,
            D2_misses_all_offered=1,C8_misses_all_offered=0),worker_ledger=dict(worker_seconds=20.),
            common_external_energy=dict(origin_to_confirmed_physical_model_drain=dict(total_joules=100.)),
            view_audit=dict(continuity=dict(avoidable_withdrawals=int(c['condition']=='r1s0'),
                necessary_withdrawals=0,unknown_withdrawals=0,gap_right_censored_windows=1,
                total_gap_audio_seconds_x_wall_seconds=1.,same_root_avoidable_gap_audio_seconds_x_wall_seconds=.5))))
    return result

class CorpusControls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
        self.disk=patch.object(corpus,'B',self.root);self.disk.start();self.receipt=fixture(self.root)
    def tearDown(self):self.disk.stop();self.tmp.cleanup()
    def test_full_archive_pcm_label_binding_and_both_entry_points(self):
        expected=self.receipt['sources']
        self.assertEqual(corpus.selected_md68_sources(self.receipt),expected)
        self.assertEqual(selected_sources(self.receipt,4),expected)
        self.assertEqual(sources_from_receipt(self.receipt),expected)
        self.assertEqual([s['raw_source_id'] for s in expected],['a16','b15','c12','d20'])
    def test_repeated_or_wrong_speaker_member_rejected(self):
        for key,value in [('raw_speaker_id','B'),('speaker_id','MD68_B')]:
            r=copy.deepcopy(self.receipt);r['sources'][0][key]=value
            with self.assertRaises(GateError):corpus.selected_md68_sources(r)
        r=copy.deepcopy(self.receipt);r['sources'][0]['archive_member']['path']='test/B/a16.wav'
        with self.assertRaises(GateError):corpus.selected_md68_sources(r)
    def test_model_boolean_missing_or_nonzero_not_zero(self):
        for value in (False,None,1):
            r=copy.deepcopy(self.receipt);r['model_calls']=value
            with self.assertRaises(GateError):corpus.selected_md68_sources(r)
    def test_cropped_or_reencoded_audio_rejected(self):
        r=copy.deepcopy(self.receipt);r['no_trim']=False
        with self.assertRaises(GateError):corpus.selected_md68_sources(r)
        r=copy.deepcopy(self.receipt);r['sources'][0]['header']['PCM_sha256']='0'*64
        with self.assertRaises(GateError):corpus.selected_md68_sources(r)
        p=pathlib.Path(r['sources'][0]['path']);p.write_bytes(p.read_bytes()+b'x')
        with self.assertRaises(GateError):corpus.selected_md68_sources(self.receipt)
    def test_archive_or_census_mutation_rejected(self):
        for key in ('archive','metadata_census'):
            r=copy.deepcopy(self.receipt);r[key]['sha256']='0'*64
            with self.assertRaises(GateError):corpus.selected_md68_sources(r)
    def test_labels_before_freeze_and_late_label_binding_rejected(self):
        p=pathlib.Path(self.receipt['ids_frozen']['path']);ids=json.loads(p.read_bytes());ids['reference']='forbidden'
        p.write_bytes(canonical(ids));r=copy.deepcopy(self.receipt);r['ids_frozen']['sha256']=sha(p)
        with self.assertRaises(GateError):corpus.selected_md68_sources(r)
    def test_wrong_official_text_and_layout_rejected(self):
        for field,value in [('text','wrong'),('layout','key_text'),('raw_row_sha256','0'*64)]:
            r=copy.deepcopy(self.receipt);p=pathlib.Path(r['transcript_binding']['path']);original=p.read_bytes()
            labels=json.loads(original);labels['selected']['a16'][field]=value;p.write_bytes(canonical(labels))
            r['transcript_binding']['sha256']=sha(p)
            if field=='text':r['sources'][0]['reference']=value
            with self.assertRaises(GateError):corpus.selected_md68_sources(r)
            p.write_bytes(original)
    def test_actual_shortfall_and_empty_are_never_fabricated_four(self):
        for n in (0,1,2,3):
            p=self.root/('short'+str(n));p.mkdir();r=fixture(p,n)
            if n:
                self.assertEqual(len(corpus.selected_md68_sources(r)),n)
                with self.assertRaises(GateError):corpus.selected_md68_sources(r,4)
            else:
                self.assertTrue(corpus.validate_empty_selection(r))
                with self.assertRaises(GateError):corpus.selected_md68_sources(r)
    def test_no_prelabel_metadata_transcript_leak(self):
        rows=[dict(utterance_id='u',speaker_id='s',transcript='forbidden')]
        with self.assertRaises(GateError):corpus.metadata_choice(rows)
    def test_empty_selection_freezes_no_go_without_reading_reference_or_creating_configs(self):
        p=self.root/'empty';p.mkdir();receipt=fixture(p,0)
        receipt_path=p/'selection.json';put(receipt_path,receipt);target=p/'NO_GO.json'
        names=('manifest','selection-receipt','reference-receipt','template','environment','base-source',
            'base-manifest','support-source','support-manifest','view-audit-source','view-audit-manifest',
            'config-dir','raw-root','out')
        values={n:str(p/n) for n in names};values.update({'selection-receipt':str(receipt_path),'out':str(target)})
        argv=['make_workload_plan.py']+[v for n in names for v in ('--'+n,values[n])]
        with patch.object(sys,'argv',argv),patch('make_workload_plan.verify_source',return_value={'source_commit':'f'*40}):
            make_plan_main()
        result=json.loads(target.read_bytes())
        self.assertEqual(result['status'],corpus.NO_GO);self.assertEqual(result['expected_trials'],0)
        self.assertFalse(result['GPU_launch_ready']);self.assertFalse((p/'config-dir').exists())

class CampaignControls(unittest.TestCase):
    def setUp(self):self.sources=[dict(source_id='MD68_u'+str(i),speaker_id='MD68_s'+str(i),frames=240000) for i in range(4)]
    def test_exact_reversed_three_condition_matrix(self):
        for n in (1,2,3,4):self.assertTrue(validate_matrix(cell_matrix(self.sources[:n]),self.sources[:n]))
        with self.assertRaises(GateError):validate_matrix([],[])
    def test_missing_repeat_wrong_s_and_order_rejected(self):
        c=cell_matrix(self.sources)
        for mutate in (lambda x:x.pop(),lambda x:x[0].update(consumer_retain_views='false'),
                       lambda x:x[0].update(primary_gpu=1),lambda x:x[0].update(condition='r0s1')):
            bad=copy.deepcopy(c);mutate(bad)
            with self.assertRaises(GateError):validate_matrix(bad,self.sources)
    def test_negative_s_effect_and_zero_activation_are_retained_without_factorial(self):
        rr=synthetic_results(self.sources);plan=dict(sources=self.sources,expected_trials=24,actual_NN=dict(source_commit='n'*40))
        a=aggregate(rr,plan)
        self.assertTrue(a['status'].startswith('COMPLETE'))
        self.assertEqual(set(a['condition_totals']),set(CONDITIONS));self.assertTrue(a['factorial_interaction_not_estimated'])
        self.assertTrue(all(r['S_at_R1_audio_s']==-1. for r in a['repeat_pairs']))
        self.assertTrue(all('factorial_interaction_audio_s' not in r for r in a['repeat_pairs']))
        self.assertEqual(a['condition_totals']['r1s1']['continuity_totals']['gap_right_censored_windows'],8)
        self.assertEqual(a['condition_totals']['r1s1']['observed_offered_audio_s'],120.)
        self.assertEqual(a['condition_totals']['r1s1']['D2_misses'],8)
    def test_technical_failure_preserves_full_planned_denominator(self):
        rr=synthetic_results(self.sources);lost=rr.pop();plan=dict(sources=self.sources,expected_trials=24,actual_NN=dict(source_commit='n'*40))
        a=aggregate(rr,plan,[dict(cell_id=lost['cell_id'])]);c=a['condition_totals'][lost['condition']]
        self.assertTrue(a['status'].startswith('INCOMPLETE'));self.assertIsNone(c['coverage_percent'])
        self.assertEqual(c['planned_offered_audio_s'],120.);self.assertEqual(c['unobserved_planned_audio_s'],15.)
    def test_real_config_freeze_preserves_warmup_sources_and_original_settings(self):
        warm=dict(source_id='fixed_warmup',path='unchanged-original-warmup.wav')
        template=dict(settings=dict(source_commit=NN4F,corrector_dtype='float32',max_ahead_frames=32000,
            sources=[dict(source_id='old-test')],model_sources=[warm],
            warmup=dict(source_id=warm['source_id'],original_reference_start_state=dict(frontier=24000)),
            backend=dict(original='unaltered'),step=8000,feedback_seconds=.5))
        reference=dict(reference_details=dict(path='strict-details',sha256='d'*64),reference_gate=dict(path='strict-gate',sha256='g'*64))
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);configs=root/'configs';configs.mkdir()
            cc,orders,warmup,warm_source=freeze_cells(template,self.sources,reference,configs,root/'raw')
            self.assertTrue(validate_matrix(cc,self.sources));self.assertEqual(len(cc),24)
            plan=dict(sources=self.sources,reference_details=reference['reference_details'],warmup=warmup,warmup_source=warm_source)
            for cell in cc:
                cfg=json.loads(pathlib.Path(cell['config']).read_bytes())
                validate_cell(cell,cfg,plan,dict(source_commit=NN4F))
                self.assertEqual(cfg['settings']['backend'],template['settings']['backend'])
                self.assertEqual(cfg['settings']['step'],8000)
                self.assertEqual(cfg['settings']['feedback_seconds'],.5)
            bad=json.loads(pathlib.Path(cc[0]['config']).read_bytes());bad['settings']['sources'][0]['path']='tampered'
            with self.assertRaises(GateError):validate_cell(cc[0],bad,plan,dict(source_commit=NN4F))

if __name__=='__main__':unittest.main()
