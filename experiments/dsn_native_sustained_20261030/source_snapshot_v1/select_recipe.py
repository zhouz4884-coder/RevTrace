"""Freeze speaker-disjoint synthetic long input from archive metadata only."""
import argparse,datetime,pathlib,random,sys,platform
from data_common import read,put,sha,verify_source

EXCLUDED=('S0764','S0765','S0767','S0768','S0908','S0916','S0913','S0905')

def select(entries,*,seed,speakers=2,members=24,excluded=EXCLUDED):
 if (speakers,members)!=(2,24):raise ValueError('this fixed study requires two speakers and24 utterances each')
 pool=[]
 for row in entries:
  path=pathlib.PurePosixPath(row['path']);sid=path.stem;speaker=sid[6:11]
  if '/aishell1_testset/' in row['path'] and row['path'].endswith('.wav') and speaker not in excluded and 8*32000+44<=row['bytes']<=12*32000+44:
   pool.append(dict(row,source_id=sid,speaker_id=speaker,estimated_duration_seconds=(row['bytes']-44)/32000))
 if len({x['path'] for x in pool})!=len(pool):raise ValueError('duplicate metadata member')
 pool=sorted(pool,key=lambda x:x['path']);eligible=sorted({x['speaker_id'] for x in pool if sum(y['speaker_id']==x['speaker_id'] for y in pool)>=members})
 if len(eligible)<speakers:raise ValueError('insufficient fixed-band unused speakers; no widening')
 rng=random.Random(seed);chosen=rng.sample(eligible,speakers);recipes=[]
 for speaker in chosen:
  candidates=[x for x in pool if x['speaker_id']==speaker];picked=rng.sample(candidates,members)
  recipes.append(dict(stream_id='SC_SYNTH_'+speaker+'_24UTT_V1',speaker_id=speaker,members=picked,technical_fallback='none; invalid header/CRC stops; transport may only retry the same range',estimated_seconds=sum(x['estimated_duration_seconds'] for x in picked),synthetic_concatenated_utterances=True))
 return dict(eligible_speakers=eligible,eligible_pool=pool,recipes=recipes,selected_speakers=chosen)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',type=pathlib.Path,required=True);ap.add_argument('--manifest',type=pathlib.Path,required=True);a=ap.parse_args();cfg=read(a.config)
 identity=verify_source(pathlib.Path(__file__).resolve().parent,a.manifest,cfg['selection_source_commit'])
 if sha(cfg['archive_index'])!=cfg['archive_index_sha256']:raise ValueError('archive index changed')
 result=select(read(cfg['archive_index']),seed=cfg['seed'])
 result.update(experiment_id=cfg['experiment_id'],status='PASS_FIXED_METADATA_SYNTHETIC_LONG_RECIPE_BEFORE_AUDIO',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),selection_source_identity=identity,selection_source_commit=cfg['selection_source_commit'],selection_rule_sha256=sha(a.config),archive_index_sha256=sha(cfg['archive_index']),archive_public_url=cfg['archive_public_url'],seed=cfg['seed'],excluded_speakers=list(EXCLUDED),metadata_only_before_audio=True,new_audio_bytes_read=False,new_reference_text_read=False,new_neural_calls=0,predecessor_neural_method_commit=cfg['predecessor_neural_method_commit'],new_runtime_frozen_before_selection=False,scope='Metadata-selected synthetic input, not natural continuous recording; final runtime will be frozen separately before inference.')
 out=pathlib.Path(cfg['selection_output'])
 if out.exists():raise ValueError('refuse to overwrite frozen selection')
 put(out,result);put(out.with_name('SELECTION_ENVIRONMENT_v1.json'),dict(python=sys.version,executable=sys.executable,platform=platform.platform(),new_neural_calls=0,new_audio_bytes_read=False))
 print({'status':result['status'],'selection_sha256':sha(out),'speakers':result['selected_speakers'],'members':sum(len(r['members']) for r in result['recipes'])})
if __name__=='__main__':main()
