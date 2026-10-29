"""Select using only archive paths/speakers/uncompressed sizes, never content."""
import argparse,datetime,hashlib,json,pathlib,platform,random,subprocess
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def choose(entries,*,seed,excluded):
    wav=[x for x in entries if '/aishell1_testset/' in x['path'] and x['path'].endswith('.wav')]
    assert len({x['path'] for x in wav})==len(wav)
    bands=[];selected_band=None;pool=None
    for high in (9,10,15):
        eligible=[dict(x,source_id=pathlib.PurePosixPath(x['path']).stem,speaker_id=pathlib.PurePosixPath(x['path']).stem[6:11],estimated_duration_seconds=(x['bytes']-44)/32000) for x in wav
          if 8*32000+44<=x['bytes']<=high*32000+44 and pathlib.PurePosixPath(x['path']).stem[6:11] not in excluded]
        speakers=sorted({x['speaker_id'] for x in eligible});bands.append(dict(estimated_seconds=[8,high],eligible_members=len(eligible),eligible_speakers=speakers))
        if len(speakers)>=4:selected_band=[8,high];pool=sorted(eligible,key=lambda x:x['path']);break
    if pool is None:raise ValueError('fewer than four speaker-disjoint eligible speakers even after predeclared15s widen')
    rng=random.Random(seed);speakers=rng.sample(sorted({x['speaker_id'] for x in pool}),4);selected=[]
    for speaker in speakers:
        candidates=sorted([x for x in pool if x['speaker_id']==speaker],key=lambda x:x['path']);index=rng.randrange(len(candidates))
        # Initial member uniform among sorted speaker candidates; only technical
        # header rejection may advance lexicographically, wrapping once.
        priority=candidates[index:]+candidates[:index]
        selected.append(dict(speaker_id=speaker,initial_source_id=priority[0]['source_id'],initial_uniform_candidate_index=index,
          candidate_count=len(candidates),technical_fallback_order=priority))
    return dict(considered_bands=bands,selected_estimated_duration_band=selected_band,eligible_pool=pool,selected=selected)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--rule',type=pathlib.Path,required=True);a=ap.parse_args();cfg=read(a.rule)
    src=pathlib.Path(__file__).resolve().parent;commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()
    assert commit==cfg['selection_source_commit'] and not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
    assert sha(cfg['archive_index'])==cfg['archive_index_sha256'] and sha(cfg['method_freeze'])==cfg['method_freeze_sha256']
    method=read(cfg['method_freeze']);assert method['method_source_commit']==cfg['method_source_commit'] and method['no_new_source_metadata_selected_yet']
    result=choose(read(cfg['archive_index']),seed=cfg['seed'],excluded=set(cfg['excluded_speakers']))
    result.update(experiment_id=cfg['experiment_id'],status='PASS_METADATA_ONLY_SELECTION_FROZEN_BEFORE_CONTENT',
      selection_created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),selection_source_commit=commit,
      method_source_commit=cfg['method_source_commit'],method_freeze_sha256=cfg['method_freeze_sha256'],
      metadata_only_before_neural=True,archive_index_sha256=cfg['archive_index_sha256'],
      archive_public_url=cfg['archive_public_url'],seed=cfg['seed'],excluded_speakers=cfg['excluded_speakers'],
      reference_read=False,WAV_bytes_read=False,model_calls=0,rule_sha256=sha(a.rule))
    out=pathlib.Path(cfg['selection_output']);assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    env=dict(python=platform.python_version(),platform=platform.platform(),model_calls=0,gpu_calls=0)
    out.with_name('SELECTION_ENVIRONMENT_v1.json').write_text(json.dumps(env,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],band=result['selected_estimated_duration_band'],eligible=len(result['eligible_pool']),
      selected=[dict(speaker_id=x['speaker_id'],source_id=x['initial_source_id']) for x in result['selected']],selection_sha256=sha(out))))
if __name__=='__main__':main()
