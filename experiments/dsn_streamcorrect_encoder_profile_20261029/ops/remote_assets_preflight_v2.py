"""Read-only complete model/audio rehash before the allocated component window."""
import datetime,hashlib,json,os,pathlib,subprocess
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_encoder_profile_20261029';O=B/'results/revtrace/dsn_streamcorrect_encoder_profile_20261029'
def read(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(16*1024*1024),b''):h.update(b)
 return h.hexdigest()
cfg=read(P/'PROFILE_PLAN_v2_FROZEN.json');cpu=read(O/'cpu_gate_v2/GATE.json')
assert cpu['status']=='PASS_17_CPU_CONTROLS_AND_COMPLETE_SOURCE_ENVIRONMENT_IMPORT_GATE' and cpu['skips']==0 and cpu['source_commit']==cfg['profile_source_commit']
assert sha(P/'PROFILE_PLAN_v2_FROZEN.json')=='789f0069a563f4cbc4e454c5259da9b482f588b8d6a708605d31ef134258a960'
env=read(cfg['environment_record']);assert sha(cfg['environment_record'])==cfg['environment_sha256']
am=read(env['assets_manifest_path']);assert sha(env['assets_manifest_path'])==env['assets_manifest_sha256']
assets={r['path']:r for r in am['files']}
required=dict(cfg['settings']['backend']['contract']['model_assets'])
asr=cfg['settings']['backend']['asr_model'];required[asr]=assets[asr]
records=[]
for path,expected in sorted(required.items()):
 p=pathlib.Path(path);assert p.resolve().is_relative_to(B) and p.is_file()
 observed=sha(p);assert observed==expected['sha256'] and p.stat().st_size==expected['bytes']
 records.append(dict(path=path,bytes=p.stat().st_size,sha256=observed));print(json.dumps(dict(verified_asset=p.name,bytes=p.stat().st_size)),flush=True)
audio=[]
for s in cfg['settings']['model_sources']:
 p=pathlib.Path(s['path']);assert p.resolve().is_relative_to(B);observed=sha(p);assert observed==s['audio_sha256'];audio.append(dict(source_id=s['source_id'],sha256=observed,bytes=p.stat().st_size))
gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader'],text=True).strip();assert not gpu,'foreign GPU process: '+gpu
record=dict(status='PASS_COMPLETE_MODEL_AUDIO_AND_CPU17_COMPONENT_PREREQUISITE',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),profile_source_commit=cfg['profile_source_commit'],imported_runtime_commit=cfg['imported_runtime_commit'],plan_sha256=sha(P/'PROFILE_PLAN_v2_FROZEN.json'),CPU_gate_sha256=sha(O/'cpu_gate_v2/GATE.json'),full_rehashed_assets=records,full_rehashed_audio=audio,asset_bytes=sum(x['bytes'] for x in records),gpu_processes_empty=True,gpu_launched=False)
dest=O/'ASSET_PREREQUISITE_v2.json';assert not dest.exists();dest.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(status=record['status'],asset_count=len(records),asset_bytes=record['asset_bytes'],path=str(dest),sha256=sha(dest))),flush=True)
