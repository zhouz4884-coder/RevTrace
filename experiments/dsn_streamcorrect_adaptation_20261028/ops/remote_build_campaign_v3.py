"""Freeze actual downloaded inputs/configs and prelaunch records, no GPU calls."""
import pathlib,json,hashlib,subprocess,random,datetime,os,importlib.metadata,sys
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028'
A=json.loads((O/'assets_v1/ASSET_MANIFEST.json').read_text());plan=json.loads((O/'assets_v1/PUBLIC_PLAN.json').read_text())
assert A['status']=='PASS_EXACT_NATIVE_ASSETS_ACQUIRED'
records={x['path']:x for x in A['files']};M=pathlib.Path(plan['model_root']);D=pathlib.Path(plan['dataset_root']);S=P/'runtime_source_v3';cache=B/'cache/revtrace_streamcorrect_20261028'
references=json.loads((D/'reference.json').read_text());assert isinstance(references,list)
ref={}
for row in references:
 name=pathlib.PurePosixPath(row.get('audio_path','')).stem;text=row.get('text_zh','')
 if name and text:
  if name in ref and ref[name]!=text:raise ValueError('duplicate conflicting author reference')
  ref[name]=text
sources=[]
for row in plan['selected_sources']:
 p=pathlib.Path(row['path']);b=p.read_bytes();h=hashlib.sha256(b).hexdigest();assert records[str(p)]['sha256']==h
 sid=row['source_id'];assert sid in ref
 sources.append(dict(source_id=sid,speaker_id=row['speaker_id'],path=str(p),audio_sha256=h,frames=row['frames'],duration=row['duration'],reference=ref[sid]))
models={k:dict(path=x['path'],bytes=x['bytes'],sha256=x['sha256']) for k,x in records.items() if k.startswith(str(M))}
contract=dict(application='author StreamCorrect selected-feedback recurrence',native_author_commit=plan['native_author_commit'],
 author_whisper_sha256='9f016f71df780c05b04719633ed302b502a457ff18a086eb5412a394b05cacb7',
 model_assets=models,beam_size=4,corrector_max_new_tokens=8,corrector_do_sample=False,
 dtype='float32',language='zh',cadence_seconds=.5,initial_audio_seconds=1.,frame_threshold=20,
 audio_buffer_seconds=30.,private_lookahead_samples=32000,native_cache_cut='clean KV/attention and reset beam decoder',
 front_end='controlled fixed-boundary no-VAD wrapper',private_update='first-beam identity prediction through native selected-feedback append',
 render='append actual native selected token decoding',exact_compatibility='complete native state cut byte equality')
backend=dict(author_root=str(P/'author_StreamCorrect_bbb9f7f'),asr_model=str(M/'asr/large-v2-zh.pt'),
 corrector_base=str(M/'ultravox_b95bec8'),corrector_adapter=str(M/'adapter'),text_backbone=str(M/'llama32_1b_instruct_f8e6b'),contract=contract)
env=dict(python=sys.version,executable=sys.executable,packages={k:importlib.metadata.version(k) for k in ('torch','transformers','numpy','peft','soundfile','torchaudio')},
 assets_manifest_path=str(O/'assets_v1/ASSET_MANIFEST.json'),assets_manifest_sha256=hashlib.sha256((O/'assets_v1/ASSET_MANIFEST.json').read_bytes()).hexdigest(),
 author_source_commit=plan['native_author_commit'],code_commit='825b96f60f63f6affb42daf182d0c77e2b9fb7b2',gpu_launched=False)
configs=P/'native_campaign_v3_configs';configs.mkdir(exist_ok=False);envpath=configs/'FROZEN_ENVIRONMENT.json';envpath.write_text(json.dumps(env,indent=2))
cohorts={'A':sources[:2],'B':sources[2:]};order=[]
for cohort in ('A','B'):order.append(dict(stage='witness',cohort=cohort,arm='joint',repeat=-1))
arms=['sequential','drop','joint'];rng=random.Random(20261028);rng.shuffle(arms)
for repeat in range(2):
 for slot in range(3):
  cs=['A','B'] if (slot+repeat)%2==0 else ['B','A']
  for cohort in cs:
   idx=(slot+('A','B').index(cohort)+repeat)%3
   order.append(dict(stage='formal',cohort=cohort,arm=arms[idx],repeat=repeat))
cells=[]
for x in order:
 cid=f"SC_NATIVE_V3_{x['stage']}_{x['cohort']}_{x['arm']}_r{x['repeat']}";out=O/'native_campaign_v3_cells'/cid
 settings=dict(backend=backend,hf_home=str(cache/'huggingface'),sources=cohorts[x['cohort']],asset_manifest=str(O/'assets_v1/ASSET_MANIFEST.json'))
 config=dict(experiment_id=cid,code_commit=env['code_commit'],arm=x['arm'],cohort=x['cohort'],repeat=x['repeat'],stage=x['stage'],settings=settings)
 cfg=configs/(cid+'.json');cfg.write_text(json.dumps(config,ensure_ascii=False,indent=2))
 record=dict(experiment_id=cid,code_commit=env['code_commit'],frozen_config=str(cfg),frozen_config_sha256=hashlib.sha256(cfg.read_bytes()).hexdigest(),
 environment_record=str(envpath),environment_record_sha256=hashlib.sha256(envpath.read_bytes()).hexdigest(),raw_result_location=str(out/'native_jobs.jsonl'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'))
 pre=configs/(cid+'_PRELAUNCH_RECORD.json');pre.write_text(json.dumps(record,indent=2))
 cells.append(dict(**x,cell_id=cid,config=str(cfg),out=str(out),prelaunch_record=str(pre)))
frozen=dict(experiment_id='SC_NATIVE_CONTROLLED_ADAPTATION_V3',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 source_commit=env['code_commit'],sources=sources,model_contract=contract,cells=cells,
 scope='2 prerequisite natural-feedback witness runs then 12 formal real-service cells; no replay and no training',
 gate='fixed four sources must naturally include nonempty corrected and unchanged actual learned selections with actual same-source private-ahead interleaving; empty or unstarted pending updates do not satisfy the gate',
 runtime_source=str(S),source_manifest=str(P/'SOURCE_v3.json'),environment_record=str(envpath),order_seed=20261028)
path=P/'NATIVE_CAMPAIGN_v3_FROZEN.json';assert not path.exists();path.write_text(json.dumps(frozen,ensure_ascii=False,indent=2))
(O/'FROZEN_CAMPAIGN_IDENTITY.json').write_text(json.dumps(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),cells=len(cells),sources=[x['source_id'] for x in sources],source_commit=env['code_commit']),indent=2))
print(json.dumps(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),cells=len(cells),sources=sources),ensure_ascii=False,indent=2))
