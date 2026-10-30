"""Exact selected Range/CRC/header acquisition and no-gap PCM concatenation on8TB."""
import argparse,datetime,hashlib,json,pathlib,platform,sys,urllib.request
from data_common import read,put,sha,verify_source,extract_member,inspect_wave,joined_wave

def fetch(url,entry):
 begin=entry['local_offset'];length=entry['compressed']+4096;end=begin+length-1
 request=urllib.request.Request(url,headers={'Range':f'bytes={begin}-{end}'})
 with urllib.request.urlopen(request,timeout=45) as response:
  if response.status!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {begin}-{end}/'):raise ValueError('official server did not honor exact bounded Range')
  raw=response.read(length+1)
 if len(raw)!=length:raise ValueError('Range length differs')
 return raw

def source_references(rows):
 result={}
 for row in rows:
  sid=pathlib.PurePosixPath(row.get('audio_path','')).stem;text=row.get('text_zh','')
  if sid and text:
   if sid in result and result[sid]!=text:raise ValueError('conflicting reference')
   result[sid]=text
 return result

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',type=pathlib.Path,required=True);ap.add_argument('--manifest',type=pathlib.Path,required=True);a=ap.parse_args();cfg=read(a.config)
 identity=verify_source(pathlib.Path(__file__).resolve().parent,a.manifest,cfg['source_commit'])
 selection=read(cfg['selection'])
 if sha(cfg['selection'])!=cfg['selection_sha256'] or not selection['metadata_only_before_audio'] or selection['new_audio_bytes_read'] or selection['new_neural_calls']!=0:raise ValueError('selection not frozen before audio')
 recipes=selection['recipes']
 if len(recipes)!=2 or any(len(r['members'])!=24 for r in recipes) or len({r['speaker_id'] for r in recipes})!=2:raise ValueError('fixed2x24 recipe differs')
 if len({e['source_id'] for r in recipes for e in r['members']})!=48:raise ValueError('duplicate selected member')
 B=pathlib.Path(cfg['designated_disk']);out=pathlib.Path(cfg['out']);dataset=pathlib.Path(cfg['dataset_root'])
 if not out.resolve().is_relative_to(B) or not dataset.resolve().is_relative_to(B):raise ValueError('large data outside designated8TB')
 out.mkdir(exist_ok=False);(out/'ranges').mkdir();(dataset/'parts').mkdir(parents=True,exist_ok=True);(dataset/'audio').mkdir(exist_ok=True)
 put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),model_calls=0,gpu_calls=0))
 put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=cfg['source_commit'],frozen_config=str(a.config),frozen_config_sha256=sha(a.config),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 parts=[];sources=[];attempts=[]
 try:
  if sha(cfg['reference_metadata'])!=cfg['reference_metadata_sha256']:raise ValueError('official reference metadata changed')
  references=source_references(read(cfg['reference_metadata']))
  for recipe in recipes:
   pcms=[];manifest=[];offset=0
   for entry in recipe['members']:
    sid=entry['source_id'];stage=cfg.get('staged_ranges',{}).get(sid);raw=None
    if stage:
     p=pathlib.Path(stage['path']);begin=entry['local_offset'];end=begin+entry['compressed']+4095
     if not p.resolve().is_relative_to(B) or stage['public_source']!=selection['archive_public_url'] or not stage['content_range'].startswith(f'bytes {begin}-{end}/'):raise ValueError('staged Range provenance differs')
     raw=p.read_bytes()
     if len(raw)!=stage['bytes'] or hashlib.sha256(raw).hexdigest()!=stage['sha256']:raise ValueError('staged Range bytes differ')
    else:
     for attempt in range(3):
      try:raw=fetch(selection['archive_public_url'],entry);break
      except (OSError,TimeoutError) as exc:
       attempts.append(dict(source_id=sid,attempt=attempt,error_type=type(exc).__name__,same_member_retained=True))
     if raw is None:raise RuntimeError('same selected public Range unavailable after3 attempts')
    (out/'ranges'/(sid+'.range')).write_bytes(raw);data=extract_member(raw,entry);header,pcm=inspect_wave(data)
    if sid not in references:raise ValueError('selected source lacks official reference; do not replace it')
    p=dataset/'parts'/(sid+'.wav')
    if p.exists():
     if p.read_bytes()!=data:raise ValueError('existing immutable part differs')
    else:p.write_bytes(data);p.chmod(0o444)
    row=dict(source_id=sid,speaker_id=recipe['speaker_id'],path=str(p),audio_sha256=sha(p),PCM_sha256=header['PCM_sha256'],frames=header['frames'],start_sample=offset,end_sample=offset+header['frames'],header=header,archive_member=entry,reference=references[sid])
    manifest.append(row);parts.append(row);pcms.append(pcm);offset+=header['frames'];put(out/'PROGRESS.json',dict(completed_members=len(parts),target_members=48,completed_streams=len(sources)));print(json.dumps(dict(source_id=sid,completed_members=len(parts),frames=header['frames'])),flush=True)
   data=joined_wave(pcms);header,pcm=inspect_wave(data);path=dataset/'audio'/(recipe['stream_id']+'.wav')
   if header['frames']!=offset or pcm!=b''.join(pcms):raise ValueError('concatenation changed PCM or inserted audio')
   if path.exists():
    if path.read_bytes()!=data:raise ValueError('existing synthetic source differs')
   else:path.write_bytes(data);path.chmod(0o444)
   source=dict(source_id=recipe['stream_id'],speaker_id=recipe['speaker_id'],path=str(path),audio_sha256=sha(path),PCM_sha256=header['PCM_sha256'],frames=offset,duration=offset/16000,reference=' '.join(r['reference'] for r in manifest),synthetic_concatenated_utterances=True,parts=manifest,no_resampling=True,no_inserted_silence=True,no_model_reset_at_part_boundaries=True,only_final_synthetic_EOS=True)
   sources.append(source)
  receipt=dict(status='PASS_FROZEN_TWO_SPEAKER_48_PART_SYNTHETIC_LONG_INPUTS',source_identity=identity,selection_sha256=sha(cfg['selection']),metadata_only_selection=True,sources=sources,unique_acoustic_speakers=2,parts=48,model_calls=0,gpu_calls=0,attempts=attempts,scope='Synthetic same-speaker utterance concatenations; not natural continuous recordings. Selected IDs and order unchanged.')
  put(out/'SOURCE_RECEIPT.json',receipt);put(dataset/'SOURCE_RECEIPT_v1.json',receipt)
  summary=dict(status=receipt['status'],streams=2,parts=48,source_receipt_sha256=sha(out/'SOURCE_RECEIPT.json'),source_frames={s['source_id']:s['frames'] for s in sources},model_calls=0,gpu_calls=0)
  put(out/'SUMMARY.json',summary);put(out/'GATE.json',summary);print(json.dumps(summary),flush=True)
 except BaseException as exc:
  put(out/'FAILURE.json',dict(error_type=type(exc).__name__,completed_parts=len(parts),completed_streams=len(sources),message='Technical/transport/source-identity failure; fixed selected members never replaced.'))
  put(out/'GATE.json',dict(status='FAIL_FROZEN_SYNTHETIC_INPUT_ACQUISITION_PRESERVED',completed_parts=len(parts),model_calls=0,gpu_calls=0));raise
if __name__=='__main__':main()
