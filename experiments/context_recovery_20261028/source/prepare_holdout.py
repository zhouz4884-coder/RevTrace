"""Metadata-only prospective holdout, fixed public bytes and no ASR execution."""
from pathlib import Path
import argparse,hashlib,importlib.metadata,io,json,os,platform,sys,time,traceback,urllib.error,urllib.request


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4194304),b''):h.update(b)
    return h.hexdigest()


def plans(records,seen_ids,seen_speakers,config):
    groups={};excluded=[]
    for r in records:
        if r['id'] in seen_ids or str(r['speaker_id']) in seen_speakers:
            excluded.append(r['id']);continue
        groups.setdefault((str(r['speaker_id']),str(r['chapter_id'])),[]).append(r)
    chosen=[];speakers=set()
    for (speaker,chapter),rows in sorted(groups.items(),key=lambda x:(int(x[0][0]),int(x[0][1]))):
        if speaker in speakers:continue
        rows=sorted(rows,key=lambda r:int(r['id'].rsplit('-',1)[1]));sessions=[];current=[];seconds=0.
        for r in rows:
            extra=r['duration']+(config['separator_seconds'] if current else 0.)
            if current and seconds+extra>config['target_seconds']:
                if seconds<config['minimum_seconds']:break
                sessions.append(current);current=[];seconds=0.;extra=r['duration']
                if len(sessions)==config['sessions_per_speaker']:break
            if extra>config['target_seconds']:break
            current.append(r);seconds+=extra
        if len(sessions)<config['sessions_per_speaker'] and seconds>=config['minimum_seconds']:sessions.append(current)
        if len(sessions)==config['sessions_per_speaker']:
            chosen.append(dict(speaker=speaker,chapter=chapter,sessions=sessions));speakers.add(speaker)
        if len(chosen)==config['speakers']:break
    return chosen,excluded


def download(row,spec,directory,log):
    dest=directory/row['name']
    if dest.exists():
        assert dest.stat().st_size==row['bytes'] and sha(dest)==row['sha256'];return dest
    base='datasets/'+spec['dataset']+'/resolve/'+spec['revision']+'/'+spec['split']+'/'+row['name']
    for attempt,host in enumerate(['https://huggingface.co/','https://hf-mirror.com/']):
        url=host+base;part=directory/(row['name']+f'.attempt{attempt}.partial');assert not part.exists()
        started=time.monotonic();written=0;h=hashlib.sha256()
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'RevTrace-research-data-freeze/1.0'})
            with urllib.request.urlopen(request,timeout=45) as response,part.open('xb') as f:
                while True:
                    b=response.read(1048576)
                    if not b:break
                    f.write(b);h.update(b);written+=len(b)
                    if time.monotonic()-started>600:raise TimeoutError('bounded public download exceeded600s')
            assert written==row['bytes'] and h.hexdigest()==row['sha256'],'public artifact identity mismatch'
            part.rename(dest);log.append(dict(url=url,status='MATCHED_PRIMARY_SHA256',bytes=written,seconds=time.monotonic()-started));return dest
        except Exception as e:
            log.append(dict(url=url,status='FAILED_PRESERVED',error_type=type(e).__name__,http_status=getattr(e,'code',None),bytes=written,seconds=time.monotonic()-started))
            # No signed redirect URL or response body enters the record.
    raise RuntimeError('both public download routes failed; partials retained')


