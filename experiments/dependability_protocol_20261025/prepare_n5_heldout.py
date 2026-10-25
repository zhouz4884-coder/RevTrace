"""Linux CPU metadata-only source-disjoint validation selection, before GPU."""
from pathlib import Path
import hashlib,json,subprocess
import numpy as np,soundfile as sf
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/n5_v2'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'do not contend with serving'
launch=B/'results/revtrace/dependability_20261025/n5_v2/DEVELOPMENT_LAUNCH.json'
if launch.exists():
 d=json.loads(launch.read_text());q=Path('/proc')/str(d['pid'])
 assert not (q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks']),'do not contend with live controller even between cells'
exclude=json.loads((P/'N5_SOURCE_EXCLUSIONS_v1.json').read_text());old=set(exclude['excluded_native_ids']);speakers=set(exclude['excluded_speakers']);old_audio=set(exclude['excluded_audio_digests'])
roots=[B/'datasets/revtrace/librispeech_dev/LibriSpeech/dev-clean',B/'datasets/revtrace/librispeech_dev/LibriSpeech/dev-other']
candidates=[];refs={}
for root in roots:
 if not root.exists():continue
 for file in root.rglob('*.trans.txt'):
  for line in file.read_text().splitlines():
   if ' ' in line:key,text=line.split(' ',1);refs[key]=(text,file)
 for file in root.rglob('*.flac'):
  source=file.stem
  if source in old or source not in refs:continue
  info=sf.info(file);duration=info.frames/info.samplerate
  if not (info.samplerate==16000 and info.channels==1 and 16<=duration<=28):continue
  key=hashlib.sha256((exclude['selection_seed']+':'+source).encode()).hexdigest()
  candidates.append(dict(source_id=source,speaker=source.split('-')[0],path=str(file),duration=duration,rank=key))
candidates.sort(key=lambda x:x['rank'])
unseen={r['speaker'] for r in candidates if r['speaker'] not in speakers}
strict=len(unseen)>=32;selected=[];used=set()
for row in candidates:
 if row['speaker'] in used or (strict and row['speaker'] in speakers):continue
 wave,rate=sf.read(row['path'],dtype='float32');wave=np.asarray(wave,dtype='<f4');digest=hashlib.sha256(wave.tobytes()).hexdigest()
 if digest in old_audio:continue
 text,file=refs[row['source_id']]
 selected.append(dict(row,language='English',audio_sha256=digest,reference=text,reference_source=str(file),
  reference_source_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),native_not_concatenated=True))
 used.add(row['speaker'])
 if len(selected)==32:break
assert len(selected)==32,'do not quietly reduce independent source scope'
assert not set(r['source_id'] for r in selected)&old
result=dict(study='REVTRACE-N5-INDEPENDENT-20261026',selection='hash/metadata only before validation GPU; no speech-output filtering',
 source_disjoint=True,speaker_disjoint=strict,speaker_overlap_with_conservative_old_pool=sorted(used&speakers),
 candidate_count=len(candidates),available_unseen_speakers=len(unseen),
 exclusion_sha256=hashlib.sha256((P/'N5_SOURCE_EXCLUSIONS_v1.json').read_bytes()).hexdigest(),sessions=selected)
out=P/'INDEPENDENT_MANIFEST_v1.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(path=str(out),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),sources=len(selected),speaker_disjoint=strict,speaker_overlap=result['speaker_overlap_with_conservative_old_pool'])))
