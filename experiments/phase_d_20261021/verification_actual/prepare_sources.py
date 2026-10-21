"""Predetermined complete utterances, independent speakers, no outcome selection."""
from pathlib import Path
import json,hashlib,sys
import soundfile as sf,numpy as np
B=Path(sys.argv[1]);O=B/'datasets/revtrace/phaseD_20261021';O.mkdir(exist_ok=False)
root=B/'datasets/revtrace/librispeech/LibriSpeech/test-clean'
speakers=sorted(root.iterdir(),key=lambda p:hashlib.sha256(('PHASE-D-20261021:'+p.name).encode()).hexdigest());records=[]
dev=json.loads((B/'datasets/tc_live_20260906/manifest.json').read_text())
excluded_utterances={x['sample_id'] for s in dev['sessions'] if s['language']=='English' for x in s.get('sources',[])}
excluded_speakers={x.split('-')[0] for x in excluded_utterances}
for speaker in speakers:
 if not speaker.is_dir() or speaker.name in excluded_speakers:continue
 candidates=sorted(speaker.rglob('*.flac'),key=lambda p:hashlib.sha256(('PHASE-D-20261021:'+p.stem).encode()).hexdigest())
 for p in candidates:
  info=sf.info(p)
  if not (16<=info.duration<=28):continue
  textfile=p.parent/(speaker.name+'-'+p.parent.name+'.trans.txt')
  refs=dict(line.split(' ',1) for line in textfile.read_text().splitlines());wav,rate=sf.read(p,dtype='float32');assert rate==16000 and wav.ndim==1
  samples=np.asarray(wav,dtype='<f4');h=hashlib.sha256(samples.tobytes()).hexdigest()
  assert h not in {x['audio_sha256'] for x in dev['sessions']}
  out=O/(p.stem+'.wav');sf.write(out,samples,16000,subtype='FLOAT')
  records.append({'path':str(out),'source_id':p.stem,'speaker':speaker.name,'language':'English','duration':len(samples)/16000,'reference':refs[p.stem],'audio_sha256':h,'original_file':str(p),'original_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'split':'test-clean'})
  break
 if len(records)==16:break
assert len(records)==16 and len({r['speaker'] for r in records})==16
(O/'manifest.json').write_text(json.dumps({'study':'PHASE-D-INDEPENDENT-16-SPEAKERS','selection':'SHA256 PHASE-D-20261021 speaker and utterance order; exclude all 19 original English component speakers; first complete 16–28s utterance per remaining speaker; no ASR outcome used','excluded_original_speakers':sorted(excluded_speakers),'excluded_original_utterances':sorted(excluded_utterances),'sessions':records},indent=2)+'\n')
print(json.dumps({'count':len(records),'audio_seconds':sum(r['duration'] for r in records),'speakers':[r['speaker'] for r in records],'manifest':str(O/'manifest.json')}))
