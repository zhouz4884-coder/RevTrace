"""Metadata-only independent16-source validation freeze before formal outcomes."""
from pathlib import Path
import hashlib,json,re,sys
import numpy as np,soundfile as sf
B=Path(sys.argv[1]);O=B/'results/revtrace/row_completion_20261023';D=O/'validation_source_v1';D.mkdir(exist_ok=False)
old=json.loads((B/'datasets/revtrace/phaseD_20261021/manifest.json').read_text())
excluded=set(map(str,old['excluded_original_speakers']))|{r['source_id'].split('-')[0] for r in old['sessions']}
for p in [O/'r3_source_v1/MANIFEST.json',B/'results/revtrace/online_admission_20261022/PILOT_MANIFEST.json']:
 excluded|={r['source_id'].split('-')[0] for r in json.loads(p.read_text())['sessions']}
roots=[B/'datasets/revtrace'/n for n in ['librispeech','librispeech_dev','librispeech_hf','librispeech_r9_final','librispeech_r9_final2']]+[B/'datasets/revbatch/qwen_public']
byid={};tables={};scanned=0
for root in roots:
 if not root.is_dir():continue
 for p in sorted(root.rglob('*.flac')):
  scanned+=1;assert scanned<=40000
  sid=p.stem
  if not re.fullmatch(r'\d+-\d+-\d+',sid) or sid in byid or sid.split('-')[0] in excluded:continue
  if p.parent not in tables:
   t={}
   for q in p.parent.glob('*.trans.txt'):
    for line in q.read_text().splitlines():
     if ' ' in line:
      key,text=line.split(' ',1);t[key]=(text,str(q),hashlib.sha256(q.read_bytes()).hexdigest())
   tables[p.parent]=t
  if sid not in tables[p.parent]:continue
  info=sf.info(p)
  if info.samplerate!=16000 or info.channels!=1 or not 12<=info.duration<=28:continue
  text,refpath,refsha=tables[p.parent][sid]
  byid[sid]={'source_id':sid,'speaker':sid.split('-')[0],'path':str(p),'language':'English','duration':info.duration,
    'reference':text,'reference_source':refpath,'reference_source_sha256':refsha,'native_not_concatenated':True}
speakers=sorted({r['speaker'] for r in byid.values()},key=lambda s:hashlib.sha256(('ROW-VAL-20261023/'+s).encode()).hexdigest())
selected=[]
for speaker in speakers[:16]:
 r=min((r for r in byid.values() if r['speaker']==speaker),key=lambda r:hashlib.sha256(('ROW-VAL-UTT/'+r['source_id']).encode()).hexdigest())
 wave,sr=sf.read(r['path'],dtype='float32');assert sr==16000
 r['audio_sha256']=hashlib.sha256(np.asarray(wave,dtype='<f4').tobytes()).hexdigest();selected.append(r)
out={'status':'FROZEN_INDEPENDENT_VALIDATION16' if len(selected)==16 else 'INSUFFICIENT_ASSETS_NO_SUBSTITUTION',
 'sessions':selected,'unique_speakers':len(selected),'headers_scanned':scanned,'excluded_speakers':sorted(excluded),
 'selection':'SHA order by speaker/utterance,header/reference availability only; frozen before formal outcomes',
 'not_extra_concurrency_or_repeats_as_subjects':True,'new_model_calls':0}
(D/'MANIFEST.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['sessions','excluded_speakers']}))
