"""CPU-only original R7 input reconstruction from recorded utterance IDs."""
from pathlib import Path
import hashlib,json,sys,time,os
import numpy as np
import soundfile as sf
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
D=B/'results/revtrace/freeze_boundary_20261027/r7_input_reconstruction_v1'
if D.exists():raise FileExistsError(D)
D.mkdir(parents=True)
started=time.perf_counter()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=B/'datasets/revtrace/librispeech/whisper-w-quality.json'
paired=B/'results/revtrace/r7_efsc/whisper_base_quality/paired-128.json'
data=json.loads(paired.read_text());source=json.loads(manifest.read_text())
lookup={(r['split'],r['utterance_id']):r for r in source['records']}
records=[];sessions=[]
for s in data['sessions']:
 pieces=[];offset=0;layout=[];reference=[]
 for ident in s['utterance_ids']:
  r=lookup[s['split'],ident];p=Path(r['path']);actualsha=sha(p)
  if actualsha!=r['sha256']:raise ValueError('audio source SHA changed: '+str(p))
  a,rate=sf.read(p,dtype='float32',always_2d=False)
  if rate!=16000:raise ValueError('sample rate changed')
  if a.ndim==2:a=a.mean(axis=1)
  a=np.asarray(a,dtype=np.float32)
  if a.size!=r['samples']:raise ValueError('source length changed')
  if pieces:pieces.append(np.zeros(1600,dtype=np.float32));layout.append(dict(kind='zero_separator',start=offset,end=offset+1600));offset+=1600
  pieces.append(a);layout.append(dict(kind='utterance',utterance_id=ident,path=str(p),start=offset,end=offset+a.size,sha256=actualsha));offset+=a.size
  records.append(dict(utterance_id=ident,split=s['split'],path=str(p),sha256=actualsha,samples=int(a.size),sample_rate=rate))
  reference.append(r['text'])
 if offset<1440000:
  if offset<1080000:raise ValueError('historical builder would not retain this short session')
  pieces.append(np.zeros(1440000-offset,dtype=np.float32));layout.append(dict(kind='zero_tail',start=offset,end=1440000));offset=1440000
 audio=np.concatenate(pieces);windows=np.array_split(audio,9);at=0;win=[]
 for i,w in enumerate(windows):
  win.append(dict(window_index=i,start=at,end=at+int(w.size),samples=int(w.size),float32le_sha256=hashlib.sha256(w.astype('<f4',copy=False).tobytes()).hexdigest()));at+=int(w.size)
 sessions.append(dict(session_id=s['session_id'],split=s['split'],catastrophic_outlier=s['catastrophic_outlier'],
  utterance_ids=s['utterance_ids'],samples=int(audio.size),duration_seconds=audio.size/16000,
  float32le_sha256=hashlib.sha256(audio.astype('<f4',copy=False).tobytes()).hexdigest(),
  reference=' '.join(reference),layout=layout,windows=win,
  historical_canonical_wer=s['canonical_wer'],historical_efsc_wer=s['efsc_wer']))
result=dict(experiment_id='REVTRACE-R7-INPUT-IDENTITY-20261027',code_commit=os.environ['R7_AUDIT_CODE_COMMIT'],
 script_sha256=os.environ['R7_AUDIT_SCRIPT_SHA256'],old_quality_execution_commit='UNKNOWN',
 original_manifest_sha256=sha(manifest),paired128_sha256=sha(paired),
 original_manifest_path=str(manifest),paired128_path=str(paired),
 environment=dict(python=sys.version,numpy=np.__version__,soundfile=sf.__version__,libsndfile=sf.__libsndfile_version__),
 checked_audio_files=len(records),unique_audio_files=len({r['path'] for r in records}),sessions=len(sessions),
 outlier_ids=[s['session_id'] for s in sessions if s['catastrophic_outlier']],
 runtime_seconds=time.perf_counter()-started,GPU_calls=0,
 raw_result_location=str(D),summary_location=str(D/'SUMMARY.json'),gate_location=str(D/'GATE.json'),
 scope='reconstructed current bytes match original per-utterance SHA and recorded session IDs; original concatenated hashes were not recorded',
 audio_records=records,session_records=sessions)
(D/'INPUT_IDENTITY.json').write_text(json.dumps(result,indent=2)+'\n')
summary={k:v for k,v in result.items() if k not in ('audio_records','session_records')}
summary['input_identity_sha256']=sha(D/'INPUT_IDENTITY.json')
(D/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
(D/'GATE.json').write_text(json.dumps(dict(gate='PASS_SOURCE_FILE_SHA_AND_RECORDED_LAYOUT_RECONSTRUCTION',
 historical_gpu_identity='UNKNOWN',original_combined_waveform_hash='NOT_RECORDED',GPU_calls=0),indent=2)+'\n')
print(json.dumps(summary))
