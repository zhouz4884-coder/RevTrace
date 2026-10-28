"""CPU-only exact complete-utterance crop materialization on the 8 TB disk.

No model, tokenization, ASR, transcript truncation or outcome selection. Run from
its own clean committed source package with an external complete byte manifest.
"""
from pathlib import Path
import argparse,hashlib,importlib.metadata,json,math,platform,re,shutil,subprocess,sys,traceback

B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as stream:
        for data in iter(lambda:stream.read(4194304),b''):h.update(data)
    return h.hexdigest()
def put(p,v):
    with Path(p).open('x',encoding='utf8') as stream:json.dump(v,stream,indent=2,allow_nan=False);stream.write('\n')
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
def check_source(manifest_path):
    root=Path(__file__).resolve().parent;manifest=read(manifest_path);commit=manifest['code_commit']
    if not re.fullmatch('[0-9a-f]{40}',commit) or git(root,'rev-parse','HEAD')!=commit or git(root,'cat-file','-t',commit)!='commit':raise ValueError('full clean CPU source commit required')
    if git(root,'status','--porcelain','--untracked-files=all') or git(root,'config','--get','core.autocrlf')!='false':raise ValueError('CPU source dirty or byte conversion enabled')
    if set(git(root,'ls-files','-z').split('\0'))-{''}!={r['path'] for r in manifest['files']}:raise ValueError('complete CPU source file inventory differs')
    for row in manifest['files']:
        p=root/row['path']
        if not p.resolve().is_relative_to(root) or p.is_symlink() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise ValueError('CPU source byte mismatch')
    return manifest

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['selection','parent','reference-metadata','plan','source-manifest','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();selection=read(a.selection);parent=read(a.parent);refs=read(a.reference_metadata);plan=read(a.plan)
    source=check_source(a.source_manifest);out=a.out.resolve();data=Path(selection['dataset_output_root']).resolve()
    if out.exists() or data.exists():raise FileExistsError('never overwrite CPU inputs or audio assets')
    if not out.is_relative_to(B/'results/revtrace/physical_retirement_20261028') or not data.is_relative_to(B/'datasets/revtrace/composition_confirmation_20261028'):raise ValueError('designated8TB locations only')
    out.mkdir(parents=True);data.mkdir(parents=True);completed=[]
    try:
        env=dict(python=sys.version,platform=platform.platform(),packages={n:importlib.metadata.version(n) for n in ['numpy','soundfile','pyarrow']},model_imports=0,ASR_model_calls=0)
        put(out/'ENVIRONMENT.json',env)
        inputs={name:dict(path=str(getattr(a,name)),sha256=sha(getattr(a,name))) for name in ['selection','parent','reference_metadata','plan','source_manifest']}
        config=dict(selection_rule=selection['selection_rule'],inputs=inputs,data_output_root=str(data),cohorts=plan['cohorts'],sample_rate=16000,ASR_model_calls=0)
        put(out/'CONFIG.json',config)
        put(out/'FREEZE.json',dict(experiment_id='REVTRACE-COMPOSITION-UTTERANCE-ASSET-PREP-20261028',code_commit=source['code_commit'],
          source_manifest_sha256=sha(a.source_manifest),source_script_sha256=sha(Path(__file__)),frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),
          environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),
          raw_result_location=str(data),aggregate_summary_location=str(out/'MANIFEST.json'),gate_decision_location=str(out/'GATE.json'),ASR_model_calls=0))
        for name in ['selection','parent','reference_metadata','plan','source_manifest']:
            shutil.copyfile(getattr(a,name),out/(name.upper()+'.json'))
        if sha(a.parent)!=selection['parent_manifest_sha256'] or sha(a.parent)!=refs['parent_manifest_sha256']:raise ValueError('frozen parent identity')
        if refs['history_registry_sha256']!=parent['history_registry_sha256']:raise ValueError('historical registry identity')
        import numpy as np,soundfile as sf,pyarrow.parquet as pq
        wanted={u['id'] for s in selection['sessions'] for u in s['utterances']};exact={};shards=[]
        for descriptor in parent['dataset_spec']['files']:
            path=B/'datasets/revtrace/context_holdout_20261028/parquet'/descriptor['name']
            if path.stat().st_size!=descriptor['bytes'] or sha(path)!=descriptor['sha256']:raise ValueError('frozen Parquet bytes changed')
            shards.append(dict(path=str(path),sha256=descriptor['sha256'],bytes=descriptor['bytes']))
            for batch in pq.ParquetFile(path).iter_batches(batch_size=512,columns=['id','text']):
                for row in batch.to_pylist():
                    if row['id'] in wanted:
                        if row['id'] in exact:raise ValueError('duplicate reference ID')
                        exact[row['id']]=row['text']
        if set(exact)!=wanted:raise ValueError('missing exact utterance references')
        original={s['source_id']:s for s in parent['sessions']};first={}
        for s in parent['sessions']:first.setdefault(s['speaker'],s['source_id'])
        if len(selection['sessions'])!=24 or len({s['speaker'] for s in selection['sessions']})!=24:raise ValueError('24 independent speakers required')
        histories=set(map(str,refs['historical_source_ids']));speakers=set(map(str,refs['historical_speaker_ids']))
        for s in selection['sessions']:
            if s['speaker'] in speakers or any(u['id'] in histories for u in s['utterances']):raise ValueError('historical overlap')
            parent_row=original[s['parent_source_id']]
            if first[s['speaker']]!=s['parent_source_id']:raise ValueError('not first frozen parent of speaker')
            candidates=[]
            for i,u in enumerate(parent_row['utterances']):
                for j,v in enumerate(parent_row['utterances'][i:],i):
                    count=v['end']-u['start']
                    if 400000<=count<=560000:candidates.append((abs(count-480000),i,j,u['start'],v['end']))
            best=min(candidates)
            if (s['parent_start_sample'],s['parent_end_sample'])!=(best[3],best[4]):raise ValueError('metadata duration rule differs')
            units=parent_row['utterances'][best[1]:best[2]+1]
            if [u['id'] for u in s['utterances']]!=[u['id'] for u in units]:raise ValueError('complete utterance selection differs')
            ref=' '.join(exact[u['id']] for u in units)
            if ref!=s['reference'] or any(u['text']!=exact[u['id']] for u in s['utterances']):raise ValueError('reference text is not exact full utterances')
            parent_path=Path(s['parent_path'])
            if sha(parent_path)!=s['parent_file_sha256']:raise ValueError('original90s file changed')
            audio,rate=sf.read(parent_path,dtype='float32')
            audio=np.asarray(audio,dtype='<f4')
            if rate!=16000 or audio.ndim!=1 or len(audio)!=90*16000 or hashlib.sha256(audio.tobytes()).hexdigest()!=s['parent_audio_sha256']:raise ValueError('original90s decoded sample identity')
            utterance_records=[]
            for u in s['utterances']:
                original_path=Path(u['original_encoded_path'])
                if sha(original_path)!=u['source_sha256']:raise ValueError('complete original utterance encoded identity')
                raw,raw_rate=sf.read(original_path,dtype='float32');raw=np.asarray(raw,dtype='<f4')
                if raw_rate!=16000 or len(raw)!=u['end']-u['start'] or not np.array_equal(raw,audio[u['start']:u['end']]):raise ValueError('utterance/boundary sample mismatch')
                utterance_records.append(dict(id=u['id'],original_start=u['start'],original_end=u['end'],
                  start=u['relative_start'],end=u['relative_end'],source_sha256=u['source_sha256'],reference=exact[u['id']]))
            cropped=np.asarray(audio[s['parent_start_sample']:s['parent_end_sample']],dtype='<f4')
            path=Path(s['intended_path'])
            if path.parent!=data or path.exists() or not 25*16000<=len(cropped)<=35*16000:raise ValueError('invalid new output identity')
            sf.write(path,cropped,16000,format='WAV',subtype='FLOAT')
            actual,actual_rate=sf.read(path,dtype='float32');actual=np.asarray(actual,dtype='<f4')
            if actual_rate!=16000 or not np.array_equal(cropped,actual):raise ValueError('lossy crop serialization')
            completed.append(dict(source_id=s['source_id'],speaker=s['speaker'],chapter=s['chapter'],path=str(path),language='English',
              duration=len(actual)/16000,reference=ref,audio_sha256=hashlib.sha256(actual.tobytes()).hexdigest(),file_sha256=sha(path),
              parent_source_id=s['parent_source_id'],parent_audio_sha256=s['parent_audio_sha256'],parent_file_sha256=s['parent_file_sha256'],
              parent_start_sample=s['parent_start_sample'],parent_end_sample=s['parent_end_sample'],utterances=utterance_records,
              grouping=s['grouping'],ASR_evaluated=False))
        if len({s['audio_sha256'] for s in completed})!=24:raise ValueError('duplicate resulting audio')
        manifest=dict(status='FROZEN_COMPLETE_UTTERANCE_CROPS_NOT_ASR_EVALUATED',sessions=completed,
          parent_manifest_sha256=sha(a.parent),selection_sha256=sha(a.selection),reference_metadata_sha256=sha(a.reference_metadata),
          source_commit=source['code_commit'],source_script_sha256=sha(Path(__file__)),history_registry_sha256=parent['history_registry_sha256'],
          source_speakers=24,unique_audio_seconds=sum(s['duration'] for s in completed),
          historical_utterance_overlap=0,historical_speaker_overlap=0,ASR_model_calls=0,
          model_pretraining_exposure='UNKNOWN_NOT_CLAIMED',independent_clustering_unit='speaker; paired windows/repeats are dependent')
        put(out/'MANIFEST.json',manifest);put(out/'PARQUET_IDENTITY.json',shards)
        for cohort in plan['cohorts']:
            rows=[s for sid in cohort['source_ids'] for s in completed if s['source_id']==sid]
            if len(rows)!=8 or len({r['speaker'] for r in rows})!=8:raise ValueError('disjoint8speaker cohort')
            put(out/('COHORT_'+cohort['cohort']+'.json'),dict(sessions=rows,cohort=cohort['cohort'],
              selection='predeclared round-robin metadata source blocks',full_manifest_sha256=sha(out/'MANIFEST.json'),ASR_model_calls=0))
        put(out/'SUMMARY.json',dict(status=manifest['status'],source_commit=source['code_commit'],streams=24,speakers=24,
          audio_seconds=manifest['unique_audio_seconds'],utterances=len(wanted),audio_bytes=sum(Path(s['path']).stat().st_size for s in completed),
          manifest_sha256=sha(out/'MANIFEST.json'),cohort_manifests={co['cohort']:dict(path=str(out/('COHORT_'+co['cohort']+'.json')),sha256=sha(out/('COHORT_'+co['cohort']+'.json'))) for co in plan['cohorts']},
          ASR_model_calls=0))
        put(out/'GATE.json',dict(gate='PASS_CPU_EXACT_UTTERANCE_ASSET_FREEZE_NO_ASR',manifest_sha256=sha(out/'MANIFEST.json'),
          source_commit=source['code_commit'],all_parent_and_complete_utterance_sample_checks=True,ASR_model_calls=0))
        print(json.dumps(read(out/'SUMMARY.json'),allow_nan=False))
    except BaseException:
        put(out/'STOP.json',dict(error=traceback.format_exc(),completed_sources=[s['source_id'] for s in completed],ASR_model_calls=0))
        if not (out/'GATE.json').exists():put(out/'GATE.json',dict(gate='NO_GO_CPU_ASSET_FREEZE_FAILURE_PRESERVED',ASR_model_calls=0))
        raise

if __name__=='__main__':main()
