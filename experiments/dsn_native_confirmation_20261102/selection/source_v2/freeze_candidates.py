"""Freeze same-split, speaker-disjoint full-utterance metadata candidates.

No audio/transcripts/model outputs are read. WAV and PCM hashes/actual headers
are deliberately PENDING until a separately frozen acquisition/readiness gate.
"""
from __future__ import annotations
import argparse,collections,datetime,hashlib,json,platform,random,re,sys
from pathlib import Path
from selection_common import need,read,sha,put,verify_source
from metadata_census import UTT,resolve_lineage


def member_pool(entries,excluded,rule):
    pool=collections.defaultdict(list);seen={}
    lo,hi=rule['duration_seconds']
    for original in entries:
        path=original.get('path','')
        if not path.startswith(rule['member_prefix']) or not path.lower().endswith('.wav'):continue
        match=UTT.search(Path(path).name)
        if not match:continue
        uid,speaker=match.group(0),match.group(1)
        signature=(path,original['bytes'],original['crc32'],original['local_offset'])
        need(uid not in seen or seen[uid]==signature,'conflicting same-utterance catalog members')
        if uid in seen:continue
        seen[uid]=signature
        if speaker in excluded:continue
        estimated=(original['bytes']-44)/32000
        if lo<=estimated<=hi:
            pool[speaker].append(dict(original,source_id=uid,speaker_id=speaker,estimated_duration_seconds=estimated))
    return {speaker:sorted(members,key=lambda row:row['source_id']) for speaker,members in sorted(pool.items())}


def choose(pool,rule):
    rng=random.Random(rule['seed'])
    speakers=sorted(pool)
    order=rng.sample(speakers,min(rule['target_speakers_maximum'],len(speakers)))
    selected=[]
    for speaker in order:
        members=pool[speaker]
        primary=rng.randrange(len(members))
        fallback=members[primary:]+members[:primary]
        selected.append(dict(source_id=fallback[0]['source_id'],speaker_id=speaker,archive_member=fallback[0],
                             technical_header_fallback_order=fallback,technical_fallback_requires='After exact original ZIP CRC succeeds: invalid PCM16/mono/16kHz header or actual duration outside [8,9] only; network/CRC failures retry the SAME member or stop; no model/ref outcome',
                             audio_sha256=None,PCM_sha256=None,actual_frames=None,audio_status='PENDING_DATA_READINESS_NOT_YET_READ'))
    return selected


