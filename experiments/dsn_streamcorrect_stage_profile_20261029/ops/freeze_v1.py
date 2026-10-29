import pathlib,json,hashlib,subprocess,datetime
T=pathlib.Path(__file__).resolve().parents[1];R=T.parents[1];S=T/'source_v1';P=T/'packages';P.mkdir(exist_ok=True)
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';RP=B+'/projects/revtrace_dsn_streamcorrect_stage_profile_20261029';O=B+'/results/revtrace/dsn_streamcorrect_stage_profile_20261029'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):
 data=json.dumps(x,ensure_ascii=False,indent=2).encode('utf-8')
 if p.exists():assert json.loads(p.read_text(encoding='utf-8'))==x
 else:p.write_bytes(data)
def git(*args):return subprocess.check_output(['git','-C',str(S),*args],text=True).strip()
assert not git('status','--porcelain','--untracked-files=all');commit=git('rev-parse','HEAD')
rows=[dict(path=p,bytes=(S/p).stat().st_size,sha256=sha(S/p)) for p in git('ls-files').splitlines()]
manifest=dict(source_commit=commit,files=rows,scope='read-only original corrector entry capture and bounded component replay; no handoff')
put(P/'SOURCE_v1.json',manifest);put(P/'SOURCE_v1_LOCAL_PREFLIGHT.json',dict(manifest,code_commit=commit))
if not (P/'SOURCE_v1.bundle').exists():subprocess.run(['git','-C',str(S),'bundle','create',str((P/'SOURCE_v1.bundle').resolve()),'HEAD'],check=True)
snapshot=T/'source_snapshot_v1';snapshot.mkdir(exist_ok=True)
for r in rows:
 dest=snapshot/r['path'];dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():assert dest.read_bytes()==(S/r['path']).read_bytes()
 else:dest.write_bytes((S/r['path']).read_bytes())
native=R/'experiments/dsn_streamcorrect_adaptation_20261028/final_native_v8_evidence/NATIVE_CAMPAIGN_v8_FROZEN.json';n=json.loads(native.read_text(encoding='utf-8'))
runs=[dict(run_id='full_'+str(i),kind='full',source_index=i,gpu=0,capture='full') for i in range(4)]
for name,source,gpu,mode in [('plain',0,0,'off'),('deferred',0,0,'deferred'),('full',0,0,'full'),('fresh_repeat',0,0,'full'),('cross_gpu',0,1,'full'),('different_source',2,0,'full')]:runs.append(dict(run_id='control_'+name,kind='control',source_index=source,gpu=gpu,capture=mode,start_F=24000,end_F=32000))
plan=dict(experiment_id='SC_ORIGINAL_STAGE_PROFILE_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=commit,native_plan=B+'/projects/revtrace_dsn_streamcorrect_20261028/NATIVE_CAMPAIGN_v8_FROZEN.json',native_plan_sha256=sha(native),native_model_source_commit=n['source_commit'],native_frozen_environment_sha256='96a0679d34741743de1a1b6d784c0e518cbdcf7b76a23cae3d95c12d20a6fae8',author_commit=n['model_contract']['native_author_commit'],author_infer_sha256=n['model_contract']['author_whisper_sha256'],runs=runs,cache_root=B+'/cache/revtrace_streamcorrect_stage_profile_20261029',raw_result_location=O+'/campaign_v1',aggregate_summary_location=O+'/campaign_v1/SUMMARY.json',gate_decision_location=O+'/campaign_v1/GATE.json',source_root=RP+'/source_v1',source_manifest=RP+'/SOURCE_v1.json',environment_python=B+'/envs/revtrace-streamcorrect-20261028/bin/python',source_selection='all four original metadata-selected sources retained; no output filtering',logical_infer_calls_max=sum((x['frames']+7999)//8000 for x in n['sources'])+4+12,control_target='predeclared 1.5s full canonical input to 2.0s target, first and third fixed source; full input packet repeat across capture and GPU, original v8 selected full histories are legal oracle',timing='CUDA-synchronized A to original C entry; original C; H tail/sync/unclassified residual. Explicit snapshot capture cost and post-model materialization reported; none equals IPC or deployed handoff overhead. First actual C per fresh process retained in declared warmup.',precision='unchanged native v8 FP32 controlled contract; no autocast/TF32. No claim against original recommended optimized precision.',scope='four complete original flows once and six bounded short controls, no training/model/source/dtype grid; no resume/tail/handoff implementation; no deployed serving claim')
put(T/'PLAN_v1_FROZEN.json',plan)
record=dict(source_commit=commit,source_manifest_sha256=sha(P/'SOURCE_v1.json'),local_preflight_manifest_sha256=sha(P/'SOURCE_v1_LOCAL_PREFLIGHT.json'),bundle_sha256=sha(P/'SOURCE_v1.bundle'),plan_sha256=sha(T/'PLAN_v1_FROZEN.json'),files=len(rows))
put(P/'FREEZE_RECORD_v1.json',record);print(json.dumps(record,indent=2))
