"""Select native long utterances by headers/IDs only, never ASR outcomes."""
from pathlib import Path
import hashlib,json,re,sys
import soundfile as sf
import numpy as np
B=Path(sys.argv[1]);O=B/'results/revtrace/row_completion_20261023';D=O/'r3_source_v1';D.mkdir(exist_ok=False)
phase=json.loads((B/'datasets/revtrace/phaseD_20261021/manifest.json').read_text())
excluded=set(map(str,phase['excluded_original_speakers']))|{str(r['source_id']).split('-')[0] for r in phase['sessions']}
pilot=json.loads((B/'results/revtrace/online_admission_20261022/PILOT_MANIFEST.json').read_text())
excluded|={r['source_id'].split('-')[0] for r in pilot['sessions']}
roots=[B/'datasets/revtrace'/n for n in ['librispeech','librispeech_dev','librispeech_hf','librispeech_r9_final','librispeech_r9_final2']]
roots+=[B/'datasets/revbatch/qwen_public']
byid={};trans={};considered=0
for root in roots:
 if not root.is_dir():continue
 for p in sorted(root.rglob('*.flac')):
  considered+=1
  if considered>40000:raise ValueError('bounded metadata scan exceeded40000')
  sid=p.stem
  if not re.fullmatch(r'\d+-\d+-\d+',sid) or sid in byid or sid.split('-')[0] in excluded:continue
  if p.parent not in trans:
   table={}
   for t in p.parent.glob('*.trans.txt'):
    for line in t.read_text().splitlines():
     if ' ' in line:
      key,text=line.split(' ',1);table[key]=(text,str(t),hashlib.sha256(t.read_bytes()).hexdigest())
   trans[p.parent]=table
  if sid not in trans[p.parent]:continue
  info=sf.info(p)
  if info.samplerate!=16000 or info.channels!=1 or not 30<=info.duration<=60:continue
  text,tp,th=trans[p.parent][sid]
  byid[sid]={'source_id':sid,'speaker':sid.split('-')[0],'path':str(p),'duration':info.duration,
   'reference':text,'reference_source':tp,'reference_source_sha256':th,'native_utterance_not_concatenation':True}
speakers=sorted({r['speaker'] for r in byid.values()},key=lambda x:hashlib.sha256(('ROW-R3-20261023/'+x).encode()).hexdigest())
chosen=[]
for speaker in speakers[:8]:
 candidates=[r for r in byid.values() if r['speaker']==speaker]
 r=min(candidates,key=lambda r:hashlib.sha256(('ROW-R3-UTTERANCE/'+r['source_id']).encode()).hexdigest())
 wave,sr=sf.read(r['path'],dtype='float32');r['audio_sha256']=hashlib.sha256(np.asarray(wave,dtype='<f4').tobytes()).hexdigest()
 chosen.append(r)
out={'status':'FROZEN_NATIVE_LONG_SOURCES' if len(chosen)>=4 else 'INSUFFICIENT_NATIVE_LONG_ASSETS_NO_SILENT_SUBSTITUTION',
 'sessions':chosen,'unique_speakers':len(chosen),'native_eligible_utterances':len(byid),'headers_considered':considered,
 'excluded_speakers':sorted(excluded),'selection':'SHA speaker then utterance; audio headers/reference availability only; no model outcomes',
 'one_shared_source_pool_across_two_adapters_not_twice_as_many_subjects':True,'new_GPU_calls':0,
 'Whisper_path':'explicit get_prompt_ids of cumulative declared history, no presumed previous-segment truncation',
 'Qwen_path':'actual cumulative rollback5; future audio coverage must be verified before long-run claims'}
(D/'MANIFEST.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['sessions','excluded_speakers']}))
