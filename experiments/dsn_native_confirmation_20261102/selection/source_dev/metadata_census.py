"""Frozen metadata-only historical AISHELL lineage census, without outcomes.

The program reads only identity/path/hash fields. Candidate-pool catalogs and
technical fallback lists are NOT historical model usage. It records unresolved
aliases and acquisition/planning vs actual-config evidence as separate tiers.
"""
from __future__ import annotations
import argparse,collections,csv,datetime,hashlib,json,os,platform,re,sys,traceback
from pathlib import Path
from selection_common import need,read,sha,put,verify_source,MemoryPath

UTT=re.compile(r'BAC009(S\d{4})W\d{4}')
SPK=re.compile(r'(?<![A-Za-z0-9])S\d{4}(?![0-9])')
HASH_KEYS={'audio_sha256','wav_sha256','wave_sha256','pcm_sha256','source_audio_sha256'}
IDENTITY_KEYS={'id','key','source_id','source_filename','sample_id','speaker_id','utterance_id','utterance','utt_id','utt','path','audio_path','wav_path','filename','file_name','file','audio','wav','audio:file','audio_file','source_path','uri','original_source_id'}
POOL_KEYS={'eligible_pool','eligible_speakers','considered_bands','candidate_pool','all_candidates','candidates','reserve_sources','reserve_speakers'}


def pool_key(key):
    return key.lower() in POOL_KEYS or 'fallback' in key.lower()


def catalog_file(path):
    name=Path(path).name.lower()
    context=str(path).replace('\\','/').lower()
    return (any(marker in context for marker in ['public_asset_metadata','author_checkpoint_metadata','native_processor_dependency'])
            or name.startswith(('archive_entries','tree_','zip_directory','zip_tail'))
            or name in {'reference.json','corpus_catalog.json','catalog.json'})


def metadata_tier(path):
    text=str(path).replace('\\','/').lower();name=Path(path).name.lower()
    if catalog_file(path):return 'metadata_only_catalog'
    if name=='config.json' and any(x in text for x in ['/cells/','/results/','results_','/attempt','/collected']):
        return 'recorded_case_config'
    if 'receipt' in name:return 'acquired_or_selected_source_receipt'
    if 'frozen' in name or 'plan' in name or 'selection' in name:return 'frozen_selection_or_plan'
    if any(x in text for x in ['/source_', '/runtime/', '/packages/']):return 'source_or_artifact_metadata'
    return 'historical_identity_metadata'


