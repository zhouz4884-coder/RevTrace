"""Full original audio acquisition after metadata lock. Never selects on text."""
from __future__ import annotations
import argparse,datetime,importlib.util,os,pathlib,platform,sys,traceback,urllib.error,zlib
from acquisition_common import (ARCHIVE_URL,SPLIT_DIRECTORY,SPLIT_NAMESPACE,B,AcquisitionError,TechnicalHeaderError,
    need,read,sha,bytes_sha,put,disk,verify_source,validate_metadata,original_reference_map,inspect_pcm,check_duration,check_independence)

def member_bytes(cfg,entry,out,attempts,transport):
    stage=cfg['staged_ranges'].get(entry['source_id'])
    if stage:
        need(pathlib.Path(stage['path']).is_absolute() and pathlib.Path(stage['path']).resolve().is_relative_to(B.resolve()),'staged Range outside8TB')
        need(stage['public_source']==ARCHIVE_URL and stage['content_range'].startswith('bytes %d-%d/'%(entry['local_offset'],entry['local_offset']+entry['compressed']+4095)),'staged public source/Range changed')
        need(stage['bytes']==entry['compressed']+4096,'staged payload is not the frozen bounded Range')
        raw=transport.verify_staged(stage)
    for index in range(cfg['network_attempts_per_same_member']):
        try:
            if not stage:raw=transport.request_member(ARCHIVE_URL,entry)
            path=out/'ranges'/f'{entry["source_id"]}_attempt{index}.range'
            with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            data=transport.extract_member(raw,entry)
            attempts.append(dict(source_id=entry['source_id'],network_attempt=index,exact_member_unchanged=True,CRC_verified=True,range_file=str(path),range_sha256=sha(path),transport='frozen_same_source_stage' if stage else 'official_public_bounded_HTTP_Range'))
            return data,path
        except (urllib.error.URLError,TimeoutError,OSError,ValueError,zlib.error) as exc:
            attempts.append(dict(source_id=entry['source_id'],network_attempt=index,error_type=type(exc).__name__,http_status=getattr(exc,'code',None),exact_member_unchanged=True,header_fallback_authorized=False))
            put(out/'ATTEMPTS.json',attempts,replace=True)
            if index+1==cfg['network_attempts_per_same_member']:raise AcquisitionError('same_selected_member_transport_or_CRC_unavailable_after_fixed_retries_STOP') from None
    raise AcquisitionError('unreachable_member_retry_state')