def main():
    p=argparse.ArgumentParser();p.add_argument('--data-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--history',type=Path,required=True);p.add_argument('--history-sha256',required=True);p.add_argument('--source-manifest',type=Path,required=True)
    a=p.parse_args();B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
    assert a.data_root.resolve().is_relative_to(B/'datasets/revtrace') and a.out.resolve().is_relative_to(B/'results/revtrace/freeze_boundary_20261027')
    assert not a.out.exists();a.out.mkdir(parents=True);a.data_root.mkdir(parents=True,exist_ok=True)
    specpath=Path(__file__).parent/'holdout_source.json';spec=json.loads(specpath.read_text());source=json.loads(a.source_manifest.read_text())
    for r in source['files']:assert sha(Path(__file__).parent/r['path'])==r['sha256']
    assert sha(a.history)==a.history_sha256;history=json.loads(a.history.read_text())
    def put(n,x):(a.out/n).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
    environment=dict(python=sys.version,platform=platform.platform(),packages={n:importlib.metadata.version(n) for n in ['pyarrow','numpy','soundfile']})
    put('ENVIRONMENT.json',environment);put('FREEZE.json',dict(experiment_id='REVTRACE-UNTOUCHED-CONTEXT-HOLDOUT-20261028',source_commit=source['code_commit'],source_manifest_sha256=sha(a.source_manifest),data_spec=spec,data_spec_sha256=sha(specpath),history_registry_sha256=a.history_sha256,environment_sha256=sha(a.out/'ENVIRONMENT.json'),raw_result_location=str(a.out),aggregate_summary_location=str(a.out/'MANIFEST.json'),gate_decision_location=str(a.out/'GATE.json'),ASR_model_calls=0))
    log=[]
    try:
        import pyarrow.parquet as pq,numpy as np,soundfile as sf
        files=a.data_root/'parquet';files.mkdir(exist_ok=True)
        inputs=[download(r,spec,files,log) for r in spec['files']];put('DOWNLOADS.json',log)
        shard_hashes={p.name:sha(p) for p in inputs}
        records=[];seen=set();raw=a.data_root/'utterances';raw.mkdir(exist_ok=True)
        for file in inputs:
            parquet=pq.ParquetFile(file)
            for batch in parquet.iter_batches(batch_size=32):
                for row in batch.to_pylist():
                    sid=row['id'];assert sid not in seen;seen.add(sid)
                    if sid in history['source_ids'] or str(row['speaker_id']) in history['speaker_ids']:continue
                    b=row['audio']['bytes'];info=sf.info(io.BytesIO(b));assert info.samplerate==16000 and info.channels==1
                    path=raw/(sid+'.flac');h=hashlib.sha256(b).hexdigest()
                    if path.exists():assert sha(path)==h
                    else:
                        with path.open('xb') as f:f.write(b)
                    records.append(dict(id=sid,speaker_id=str(row['speaker_id']),chapter_id=str(row['chapter_id']),duration=info.frames/16000,samples=info.frames,text=row['text'],path=str(path),encoded_sha256=h,shard=file.name,shard_sha256=shard_hashes[file.name]))
        groups,excluded=plans(records,set(history['source_ids']),set(history['speaker_ids']),spec['selection'])
        assert len(groups)==spec['selection']['speakers'],'insufficient untouched metadata groups; do not change rule after model outcomes'
        directory=a.data_root/'sessions';directory.mkdir(exist_ok=True);sessions=[];utterances=set()
        for group in groups:
            for index,rows in enumerate(group['sessions']):
                pieces=[];positions=[];cursor=0
                for r in rows:
                    assert r['id'] not in utterances;utterances.add(r['id'])
                    if pieces:pieces.append(np.zeros(1600,dtype='<f4'));cursor+=1600
                    x,rate=sf.read(r['path'],dtype='float32');assert rate==16000 and len(x)==r['samples'];pieces.append(x)
                    positions.append(dict(id=r['id'],start=cursor,end=cursor+len(x),source_sha256=r['encoded_sha256']));cursor+=len(x)
                target=90*16000;assert cursor<=target
                if cursor<target:pieces.append(np.zeros(target-cursor,dtype='<f4'))
                audio=np.asarray(np.concatenate(pieces),dtype='<f4');assert len(audio)==target
                name=f"holdout-{group['speaker']}-{group['chapter']}-{index}";path=directory/(name+'.wav');assert not path.exists()
                sf.write(path,audio,16000,format='WAV',subtype='FLOAT');actual,rate=sf.read(path,dtype='float32')
                assert np.array_equal(actual,audio),'lossy assembly conversion'
                sessions.append(dict(source_id=name,speaker=group['speaker'],chapter=group['chapter'],path=str(path),language='English',duration=90.,reference=' '.join(r['text'] for r in rows),audio_sha256=hashlib.sha256(audio.tobytes()).hexdigest(),file_sha256=sha(path),utterances=positions,grouping='chronological same-speaker/chapter reconstructed utterances,0.1s separators; not original uninterrupted recording',ASR_evaluated=False))
        manifest=dict(status='FROZEN_UNTOUCHED_NOT_MODEL_EVALUATED',dataset_spec=spec,source_commit=source['code_commit'],sessions=sessions,unique_speakers=len(groups),independent_clustering_unit='speaker/chapter, two sessions are not two independent speakers',history_registry_sha256=a.history_sha256,unique_utterances=len(utterances),historical_utterance_overlap=0,historical_speaker_overlap=0,ASR_model_calls=0,unseen_in_model_pretraining='UNKNOWN_NOT_CLAIMED')
        put('MANIFEST.json',manifest);put('GATE.json',dict(gate='PASS_PROSPECTIVE_FREEZE',sessions=len(sessions),speakers=len(groups),manifest_sha256=sha(a.out/'MANIFEST.json'),ASR_model_calls=0))
        print(json.dumps(dict(status=manifest['status'],sessions=len(sessions),speakers=len(groups),utterances=len(utterances))))
    except BaseException:
        put('STOP.json',dict(error=traceback.format_exc(),downloads=log));raise


if __name__=='__main__':main()
