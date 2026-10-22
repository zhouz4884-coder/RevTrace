from pathlib import Path
import hashlib,json,sys
import soundfile as sf,numpy as np
B=Path(sys.argv[1]);root=B/'datasets/revtrace/librispeech/LibriSpeech/test-clean';O=B/'datasets/revtrace/elastic_20261022_32'
old=json.loads((B/'datasets/tc_live_20260906/manifest.json').read_text());D=json.loads((B/'datasets/revtrace/phaseD_20261021/manifest.json').read_text());excluded={r['source_id'] for r in D['sessions']}|{x['sample_id'] for s in old['sessions'] if s['language']=='English' for x in s.get('sources',[])}
pool=[]
for speaker in sorted(root.iterdir(),key=lambda p:hashlib.sha256(('ELASTIC-32-20261022:'+p.name).encode()).hexdigest()):
 if not speaker.is_dir():continue
 for p in sorted(speaker.rglob('*.flac'),key=lambda p:hashlib.sha256(('ELASTIC-32-20261022:'+p.stem).encode()).hexdigest()):
  if p.stem in excluded:continue
  inf=sf.info(p)
  if 16<=inf.duration<=28:pool.append((speaker,p));break
if len(pool)<32:
 out={'status':'NO_GO_INSUFFICIENT_DISTINCT_SPEAKERS','available':len(pool),'required':32,'no_ASR_model_loaded':True};(B/'results/revtrace/elastic_20261022/STRESS_DATA_DECISION.json').write_text(json.dumps(out));print(json.dumps(out));sys.exit(0)
assert not O.exists();O.mkdir();records=[]
for speaker,p in pool[:32]:
 refs=dict(line.split(' ',1) for line in (p.parent/(speaker.name+'-'+p.parent.name+'.trans.txt')).read_text().splitlines());wav,rate=sf.read(p,dtype='float32');assert rate==16000 and wav.ndim==1;v=np.asarray(wav,dtype='<f4');out=O/(p.stem+'.wav');sf.write(out,v,16000,subtype='FLOAT')
 records.append({'path':str(out),'source_id':p.stem,'speaker':speaker.name,'language':'English','duration':len(v)/16000,'reference':refs[p.stem],'audio_sha256':hashlib.sha256(v.tobytes()).hexdigest(),'original_file':str(p),'original_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
manifest={'study':'ELASTIC-SINGLE-STRESS-QUALIFICATION-32','selection':'SHA256 ELASTIC-32-20261022; one16–28s full utterance/speaker; excludes exact previous utterances, not all previous speakers; no ASR outcome selection','sessions':records};(O/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
decision={'status':'READY_PREDECLARED_32_INDEPENDENT_SPEAKERS','eligible_pool_speakers':len(pool),'selected':32,'manifest_sha256':hashlib.sha256((O/'manifest.json').read_bytes()).hexdigest(),'source_ids':[r['source_id'] for r in records],'audio_seconds':sum(r['duration'] for r in records)};(B/'results/revtrace/elastic_20261022/STRESS_DATA_DECISION.json').write_text(json.dumps(decision,indent=2)+'\n');print(json.dumps(decision))