def inspect_object(obj,where='$',inherited_ids=(),inherited_speakers=()):
    """Emit only identity fields, never reference/model text or endpoint values."""
    if isinstance(obj,list):
        for index,item in enumerate(obj):
            if isinstance(item,(dict,list)):yield from inspect_object(item,f'{where}[{index}]',inherited_ids,inherited_speakers)
        return
    if not isinstance(obj,dict):return
    identities=[str(v) for k,v in obj.items() if str(k).lower() in IDENTITY_KEYS and isinstance(v,(str,int))]
    direct_ids=sorted({m.group(0) for value in identities for m in UTT.finditer(value)})
    direct_speakers=sorted({m.group(0) for value in identities for m in SPK.finditer(value)})
    direct_speakers=sorted(set(direct_speakers)|{UTT.fullmatch(uid).group(1) for uid in direct_ids})
    ids=direct_ids or list(inherited_ids);speakers=direct_speakers or list(inherited_speakers)
    hashes={key:str(value) for key,value in obj.items() if str(key).lower() in HASH_KEYS
            and isinstance(value,str) and re.fullmatch('[0-9a-fA-F]{64}',value)}
    paths=[str(value) for key,value in obj.items() if str(key).lower() in {'path','audio_path','wav_path','file_name','file','audio','wav','audio:file','audio_file','source_path','uri'}
           and isinstance(value,str) and value.lower().endswith(('.wav','.flac','.pcm'))]
    aliases=[str(obj[key]) for key in ['source_id','sample_id','utterance_id','utt_id'] if key in obj and isinstance(obj[key],(str,int)) and not isinstance(obj[key],bool)]
    if direct_ids or direct_speakers or (hashes and (ids or paths)) or (paths and aliases):
        yield dict(pointer=where,utterance_ids=ids,speaker_ids=speakers,audio_hashes=hashes,
                   audio_paths=paths,source_aliases=aliases,identity_is_inherited=not bool(direct_ids or direct_speakers),
                   language=obj.get('language') if isinstance(obj.get('language'),str) else None,
                   dataset=obj.get('dataset',obj.get('corpus')) if isinstance(obj.get('dataset',obj.get('corpus')),str) else None,
                   split=obj.get('split') if isinstance(obj.get('split'),str) else None)
    if 'excluded_speakers' in obj and isinstance(obj['excluded_speakers'],list):
        excluded=[str(x) for x in obj['excluded_speakers'] if re.fullmatch(r'S\d{4}',str(x))]
        if excluded:yield dict(pointer=where+'.excluded_speakers',utterance_ids=[],speaker_ids=excluded,
                              audio_hashes={},audio_paths=[],source_aliases=[],prior_recorded_exclusion=True)
    for key in ['source_ids','sample_ids','selected_speakers','selected_source_ids','used_speakers','selected_sources']:
        if isinstance(obj.get(key),list):
            strings=[x for x in obj[key] if isinstance(x,str)]
            selected_ids=sorted({m.group(0) for value in strings for m in UTT.finditer(value)})
            selected_speakers=sorted({m.group(0) for value in strings for m in SPK.finditer(value)}
                                     |{UTT.fullmatch(uid).group(1) for uid in selected_ids})
            if selected_ids or selected_speakers:
                yield dict(pointer=where+'.'+key,utterance_ids=selected_ids,speaker_ids=selected_speakers,
                           audio_hashes={},audio_paths=[],source_aliases=[])
    for key,value in obj.items():
        key=str(key)
        if pool_key(key) or key.lower() in {'reference','transcript','text','prompt','messages','generated_text'}:continue
        keyed=[match.group(0) for match in UTT.finditer(str(key))]
        if keyed:
            keyed_speakers=sorted({UTT.fullmatch(uid).group(1) for uid in keyed})
            yield dict(pointer=where+'.'+key,utterance_ids=keyed,speaker_ids=keyed_speakers,
                       audio_hashes={},audio_paths=[],source_aliases=keyed)
            yield from inspect_object(value,where+'.'+key,keyed,keyed_speakers)
        else:yield from inspect_object(value,where+'.'+key,ids,speakers)


def candidates(root,exclude):
    root=Path(root)
    if not root.exists():return
    def denied(error):raise error
    for here,dirs,files in os.walk(root,onerror=denied):
        dirs[:]=sorted(d for d in dirs if d not in {'.git','__pycache__','.pytest_cache','node_modules'}
                       and not d.lower().startswith(('pytest','cpu_tmp','tmp_')))
        here=Path(here)
        if any(here.resolve().is_relative_to(Path(p).resolve()) for p in exclude):dirs[:]=[];continue
        for name in sorted(files):
            path=here/name
            if path.suffix.lower() not in {'.json','.csv','.tsv'}:continue
            if path.is_symlink():continue
            yield path


def parse_metadata(path):
    if path.suffix.lower()=='.json':return read(path)
    with path.open(encoding='utf8',newline='') as f:return list(csv.DictReader(f,delimiter='\t' if path.suffix.lower()=='.tsv' else ','))


def extract_lineage(obj):
    extracted=list(inspect_object(obj))
    for record in extracted:
        if record['audio_paths'] and not record['utterance_ids']:
            children=[other for other in extracted if other['pointer'].startswith(record['pointer']+'.')
                      or other['pointer'].startswith(record['pointer']+'[')]
            record['utterance_ids']=sorted({uid for child in children for uid in child['utterance_ids']})
            record['speaker_ids']=sorted(set(record['speaker_ids'])|{speaker for child in children for speaker in child['speaker_ids']})
    return extracted


def lineage_keys(record):
    keys=['path:'+p for p in record['audio_paths']]
    keys+=['alias:'+alias if UTT.search(alias) else 'file-alias:'+record['origin_sha256']+':'+alias
           for alias in record['source_aliases']]
    keys+=['hash:'+value for value in record['audio_hashes'].values()]
    return keys