def run(a):
    cfg=read(a.config);identity=verify_source(a.manifest);pre=read(a.prelaunch)
    need(pre['config_sha256']==sha(a.config) and sha(pre['root_noarg_preflight'])==pre['root_noarg_preflight_sha256'],'prelaunch binding changed')
    source_gate=read(pre['root_noarg_preflight']);need(source_gate['gate']=='SOURCE_IDENTITY_PASS' and source_gate['code_commit']==identity['source_commit'] and source_gate['manifest_sha256']==identity['source_manifest_sha256'],'Root noarg source gate missing')
    need(source_gate['setup_pointer'].replace('\\','/').endswith('/CURRENT.json') and 'setup_pointer_sha256' in source_gate,'not Root CURRENT noarg receipt')
    need(cfg['archive_public_url']==ARCHIVE_URL and cfg['network_attempts_per_same_member']==3,'public source or fixed retry scope changed')
    need(sha(cfg['metadata_selection'])==cfg['metadata_selection_sha256'] and sha(cfg['rule'])==cfg['rule_sha256'] and sha(cfg['metadata_gate'])==cfg['metadata_gate_sha256'],'frozen metadata bytes changed')
    selection=read(cfg['metadata_selection']);rule=read(cfg['rule']);groups=validate_metadata(selection,rule,cfg['expected_sources'])
    need(selection['selection_recipe_sha256']==cfg['rule_sha256'] and selection['catalog_sha256']==rule['catalog_sha256'],'selection recipe/catalog binding changed')
    need(sha(cfg['historical_exclusion_inputs'])==cfg['historical_exclusion_sha256']==selection['exclusion_ledger_sha256'],'historical exclusion ledger changed')
    mg=read(cfg['metadata_gate']);need(mg['status']==selection['status'] and mg['metadata_selection_sha256']==cfg['metadata_selection_sha256'],'metadata selection gate not bound')
    if 'archive_public_url' in selection:need(selection['archive_public_url']==ARCHIVE_URL,'metadata archive identity changed')
    excluded=set(selection['excluded_audio_hashes']);need(excluded==set(read(cfg['historical_exclusion_inputs'])['excluded_audio_hashes']),'historical hash set changed')
    out=disk(cfg['raw_result_location']);data_root=disk(cfg['dataset_root']);need(not (data_root/'SOURCE_RECEIPT_v1.json').exists(),'completed dataset receipt already exists; never overwrite');out.mkdir(parents=True,exist_ok=False);(out/'ranges').mkdir();(data_root/'audio').mkdir(parents=True,exist_ok=True)
    put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),identity=identity,model_calls=0,gpu_calls=0))
    put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=identity['source_commit'],source_manifest_sha256=identity['source_manifest_sha256'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    spec=importlib.util.spec_from_file_location('verified1129_transport',pathlib.Path(__file__).parent/'vendor'/'acquire_selected.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
    attempts=[];sources=[];accepted=set();failed_speaker=None
    try:
        # Only after immutable metadata/rule/exclusion/gate validation, parse
        # original text_zh entries. They never affect candidate/header choices.
        need(sha(cfg['reference_metadata'])==cfg['reference_metadata_sha256'],'original reference.json bytes changed')
        allowed={e['source_id'] for g in groups for e in g['technical_header_fallback_order']}
        references=original_reference_map(read(cfg['reference_metadata']),allowed)
        for group in groups:
            failed_speaker=group['speaker_id']
            for index,entry in enumerate(group['technical_header_fallback_order']):
                data,rangepath=member_bytes(cfg,entry,out,attempts,transport);wavhash=bytes_sha(data)
                check_independence(wavhash,None,excluded,accepted)
                try:
                    header=inspect_pcm(data)
                    check_independence(wavhash,header['PCM_sha256'],excluded,accepted)
                    check_duration(header)
                except TechnicalHeaderError as exc:
                    attempts.append(dict(source_id=entry['source_id'],speaker_id=group['speaker_id'],technical_header_rejected=True,reason=str(exc),CRC_already_verified=True,next_locked_same_speaker_only=True));put(out/'ATTEMPTS.json',attempts,replace=True);continue
                sid=entry['source_id'];need(sid in references,'accepted_audio_missing_original_reference_STOP_no_text_based_replacement')
                dest=data_root/'audio'/(sid+'.wav');need(not dest.is_symlink() and dest.resolve().is_relative_to(data_root.resolve()),'WAV destination escaped immutable data root')
                existed=dest.exists()
                if existed:need(dest.read_bytes()==data,'preserved same-source WAV bytes differ')
                else:
                    with dest.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
                    dest.chmod(0o444)
                source=dict(source_id=sid,speaker_id=group['speaker_id'],path=str(dest),audio_sha256=sha(dest),frames=header['frames'],duration=header['duration'],reference=references[sid],header=header,
                    original_split=SPLIT_NAMESPACE,split_directory=SPLIT_DIRECTORY,archive_member=entry,technical_fallback_index=index,range_file=str(rangepath),range_sha256=sha(rangepath),preexisting_verified_WAV=existed)
                sources.append(source);accepted.update((wavhash,header['PCM_sha256']));put(out/'PROGRESS.json',dict(frozen_source_count=cfg['expected_sources'],completed_sources=len(sources),sources=sources,attempts=attempts,model_calls=0),replace=True)
                print(__import__('json').dumps(dict(source_id=sid,speaker_id=source['speaker_id'],frames=source['frames'],WAV_sha256=source['audio_sha256'],PCM_sha256=header['PCM_sha256'],model_calls=0)),flush=True);break
            else:raise AcquisitionError('all_locked_same_speaker_header_candidates_failed_STOP_no_silent_N_reduction')
        need(len(sources)==cfg['expected_sources'] and len({s['speaker_id'] for s in sources})==cfg['expected_sources'],'complete frozenN acquisition not satisfied')
        need(sha(cfg['metadata_selection'])==cfg['metadata_selection_sha256'] and sha(cfg['reference_metadata'])==cfg['reference_metadata_sha256'] and sha(cfg['rule'])==cfg['rule_sha256'] and sha(cfg['historical_exclusion_inputs'])==cfg['historical_exclusion_sha256'] and sha(cfg['metadata_gate'])==cfg['metadata_gate_sha256'],'locked input changed during acquisition')
        data_manifest=dict(metadata_selection_sha256=cfg['metadata_selection_sha256'],reference_metadata_sha256=cfg['reference_metadata_sha256'],sources=[dict(source_id=s['source_id'],speaker_id=s['speaker_id'],path=s['path'],audio_sha256=s['audio_sha256'],PCM_sha256=s['header']['PCM_sha256'],frames=s['frames'],duration=s['duration'],selected_member=s['archive_member']['path'],technical_fallback_index=s['technical_fallback_index']) for s in sources],all_frozen_speakers_retained=True,no_concat=True,no_trim=True,no_resample=True,no_padding=True)
        put(out/'DATA_MANIFEST.json',data_manifest)
        receipt=dict(status='PASS_STRICT_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE',acquisition_source_commit=identity['source_commit'],acquisition_source_manifest_sha256=identity['source_manifest_sha256'],acquisition_actual_identity=identity,
            selection_source_commit=selection['selection_source_commit'],selection_source_manifest_sha256=selection['selection_source_identity']['manifest_sha256'],source_manifest_sha256=selection['selection_source_identity']['manifest_sha256'],selection_recipe_sha256=selection['selection_recipe_sha256'],metadata_selection_sha256=cfg['metadata_selection_sha256'],exclusion_ledger_sha256=selection['exclusion_ledger_sha256'],catalog_sha256=selection['catalog_sha256'],
            data_freeze_sha256=sha(out/'DATA_MANIFEST.json'),data_manifest_path=str(out/'DATA_MANIFEST.json'),new_speaker_count=len(sources),new_utterance_count=len(sources),selected_speaker_count=len(sources),selected_utterance_count=len(sources),all_CRC_headers_SHA_passed=True,sources=sources,
            original_split=SPLIT_NAMESPACE,split_directory=SPLIT_DIRECTORY,excluded_speakers=selection['excluded_speakers'],excluded_audio_hashes=sorted(excluded),seed=selection['seed'],metadata_first=True,
            all_metadata_frozen_speakers_retained=True,historical_WAV_and_PCM_hash_collisions=False,reference_metadata_path=cfg['reference_metadata'],reference_metadata_sha256=cfg['reference_metadata_sha256'],
            no_concat=True,no_trim=True,no_resample=True,no_padding=True,model_calls=0,gpu_calls=0,attempts=attempts,independence=selection['independence'])
        put(out/'SOURCE_RECEIPT.json',receipt);put(data_root/'SOURCE_RECEIPT_v1.json',receipt)
        put(out/'SUMMARY.json',dict(status=receipt['status'],sources=len(sources),frozen_expected_sources=cfg['expected_sources'],WAV_bytes=sum(pathlib.Path(s['path']).stat().st_size for s in sources),source_receipt_sha256=sha(out/'SOURCE_RECEIPT.json'),data_freeze_sha256=receipt['data_freeze_sha256'],model_calls=0,gpu_calls=0))
        put(out/'GATE.json',dict(status=receipt['status'],source_receipt_sha256=sha(out/'SOURCE_RECEIPT.json'),all_CRC_header_extent_SHA_independence_checks=True,model_calls=0,gpu_calls=0))
    except BaseException as exc:
        put(out/'PARTIAL_SOURCE_RECEIPT.json',dict(status='INCOMPLETE_NOT_AUDIO_READY',completed_sources=sources,failed_speaker=failed_speaker,frozen_expected_sources=cfg['expected_sources'],model_calls=0,gpu_calls=0,attempts=attempts,scope='not a reducedN PASS; any cohort amendment requires new explicit Root freeze'))
        put(out/'FAILURE.json',dict(error_type=type(exc).__name__,reason=str(exc) if isinstance(exc,AcquisitionError) else 'unexpected_error_details_not_logged_to_avoid_URL_or_payload_disclosure',completed_sources=len(sources),failed_speaker=failed_speaker,model_calls=0))
        put(out/'GATE.json',dict(status='FAIL_STRICT_AUDIO_AVAILABILITY_OR_INDEPENDENCE_PRESERVED',completed_sources=len(sources),frozen_expected_sources=cfg['expected_sources'],model_calls=0,gpu_calls=0))
        raise AcquisitionError('acquisition_stopped_with_preserved_failure_no_source_or_N_substitution') from None

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('config','manifest','prelaunch'):p.add_argument('--'+n,required=True)
    run(p.parse_args())
