"""Bounded original MAGICDATA test preparation. Stdlib only; no neural execution.

Every WAV is byte-hashed/header-scanned before the metadata-only selection is
written. The second pass copies original selected WAVs and reads selected labels.
"""
from __future__ import annotations
import argparse,datetime,gzip,hashlib,io,json,os,pathlib,platform,re,struct,subprocess,sys,tarfile,time,traceback,unittest,urllib.request
from census import CensusError,MemberReader,load_catalog,need,put,safe_name,scan_archive,sha,snapshot,wav_header,validate_response

OFFICIAL_URL='https://openslr.magicdatatech.com/resources/68/test_set.tar.gz'
OFFICIAL_BYTES=2201936013
RULE=dict(minimum_frames=192000,maximum_frames=320000,target_frames=256000,requested_speakers=4,
          speaker_order='lexicographic',within_speaker_order=['abs(frames-target_frames)','utterance_id'])

def write_new(path,obj):
    path=pathlib.Path(path)
    with path.open('x',encoding='utf8',newline='\n') as f:
        f.write(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())

def identities(root,manifest,config,manifest_path):
    commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    need(commit==manifest['code_commit']==config['source_commit'],'source_commit_changed')
    need(not subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=all'],text=True).strip(),'dirty_source')
    files=subprocess.check_output(['git','-C',str(root),'ls-files'],text=True).splitlines()
    need(set(files)=={r['path'] for r in manifest['files']},'incomplete_source_manifest')
    for row in manifest['files']:
        p=root/row['path'];need(p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'source_bytes_changed')
    need(sha(manifest_path)==config['source_manifest_sha256'],'source_manifest_hash_changed')
    return commit

def archive_identity(path,config):
    need(path.stat().st_size==config['archive_bytes'],'archive_size_changed')
    digest=sha(path);expected=config.get('official_expected_sha256')
    if expected:need(digest==expected,'official_archive_checksum_mismatch')
    return dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=digest,official_url=config['archive_url'],
                expected_ETag=config['expected_ETag'],published_checksum_available=bool(expected),
                hash_scope='full_compressed_archive; gzip CRC and complete tar checked separately')

def acquire_archive(config,out,event):
    """Existing complete assets are immutable; interrupted partials remain auditable."""
    archive=pathlib.Path(config['archive_path']);archive.parent.mkdir(parents=True,exist_ok=True)
    need(config['archive_url']==OFFICIAL_URL and config['archive_bytes']==OFFICIAL_BYTES,'unexpected_official_test_asset')
    if archive.exists():
        identity=archive_identity(archive,config);identity['transport']='existing_original_verified_not_overwritten'
        write_new(out/'ARCHIVE_IDENTITY.json',identity);return archive,identity
    suffix=re.sub('[^A-Za-z0-9_.-]','_',config['experiment_id'])
    part=archive.with_name(archive.name+'.part.'+suffix)
    if not part.exists():part.touch(exist_ok=False)
    need(part.is_file() and part.stat().st_size<=config['archive_bytes'],'invalid_preserved_partial')
    started=time.monotonic();attempts=[]
    max_wall=config.get('maximum_download_wall_seconds',21600)
    for attempt in range(config.get('maximum_download_attempts',8)):
        offset=part.stat().st_size
        if offset==config['archive_bytes']:break
        req=urllib.request.Request(config['archive_url'],headers={'User-Agent':'RevTrace-original-MD68-preparation/1.0',**({'Range':f'bytes={offset}-'} if offset else {})})
        try:
            with urllib.request.urlopen(req,timeout=config.get('network_socket_timeout_seconds',60)) as response:
                validate_response(response,offset,config)
                headers={k:response.headers[k] for k in ('Content-Length','Content-Range','ETag','Last-Modified','Content-Type','Accept-Ranges') if response.headers.get(k) is not None}
                attempts.append(dict(attempt=attempt,offset=offset,status='accepted_identity_headers',headers=headers))
                put(out/'DOWNLOAD_ATTEMPTS.json',attempts)
                with part.open('ab') as f:
                    last=0.
                    while True:
                        need(time.monotonic()-started<=max_wall,'download_wall_budget_exceeded')
                        block=response.read(4*1024*1024)
                        if not block:break
                        need(f.tell()+len(block)<=config['archive_bytes'],'transport_larger_than_expected')
                        f.write(block)
                        if time.monotonic()-last>=5:
                            f.flush();put(out/'DOWNLOAD_PROGRESS.json',dict(bytes=f.tell(),expected=config['archive_bytes'],partial_path=str(part),snapshot=snapshot()));last=time.monotonic()
                    f.flush();os.fsync(f.fileno())
            attempts.append(dict(attempt=attempt,status='stream_closed',bytes=part.stat().st_size))
        except (OSError,TimeoutError) as exc:
            attempts.append(dict(attempt=attempt,status='transport_error_partial_preserved',bytes=part.stat().st_size,error=type(exc).__name__+':'+str(exc)))
        finally:put(out/'DOWNLOAD_ATTEMPTS.json',attempts)
        if part.stat().st_size==config['archive_bytes']:break
    need(part.stat().st_size==config['archive_bytes'],'incomplete_archive_transport_partial_preserved')
    need(not archive.exists(),'never_overwrite_completed_archive')
    # Atomic no-clobber publication. Keep the complete transport hard link as
    # an immutable attempt record; it consumes no second data allocation.
    os.link(part,archive)
    identity=archive_identity(archive,config);identity.update(transport='streamed_original_HTTP_asset',preserved_transport_path=str(part),download_wall_seconds=time.monotonic()-started)
    write_new(out/'ARCHIVE_IDENTITY.json',identity);event('archive_full_hash_complete',sha256=identity['sha256'])
    return archive,identity