def run(args):
    identity=verify_source(Path(__file__).parent,args.manifest);rule=read(args.rule)
    need(sha(args.catalog)==rule['catalog_sha256'],'frozen original catalog bytes changed')
    ledgers=[];excluded=set();excluded_hashes=set();phase_seen=set();all_observations=[]
    for directory in args.census:
        directory=Path(directory)
        summary=read(directory/'SUMMARY.json');gate=read(directory/'GATE.json');data=read(directory/'EXCLUSIONS.json')
        need(summary['status']==gate['status'] and summary['status'] in {'PASS_METADATA_CENSUS','REVIEW_REQUIRED_METADATA_CENSUS'},'census gate unknown')
        need(summary['input_SHA_before_after_equal'] is True and summary['errors']==0,'census not complete')
        need(sha(directory/'EXCLUSIONS.json')==summary['exclusion_sha256'],'census exclusion bytes changed')
        need(sha(directory/'OBSERVATIONS.jsonl')==summary['observations_sha256'],'census observation bytes changed')
        with (directory/'OBSERVATIONS.jsonl').open(encoding='utf8') as stream:
            all_observations += [json.loads(line) for line in stream if line.strip()]
        phase_seen.add(summary['phase']);excluded.update(row['speaker_id'] for row in data['speakers'])
        excluded_hashes.update(value for row in data['speakers'] for value in row['audio_hashes'])
        ledgers.append(dict(census_root=str(directory),phase=summary['phase'],summary_sha256=sha(directory/'SUMMARY.json'),
                            exclusions_sha256=sha(directory/'EXCLUSIONS.json'),source_identity=summary['source_identity']))
    need(set(rule['required_census_phases'])<=phase_seen,'required local/authoritative history census phase missing')
    # A renamed input may be resolved only by an authoritative record in the
    # other phase. Merge exact paths/hashes, never an outcome-based manual alias.
    all_observations=resolve_lineage(all_observations)
    combined_unresolved=[]
    for record in all_observations:
        chinese_alias=(str(record.get('language','')).lower() in {'chinese','zh','zh-cn'}
                       or any(re.match(r'^(chinese|zh)[-_]',alias,re.I) for alias in record['source_aliases']))
        if record['audio_paths'] and not record['speaker_ids'] and (chinese_alias or any('aishell' in p.lower() for p in record['audio_paths'])):
            combined_unresolved.append(record)
    need(not combined_unresolved,'combined local+authoritative AISHELL lineage remains unresolved; cannot claim unused speakers')
    excluded.update(speaker for record in all_observations for speaker in record['speaker_ids'])
    excluded_hashes.update(value for record in all_observations for value in record['audio_hashes'].values())
    entries=read(args.catalog);pool=member_pool(entries,excluded,rule);selected=choose(pool,rule)
    out=Path(args.out);need(not out.exists(),'cannot overwrite a frozen selection');out.mkdir(parents=True)
    put(out/'RULE.json',rule);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),model_calls=0))
    put(out/'HISTORICAL_EXCLUSION_INPUTS.json',dict(inputs=ledgers,excluded_speakers=sorted(excluded),excluded_audio_hashes=sorted(excluded_hashes),
        hash_scope='Exact historical hash strings; original WAV/PCM/encoding key and provenance remain in census OBSERVATIONS. Hash nonmatch alone is not speaker-disjointness proof.'))
    receipt=dict(status='PASS_STRICT_SAME_SPLIT_METADATA_SELECTION_PENDING_AUDIO' if selected else 'NO_GO_NO_STRICT_UNUSED_SPEAKER',
        experiment_id=rule['experiment_id'],selection_source_identity=identity,
        selection_source_commit=identity['source_commit'],selection_recipe_sha256=sha(args.rule),catalog_sha256=sha(args.catalog),
        archive_public_url=rule['archive_public_url'],
        exclusion_ledger_sha256=sha(out/'HISTORICAL_EXCLUSION_INPUTS.json'),excluded_audio_hashes=sorted(excluded_hashes),
        historical_exclusion_inputs=ledgers,excluded_speakers=sorted(excluded),eligible_unused_speakers=sorted(pool),
        eligible_unused_speaker_count=len(pool),selected_speaker_count=len(selected),selected_utterance_count=len(selected),
        target_speakers_was_maximum_not_required=rule['target_speakers_maximum'],original_split=rule['split_namespace'],
        no_concat=True,no_trim=True,no_resample=True,duration_seconds=rule['duration_seconds'],
        metadata_first=True,model_calls=0,new_reference_text_read=False,new_WAV_bytes_read=False,
        independence='Previously unused in recorded RevTrace experiments under this census; not a claim of pretraining-unseen speakers',
        selected_sources=selected,eligible_pool=pool,seed=rule['seed'],
        technical_failure='Same-member transport retry; frozen same-speaker header fallback only; if exhausted STOP. Any smaller N requires a new Root freeze before models, never silent shrink or performance/CER/compatibility selection')
    put(out/'METADATA_SELECTION.json',receipt);put(out/'GATE.json',dict(status=receipt['status'],speaker_count=len(selected),
        metadata_selection_sha256=sha(out/'METADATA_SELECTION.json'),audio_ready=False,model_calls=0))
    put(out/'RUN_RECORD.json',dict(experiment_id=rule['experiment_id'],code_commit=identity['source_commit'],
        source_manifest_sha256=identity['manifest_sha256'],frozen_config=str(args.rule),frozen_config_sha256=sha(args.rule),
        environment_record=str(out/'ENVIRONMENT.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),
        raw_result_location=str(out),aggregate_summary_location=str(out/'METADATA_SELECTION.json'),gate_decision_location=str(out/'GATE.json')))
    print(json.dumps({key:receipt[key] for key in ['status','eligible_unused_speakers','eligible_unused_speaker_count','selected_speaker_count','selection_source_commit']}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--rule',type=Path,required=True)
    p.add_argument('--catalog',type=Path,required=True);p.add_argument('--census',type=Path,nargs='+',required=True);p.add_argument('--out',type=Path,required=True)
    run(p.parse_args())
