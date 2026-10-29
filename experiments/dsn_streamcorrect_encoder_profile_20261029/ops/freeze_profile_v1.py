"""Freeze the approved13-call, four-fixed-pair component probe before GPU use."""
import datetime,hashlib,json,pathlib,shutil,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[3];F=pathlib.Path(__file__).resolve().parents[1]
H=ROOT/'experiments/dsn_streamcorrect_stage_handoff_20261029';src=F/'source_v1'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_streamcorrect_encoder_profile_20261029';O=B+'/results/revtrace/dsn_streamcorrect_encoder_profile_20261029'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()
tracked=subprocess.check_output(['git','ls-files'],cwd=src,text=True).splitlines()
files=[dict(path=x,bytes=(src/x).stat().st_size,sha256=sha(src/x)) for x in tracked]
packages=F/'packages';packages.mkdir(exist_ok=True)
manifest=dict(source_commit=commit,files=files,scope='encoder-only component and original full oracle generator; imported runtime bdfa separate')
mp=packages/'SOURCE_v1.json';assert not mp.exists();mp.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
snapshot=F/'source_snapshot_v1';snapshot.mkdir(exist_ok=False)
for x in tracked:shutil.copyfile(src/x,snapshot/x)
bundle=packages/'SOURCE_v1.bundle';subprocess.run(['git','bundle','create',str(bundle.resolve()),'HEAD'],cwd=src,check=True)
pilot=H/'SERVICE_PILOT_RESULTS_v1/SC_STAGE_SERVICE_PILOT_V1_two_full_spec_early_source0_r0'
ledger=read(pilot/'FULLSPEC_LEDGER.json');jobs=[json.loads(x) for x in (pilot/'native_jobs.jsonl').read_text(encoding='utf-8').splitlines()]
assert len(ledger['abandoned'])==4
pairs=[]
for i,a in enumerate(ledger['abandoned']):
 j=next(x for x in jobs if x['record']['start']==a['start']['frontier'] and x['record']['end']==a['target_end'])
 assert a['start']['audio_segments']==j['start']['audio_segments'] and a['start']['contract']==j['start']['contract']
 assert a['gpu']!=j['gpu']
 pairs.append(dict(pair_id=f'pair{i}_{a["job_id"]}_{j["job_id"]}',source_id=a['source_id'],old_gpu=a['gpu'],new_gpu=j['gpu'],
     wrong_start=a['start'],correct_start=j['start'],end=a['target_end'],is_last=j['record']['is_last'],
     old_wrong_worker_begin=a['worker_job_begin_perf'],old_fallback_model_start=j['record']['model_start'],
     original_reference=dict(end=j['end'],token_ids=j['record']['token_ids'],selected_correction=j['record']['selected_correction'])))
settings=read(pilot/'CONFIG.json')['settings'];settings['cache_root']=B+'/cache/revtrace_streamcorrect_encoder_profile_20261029'
refdir=F/'references_v1';refdir.mkdir(exist_ok=False)
for name in ('FULLSPEC_LEDGER.json','native_jobs.jsonl','CONFIG.json'):shutil.copyfile(pilot/name,refdir/name)
author=H/'encoder_boundary_review_v1/author_reference'
for name in ('model.py','audio.py','SOURCES.json'):shutil.copyfile(author/name,refdir/name)
env=ROOT/'experiments/dsn_streamcorrect_adaptation_20261028/final_native_v8_evidence/FROZEN_ENVIRONMENT_v8.json'
shutil.copyfile(env,refdir/'FROZEN_ENVIRONMENT.json')
runtime=H/'packages/SOURCE_v3.json';shutil.copyfile(runtime,refdir/'IMPORTED_RUNTIME_SOURCE.json')
for name in ('model.py','audio.py'):
 assert (refdir/name).is_file()
cfg=dict(experiment_id='SC_ENCODER_FOUR_FIXED_PAIRS_COMPONENT_PROFILE_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 profile_source_commit=commit,profile_source_files={x['path']:x['sha256'] for x in files},
 imported_runtime_commit='bdfa3b1307d267a5a4caf6484e1ad465c39a592e',
 imported_runtime_root=B+'/projects/revtrace_dsn_streamcorrect_stage_handoff_20261029/source_v3',
 imported_runtime_manifest=P+'/references_v1/IMPORTED_RUNTIME_SOURCE.json',imported_runtime_manifest_sha256=sha(runtime),
 environment_record=P+'/references_v1/FROZEN_ENVIRONMENT.json',environment_sha256=sha(env),expected_packages=read(env)['packages'],
 frozen_input_files={P+'/references_v1/'+x.name:sha(x) for x in refdir.iterdir()},
 settings=settings,cache_root=settings['cache_root'],pairs=pairs,expected_original_infer_calls=13,
 encoder_identity=dict(original_author_commit='bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3',
  original_audio_py_sha256=sha(refdir/'audio.py'),original_model_py_sha256=sha(refdir/'model.py'),
  mel_filters_git_blob='28ea26909dbdfd608aef67afc4d74d7961ae4bb6',
  asr_checkpoint_sha256='995041b2e81f8490f143933fa909009d5caedf683f882fd2c0d52536623d2f62',
  native_asr_config_sha256=hashlib.sha256(json.dumps(settings['backend']['contract'],sort_keys=True).encode()).hexdigest(),
  source_sha256=settings['sources'][0]['audio_sha256'],N_SAMPLES=480000,N_FRAMES=3000),
 out=O+'/profile_v1',environment_python=B+'/envs/revtrace-streamcorrect-20261028/bin/python',
 scope='13 original-infer calls: four fixed wrong E-only/current full/received-E full pairs + fixed EOS original full repeat; component and oracle only',
 gate=dict(exact_mel_and_E_bits=True,all_selected_C_IDs_and_closed_cuts=True,
  fixed_potential_exports=14,fixed_uses=4,net_expected_resource_margin_seconds_at_least=.100,
  positive_profile_does_not_authorize_deployed_claim=True),
 resource_rule='No GPU launch until root has reviewed this frozen plan/source and allocated window')
cp=F/'PROFILE_PLAN_v1_FROZEN.json';assert not cp.exists();cp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
normalized=dict(code_commit=commit,source_commit=commit,files=files)
(packages/'SOURCE_v1_LOCAL_PREFLIGHT.json').write_text(json.dumps(normalized,indent=2)+'\n',encoding='utf-8')
(F/'FREEZE_RECORD_v1.json').write_text(json.dumps(dict(source_commit=commit,files=len(files),manifest_sha256=sha(mp),plan_sha256=sha(cp),bundle_sha256=sha(bundle)),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(source_commit=commit,files=len(files),manifest_sha256=sha(mp),plan_sha256=sha(cp))))