def select_metadata(rows,rule=RULE):
    need(rule==RULE,'selection_rule_changed')
    by={};seen=set()
    for row in rows:
        uid=row['utterance_id'];need(uid not in seen,'duplicate_census_source');seen.add(uid)
        need(re.fullmatch(r'[A-Za-z0-9_-]+',uid) is not None,'unsafe_source_id')
        if row.get('header_status')!='valid_RIFF' or not row.get('compatible_original_input_format'):continue
        frames=row['frames']
        if not rule['minimum_frames']<=frames<=rule['maximum_frames']:continue
        by.setdefault(row['speaker_id'],[]).append(row)
    selected=[]
    for sid in sorted(by)[:rule['requested_speakers']]:
        row=min(by[sid],key=lambda r:(abs(r['frames']-rule['target_frames']),r['utterance_id']))
        row=dict(row,raw_source_id=row['utterance_id'],raw_speaker_id=row['speaker_id'],
                 source_id='MD68_'+row['utterance_id'],speaker_id='MD68_'+row['speaker_id'])
        selected.append(row)
    return selected,len(by)

def freeze_ids(census_path,out,identity,catalog_summary):
    rows=[json.loads(line) for line in pathlib.Path(census_path).read_text(encoding='utf8').splitlines()]
    need(len(rows)==catalog_summary['WAV_members'] and catalog_summary['all_expected_WAVs_present'],'incomplete_census_cannot_select')
    selected,eligible=select_metadata(rows)
    frozen=dict(status='PASS_COMPLETE_HEADER_CENSUS_IDS_FROZEN_BEFORE_LABEL_ACCESS',corpus='MAGICDATA68',split='test',
                archive_sha256=identity['sha256'],full_census_sha256=sha(census_path),selection_rule=RULE,
                requested_source_count=4,eligible_speaker_count=eligible,selected_source_count=len(selected),
                selected_source_ids=[r['source_id'] for r in selected],selected=selected,metadata_first=True,
                access_phase='ID_SELECTION_COMPLETE_BEFORE_LABEL_ACCESS',model_calls=0,GPU_calls=0)
    write_new(out/'IDS_FROZEN.json',frozen)
    return frozen

def pcm_identity(raw):
    reader=MemberReader(io.BytesIO(raw),len(raw));header=wav_header(reader)
    need(header['compatible_original_input_format'],'selected_original_format_changed')
    cursor=12;data=None
    while cursor<len(raw):
        kind=raw[cursor:cursor+4];n=struct.unpack('<I',raw[cursor+4:cursor+8])[0];cursor+=8
        if kind==b'data':need(data is None,'ambiguous_PCM_data');data=memoryview(raw)[cursor:cursor+n]
        cursor+=n+(n&1)
    need(data is not None,'missing_PCM_data')
    return header,hashlib.sha256(data).hexdigest()