def resolve_lineage(observations):
    parent={}
    def find(key):
        parent.setdefault(key,key)
        while parent[key]!=key:
            parent[key]=parent[parent[key]];key=parent[key]
        return key
    for record in observations:
        keys=lineage_keys(record)
        if keys:
            for key in keys[1:]:parent[find(key)]=find(keys[0])
    labels=collections.defaultdict(set)
    for record in observations:
        keys=lineage_keys(record)
        if keys:labels[find(keys[0])].update(record['utterance_ids']+record['speaker_ids'])
    for record in observations:
        keys=lineage_keys(record);resolved=labels[find(keys[0])] if keys else set()
        record['utterance_ids']=sorted(set(record['utterance_ids'])|{x for x in resolved if UTT.fullmatch(x)})
        record['speaker_ids']=sorted(set(record['speaker_ids'])|{x for x in resolved if re.fullmatch(r'S\d{4}',x)})
    return observations


def run(args):
    identity=verify_source(Path(__file__).parent,args.manifest);cfg=read(args.config)
    stream=bool(getattr(args,'stream_bundle',False))
    need(not stream or args.phase=='local_history','RAM stream mode is only for true Windows/local-history execution')
    phase=cfg['phases'][args.phase];out=MemoryPath(args.out) if stream else Path(args.out)
    if stream:args._stream_output=out
    need(not out.exists(),'do not overwrite census output');out.mkdir(parents=True)
    put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),new_model_calls=0))
    put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id']+'_'+args.phase,code_commit=identity['source_commit'],
        source_manifest_sha256=identity['manifest_sha256'],frozen_config=str(args.config),frozen_config_sha256=sha(args.config),
        environment_record=str(out/'ENVIRONMENT.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),
        raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    inputs=[];observations=[];errors=[];seen={};family_counts=collections.Counter();catalogs=[];skipped=[];optional_missing=[];discovered=set()
    for family in phase['roots']:
        root=Path(family['path'])
        if not root.exists():
            item=dict(family=family['family'],path=str(root),reason='configured_root_missing',required=family.get('required',True))
            (errors if family.get('required',True) else optional_missing).append(item);continue
        for path in candidates(root,phase.get('excluded_roots',[])):
            discovered.add(str(path))
            if path.name.lower()=='reference.json':
                catalogs.append(dict(path=str(path),bytes=path.stat().st_size,family=family['family'],
                                     scope='Reference corpus not read or hashed before new metadata selection'))
                continue
            if path.stat().st_size>cfg.get('maximum_generic_metadata_bytes',25_000_000) and not any(
                key in path.name.lower() for key in ['config','manifest','source_receipt','plan','selection','sources','session']):
                skipped.append(dict(path=str(path),bytes=path.stat().st_size,family=family['family'],reason='large_nonidentity_neural_or_artifact_payload_not_metadata'));continue
            digest=sha(path);row=dict(path=str(path),bytes=path.stat().st_size,sha256=digest,family=family['family'])
            inputs.append(row);family_counts[family['family']]+=1
            if digest in seen:continue
            seen[digest]=str(path)
            if catalog_file(path):catalogs.append(row);continue
            try:
                raw=path.read_bytes()
                if not any(marker in raw for marker in [b'BAC009S',b'"speaker_id"',b'aishell',b'AISHELL',b'chinese-',b'chinese_']) and not re.search(rb'S\d{4}',raw):continue
                obj=parse_metadata(path)
                extracted=extract_lineage(obj)
                for record in extracted:
                    record.update(origin=str(path),origin_sha256=digest,family=family['family'],evidence_tier=metadata_tier(path))
                observations+=extracted
            except Exception as exc:
                errors.append(dict(path=str(path),family=family['family'],reason='metadata_parse_failed',error=repr(exc)))
    # Resolve renamed/concatenated inputs by common path, alias or exact hash.
    observations=resolve_lineage(observations)
    unresolved=[]
    for record in observations:
        chinese_alias=(str(record.get('language','')).lower() in {'chinese','zh','zh-cn'}
                       or any(re.match(r'^(chinese|zh)[-_]',alias,re.I) for alias in record['source_aliases']))
        if record['audio_paths'] and not record['speaker_ids'] and (chinese_alias or any('aishell' in p.lower() for p in record['audio_paths'])):
            unresolved.append(record)
    exclusions=collections.defaultdict(lambda:dict(utterance_ids=set(),audio_hashes=set(),evidence=[]))
    for record in observations:
        for speaker in record['speaker_ids']:
            item=exclusions[speaker];item['utterance_ids'].update(uid for uid in record['utterance_ids'] if UTT.fullmatch(uid).group(1)==speaker);item['audio_hashes'].update(record['audio_hashes'].values())
            if len(item['evidence'])<30:item['evidence'].append({key:record[key] for key in ['origin','origin_sha256','pointer','family','evidence_tier']})
    excluded=[dict(speaker_id=speaker,utterance_ids=sorted(item['utterance_ids']),audio_hashes=sorted(item['audio_hashes']),evidence=item['evidence'])
              for speaker,item in sorted(exclusions.items())]
    # Full input inventory is stable-checked after the census, not assumed.
    for item in inputs:
        path=Path(item['path'])
        need(path.stat().st_size==item['bytes'] and sha(path)==item['sha256'],'historical metadata changed during census')
    after_paths={str(path) for family in phase['roots'] if Path(family['path']).exists()
                 for path in candidates(family['path'],phase.get('excluded_roots',[]))}
    need(after_paths==discovered,'historical metadata file set changed during census')
    put(out/'INPUT_MANIFEST.json',inputs);put(out/'EXCLUSIONS.json',dict(phase=args.phase,speakers=excluded,
        policy='Conservative historical source/config/plan/receipt evidence; does not assert every tier was neural execution',
        source_identity=identity,metadata_only_catalogs_not_excluded=catalogs))
    with (out/'OBSERVATIONS.jsonl').open('x',encoding='utf8',newline='\n') as stream:
        for record in observations:stream.write(json.dumps(record,ensure_ascii=False)+'\n')
    put(out/'UNRESOLVED.json',unresolved);put(out/'ERRORS.json',errors);put(out/'SKIPPED_NONMETADATA.json',skipped);put(out/'OPTIONAL_ROOTS_MISSING.json',optional_missing)
    verify_source(Path(__file__).parent,args.manifest)
    summary=dict(status='PASS_METADATA_CENSUS' if not errors and not unresolved else 'REVIEW_REQUIRED_METADATA_CENSUS',
        experiment_id=cfg['experiment_id'],phase=args.phase,source_identity=identity,input_files=len(inputs),
        unique_input_content=len(seen),identity_observations=len(observations),excluded_speakers=len(excluded),
        unresolved_AISHELL_aliases=len(unresolved),errors=len(errors),family_file_counts=dict(family_counts),
        metadata_only_catalog_count=len(catalogs),new_model_calls=0,reference_or_performance_used_for_selection=False,
        input_SHA_before_after_equal=True,exclusion_sha256=sha(out/'EXCLUSIONS.json'),
        observations_sha256=sha(out/'OBSERVATIONS.jsonl'),unresolved_sha256=sha(out/'UNRESOLVED.json'))
    put(out/'SUMMARY.json',summary);put(out/'GATE.json',summary)
    if stream:
        sys.stdout.buffer.write(out.zip_bytes());sys.stdout.buffer.flush()
    else:print(json.dumps(summary))
    return 0 if not errors else 2


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--phase',required=True);p.add_argument('--out',required=True);p.add_argument('--stream-bundle',action='store_true')
    args=p.parse_args()
    try:result=run(args)
    except Exception as exc:
        memory=getattr(args,'_stream_output',None)
        if memory is not None:
            put(memory/'FAILURE.json',dict(status='FAIL_METADATA_CENSUS_PRESERVED',error=repr(exc),traceback=traceback.format_exc(),actual_platform=platform.platform(),new_model_calls=0))
            if not (memory/'GATE.json').exists():put(memory/'GATE.json',dict(status='FAIL_METADATA_CENSUS_PRESERVED',error_type=type(exc).__name__,new_model_calls=0))
            sys.stdout.buffer.write(memory.zip_bytes());sys.stdout.buffer.flush()
            sys.stderr.write(traceback.format_exc());result=2
        else:raise
    raise SystemExit(result)
