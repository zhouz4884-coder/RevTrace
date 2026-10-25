"""Freeze genuinely unconsumed audio before any V6 development GPU result."""
from pathlib import Path
import argparse,hashlib,json,re,random
import soundfile as sf
import numpy as np
ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);a=ap.parse_args();B=a.base
O=B/'results/revtrace/ces_v6_abcd_20261025';D=O/'heldout_source_v1';assert not D.exists();D.mkdir()
old_hash=set();old_ids=set();manifests=[]
def inspect(x):
 if isinstance(x,dict):
  for key in ['audio_sha256','waveform_sha256']:
   if isinstance(x.get(key),str):old_hash.add(x[key])
  if isinstance(x.get('source_id'),str):old_ids.add(x['source_id'])
  for value in x.values():
   if isinstance(value,(list,dict)):inspect(value)
 elif isinstance(x,list):
  for v in x:
   if isinstance(v,(list,dict)):inspect(v)
roots=[B/'results/revtrace',B/'datasets/revtrace',B/'datasets/tc_live_20260906']
for root in roots:
 for p in root.rglob('*.json'):
  if O in p.parents or 'linux_cpu_tmp' in str(p) or p.stat().st_size>5_000_000:continue
  n=p.name.lower()
  if n not in ['sessions.json','manifest.json','source_manifest.json'] and not any(q in n for q in ['manifest','source','holdout']):continue
  try:x=json.loads(p.read_text())
  except (ValueError,UnicodeError):continue
  inspect(x);manifests.append({'path':str(p.relative_to(B)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
speakers={x.split('-')[0] for x in old_ids if re.match(r'^\d+-\d+-\d+$',x)}
corpora=[B/'datasets/revtrace/librispeech_dev/LibriSpeech/dev-clean',B/'datasets/revtrace/librispeech/LibriSpeech/test-clean',B/'datasets/revtrace/librispeech_dev/LibriSpeech/dev-other']
pool=[]
for corpus in corpora:
 for trans in sorted(corpus.rglob('*.trans.txt')):
  for line in trans.read_text().splitlines():
   sid,ref=line.split(' ',1);p=trans.parent/(sid+'.flac')
   if not p.exists() or sid in old_ids:continue
   info=sf.info(p)
   if info.samplerate!=16000 or not 12.<=info.duration<=20.:continue
   pool.append((sid,ref,p,corpus.name))
rng=random.Random(20261025);rng.shuffle(pool);chosen=[];chosen_speakers=set()
for require_new_speaker in [True,False]:
 for sid,ref,p,split in pool:
  speaker=sid.split('-')[0]
  if speaker in chosen_speakers or (require_new_speaker and speaker in speakers):continue
  audio,rate=sf.read(p,dtype='float32');audio=np.asarray(audio,dtype='<f4');h=hashlib.sha256(audio.tobytes()).hexdigest()
  if h in old_hash:continue
  out=D/(sid+'.wav');sf.write(out,audio,16000,subtype='FLOAT')
  chosen.append({'source_id':sid,'speaker_id':speaker,'reference':ref,'path':str(out),'audio_sha256':h,
    'duration':len(audio)/16000.,'language':'English','original_path':str(p),'corpus_split':split,'speaker_not_previously_observed':speaker not in speakers})
  chosen_speakers.add(speaker)
  if len(chosen)==16:break
 if len(chosen)==16:break
assert len(chosen)==16,'Not enough untouched source audio; do not rename old validation audio'
M=D/'MANIFEST.json';M.write_text(json.dumps({'study':'V6 final confirmation, sealed before development GPU','sessions':chosen},indent=2)+'\n')
report={'status':'FROZEN_UNCONSUMED_AUDIO_SET','sources':16,'prior_source_ids':len(old_ids),'prior_audio_hashes':len(old_hash),
 'speaker_unseen_count':sum(r['speaker_not_previously_observed'] for r in chosen),'audio_hash_disjoint':not ({r['audio_sha256'] for r in chosen}&old_hash),
 'source_id_disjoint':not ({r['source_id'] for r in chosen}&old_ids),'selection':'Metadata-only duration12–20s; no V6 model output used',
 'manifest_sha256':hashlib.sha256(M.read_bytes()).hexdigest(),'scanned_manifests':manifests,'new_GPU_calls':0}
(O/'SOURCE_EXPOSURE_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='scanned_manifests'}))