def selected_label(line,ids):
    """Inspect only the key before decoding a selected line's official value."""
    raw=line.rstrip(b'\r\n')
    if not raw.strip():return None
    parts=raw.split(None,1)
    try:key=parts[0].decode('ascii')
    except UnicodeDecodeError:return None
    key=key[:-4] if key.endswith('.wav') else key
    if key not in ids:return None
    need(len(parts)==2,'selected_official_label_missing')
    # Official MAGICDATA TRANS rows are filename, speaker, transcription.
    # Accept a strict filename+text row as well, but never strip arbitrary words.
    value=parts[1]
    rest=value.split(None,1);speaker='_'.join(key.split('_')[:2]).encode('ascii')
    if rest and rest[0]==speaker:
        need(len(rest)==2,'selected_official_label_missing');value=rest[1]
    text=value.decode('utf-8-sig').strip();need(text,'selected_official_label_empty')
    return key,text

def label_layout(line,raw_speaker):
    parts=line.rstrip(b'\r\n').split(None,1)
    remainder=parts[1].split(None,1)
    return 'key_speaker_text' if remainder and remainder[0]==raw_speaker.encode('ascii') else 'key_text'

def materialize_selected(archive,identity,frozen,out,config,event):
    ids_path=out/'IDS_FROZEN.json';ids_sha=sha(ids_path)
    need(json.loads(ids_path.read_bytes())==frozen,'frozen_IDs_changed_before_label_access')
    selected={r['raw_source_id']:r for r in frozen['selected']}
    if not selected:return [],None
    extract_root=pathlib.Path(config['selected_audio_directory']);extract_root.mkdir(parents=True,exist_ok=True)
    audio={};labels={};label_origins={};trans_members=[];member_seen=set()
    with gzip.open(archive,'rb') as gz:
        with tarfile.open(fileobj=gz,mode='r|') as tar:
            for m in tar:
                p=safe_name(m.name);need(m.name not in member_seen,'duplicate_tar_member');member_seen.add(m.name)
                need(m.isdir() or m.isfile(),'special_tar_member');need(not m.issparse(),'sparse_tar_member')
                if not m.isfile():continue
                uid=p.stem
                if p.suffix.lower()=='.wav' and uid in selected:
                    row=selected[uid];need(m.name==row['tar_path'] and m.size==row['WAV_bytes'],'selected_member_identity_changed')
                    raw=tar.extractfile(m).read();need(len(raw)==m.size and hashlib.sha256(raw).hexdigest()==row['WAV_sha256'],'selected_original_WAV_hash_changed')
                    header,pcm_sha=pcm_identity(raw);need(header['frames']==row['frames'],'selected_frames_changed')
                    path=extract_root/(row['source_id']+'.wav')
                    if path.exists():need(path.stat().st_size==len(raw) and sha(path)==row['WAV_sha256'],'never_overwrite_different_original_WAV')
                    else:
                        with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
                    splitdir=pathlib.PurePosixPath(*p.parts[:p.parts.index('test')+1]).as_posix()
                    audio[uid]=dict(source_id=row['source_id'],speaker_id=row['speaker_id'],raw_source_id=uid,raw_speaker_id=row['raw_speaker_id'],
                        path=str(path.resolve()),audio_sha256=row['WAV_sha256'],audio_bytes=m.size,
                        frames=header['frames'],duration=header['duration_seconds'],duration_seconds=header['duration_seconds'],
                        header=dict(sample_rate=header['sample_rate'],channels=header['channels'],sample_width=header['bits_per_sample']//8,
                            frames=header['frames'],PCM_sha256=pcm_sha),archive_member=dict(path=m.name,bytes=m.size,sha256=row['WAV_sha256']),
                        original_split='MD68/test@'+identity['sha256'],split_directory=splitdir,
                        no_concat=True,no_trim=True,no_resample=True)
                elif p.name.upper()=='TRANS.TXT':
                    # No value is decoded unless its metadata-frozen key is selected.
                    h=hashlib.sha256();count=0
                    with tar.extractfile(m) as stream:
                        for line in stream:
                            h.update(line);count+=len(line);item=selected_label(line,selected)
                            if item:
                                uid,text=item;need(uid not in labels,'duplicate_selected_official_transcript');labels[uid]=text
                                label_origins[uid]=dict(member_path=m.name,raw_row_sha256=hashlib.sha256(line.rstrip(b'\r\n')).hexdigest(),
                                    layout=label_layout(line,selected[uid]['raw_speaker_id']))
                    need(count==m.size,'truncated_official_TRANS_member')
                    trans_members.append(dict(path=m.name,bytes=m.size,sha256=h.hexdigest()))
            need(not any(getattr(tar.fileobj,'buf',b'')),'nonzero_trailing_tar_bytes')
        for tail in iter(lambda:gz.read(1024*1024),b''):need(not any(tail),'nonzero_trailing_tar_bytes')
    need(set(audio)==set(selected),'selected_original_audio_missing')
    need(set(labels)==set(selected),'selected_official_transcript_missing')
    need(sha(ids_path)==ids_sha,'frozen_IDs_changed_during_label_access')
    trans_by_path={r['path']:r for r in trans_members}
    binding=dict(status='PASS_SELECTED_OFFICIAL_LABELS_AFTER_IDS_FROZEN',ids_frozen_sha256=ids_sha,
                 archive_sha256=identity['sha256'],official_TRANS_members=trans_members,
                 selected_source_ids=frozen['selected_source_ids'],references={selected[k]['source_id']:labels[k] for k in selected},
                 selected={k:dict(text=labels[k],archive_member=trans_by_path[label_origins[k]['member_path']],raw_row_sha256=label_origins[k]['raw_row_sha256'],layout=label_origins[k]['layout'],
                     extraction_rule='ASCII_first_key_optional_wav_suffix; remove_next_field_only_if_exact_raw_speaker; preserve_remaining_UTF8_text') for k in selected},
                 unselected_values_decoded=False,selection_uses_labels=False,model_calls=0,GPU_calls=0)
    write_new(out/'SELECTED_TRANSCRIPTS.json',binding)
    sources=[dict(audio[r['raw_source_id']],reference=labels[r['raw_source_id']]) for r in frozen['selected']]
    event('original_selected_audio_and_selected_labels_bound',selected_sources=len(sources),ids_frozen_sha256=ids_sha)
    return sources,dict(path=str((out/'SELECTED_TRANSCRIPTS.json').resolve()),sha256=sha(out/'SELECTED_TRANSCRIPTS.json'))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=pathlib.Path,required=True);parser.add_argument('--manifest',type=pathlib.Path,required=True)
    parser.add_argument('--out',type=pathlib.Path,required=True);parser.add_argument('--mode',choices=('controls','acquire_select'),required=True);args=parser.parse_args()
    root=pathlib.Path(__file__).resolve().parent;cfg=json.loads(args.config.read_bytes());manifest=json.loads(args.manifest.read_bytes())
    commit=identities(root,manifest,cfg,args.manifest)
    need(os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU_only_CUDA_visibility_required')
    disk=pathlib.Path(cfg['experiment_disk']).resolve()
    for path in (args.out,pathlib.Path(cfg['archive_path']),pathlib.Path(cfg['selected_audio_directory'])):
        need(path.resolve().is_relative_to(disk),'all_results_and_original_assets_must_stay_on_8TB_disk')
    need(cfg.get('selection_rule',RULE)==RULE,'frozen_selection_rule_changed')
    args.out.mkdir(parents=True,exist_ok=False);write_new(args.out/'CONFIG.json',cfg)
    env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),hostname=platform.node(),CUDA_VISIBLE_DEVICES='',model_calls=0,GPU_calls=0)
    for k,v in cfg.get('expected_environment',{}).items():need(env[k]==v,'frozen_environment_changed')
    write_new(args.out/'ENVIRONMENT.json',env)
    write_new(args.out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],mode=args.mode,code_commit=commit,
        source_manifest_sha256=sha(args.manifest),frozen_config=str((args.out/'CONFIG.json').resolve()),frozen_config_sha256=sha(args.out/'CONFIG.json'),
        environment_record=str((args.out/'ENVIRONMENT.json').resolve()),environment_record_sha256=sha(args.out/'ENVIRONMENT.json'),
        raw_result_location=str(args.out.resolve()),aggregate_summary_location=str((args.out/'SUMMARY.json').resolve()),gate_decision_location=str((args.out/'GATE.json').resolve())))
    with (args.out/'EVENTS.jsonl').open('x',encoding='utf8') as stream:
        def event(kind,**body):stream.write(json.dumps(dict(kind=kind,snapshot=snapshot(),**body),ensure_ascii=False)+'\n');stream.flush()
        try:
            event('preparation_started',mode=args.mode)
            log=io.StringIO();tests=unittest.defaultTestLoader.discover(str(root),pattern='test_*.py');result=unittest.TextTestRunner(stream=log,verbosity=2).run(tests)
            (args.out/'CONTROLS.log').write_text(log.getvalue(),encoding='utf8')
            need(result.wasSuccessful() and not result.skipped and result.testsRun==cfg['expected_controls'],'local_controls_failed')
            catalog=load_catalog(cfg);event('official_path_only_metadata_verified',WAV_members=len(catalog))
            if args.mode=='controls':
                summary=dict(status='PASS_FROZEN_CPU_CONTROLS_AND_OFFICIAL_METADATA_NO_AUDIO_ACQUIRED',controls=result.testsRun,model_calls=0,GPU_calls=0)
            else:
                archive,identity=acquire_archive(cfg,args.out,event)
                census=scan_archive(archive,catalog,args.out,cfg,event);write_new(args.out/'HEADER_CENSUS_SUMMARY.json',census)
                frozen=freeze_ids(args.out/'WAV_HEADERS.jsonl',args.out,identity,census);event('metadata_only_IDs_written',ids_sha256=sha(args.out/'IDS_FROZEN.json'))
                sources,binding=materialize_selected(archive,identity,frozen,args.out,cfg,event)
                status='PASS_STRICT_METADATA_SELECTED_ORIGINAL_MAGICDATA_TEST_AUDIO_AVAILABLE' if sources else 'NO_GO_NO_ELIGIBLE_ORIGINAL_MAGICDATA_TEST_AUDIO'
                receipt=dict(status=status,corpus='MAGICDATA68',split='test',original_split='MD68/test@'+identity['sha256'],
                    archive=identity,metadata_census=dict(path=str((args.out/'WAV_HEADERS.jsonl').resolve()),sha256=sha(args.out/'WAV_HEADERS.jsonl')),
                    ids_frozen=dict(path=str((args.out/'IDS_FROZEN.json').resolve()),sha256=sha(args.out/'IDS_FROZEN.json')),transcript_binding=binding,
                    metadata_archive=dict(path=cfg['metadata_archive'],sha256=cfg['metadata_archive_sha256']),
                    selection_rule=RULE,requested_source_count=4,eligible_speaker_count=frozen['eligible_speaker_count'],selected_source_count=len(sources),
                    metadata_first=True,no_concat=True,no_trim=True,no_resample=True,model_calls=0,GPU_calls=0,sources=sources)
                write_new(args.out/'ORIGINAL_SELECTION_BANK.json',receipt)
                summary=dict(status=status,controls=result.testsRun,WAV_members=census['WAV_members'],eligible_speaker_count=frozen['eligible_speaker_count'],
                    selected_source_count=len(sources),selected_source_ids=frozen['selected_source_ids'],receipt_path=str((args.out/'ORIGINAL_SELECTION_BANK.json').resolve()),
                    receipt_sha256=sha(args.out/'ORIGINAL_SELECTION_BANK.json'),archive_sha256=identity['sha256'],model_calls=0,GPU_calls=0)
            identities(root,manifest,cfg,args.manifest);need('torch' not in sys.modules and 'transformers' not in sys.modules,'unexpected_neural_import')
            summary.update(experiment_id=cfg['experiment_id'],source_commit=commit);write_new(args.out/'SUMMARY.json',summary)
            write_new(args.out/'GATE.json',dict(status=summary['status'],experiment_id=cfg['experiment_id'],source_commit=commit,summary_sha256=sha(args.out/'SUMMARY.json'),model_calls=0,GPU_calls=0))
            event('preparation_complete',status=summary['status']);print(json.dumps(summary,indent=2,ensure_ascii=False))
        except BaseException:
            (args.out/'failure.txt').write_text(traceback.format_exc(),encoding='utf8');put(args.out/'GATE.json',dict(status='FAIL_ORIGINAL_ASSET_PREPARATION_RAW_PRESERVED',experiment_id=cfg['experiment_id'],source_commit=commit,model_calls=0,GPU_calls=0));raise

if __name__=='__main__':main()
