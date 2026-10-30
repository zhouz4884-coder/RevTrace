"""Freeze default repeated prefixes and allocator-control diagnostic intent."""
import datetime,hashlib,json,pathlib,subprocess
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];S=F/'long_memory_diagnostic_source_v1'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_resilience_20261030';O=B+'/results/revtrace/dsn_native_resilience_20261030'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):assert not p.exists();p.write_bytes((json.dumps(x,indent=2)+'\n').encode())
git=lambda *a:subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
assert not git('status','--porcelain','--untracked-files=all');commit=git('rev-parse','HEAD');rows=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in sorted(git('ls-files').splitlines())]
M=F/'packages/LONG_MEMORY_DIAGNOSTIC_SOURCE_v1.json';put(M,dict(source_commit=commit,code_commit=commit,imported_neural_source_commit='9492d3f9cb35e2b2849ec020817750a221248f0e',files=rows))
bundle=F/'packages/LONG_MEMORY_DIAGNOSTIC_SOURCE_v1.bundle';subprocess.run(['git','-C',str(S),'bundle','create',str(bundle.resolve()),'HEAD'],check=True);subprocess.run(['git','-C',str(R),'fetch',str(bundle.resolve()),'HEAD:refs/research/dsn-long-memory-diagnostic-v1'],check=True,capture_output=True)
snap=F/'long_memory_diagnostic_snapshot_v1';snap.mkdir()
for row in rows:(snap/row['path']).write_bytes((S/row['path']).read_bytes())
put(F/'CURRENT_LONG_MEMORY_DIAGNOSTIC_CANDIDATE_v1.json',dict(source_worktree=str(S.resolve()),source_manifest=str(M.resolve()),source_manifest_sha256=sha(M),source_commit=commit,GPU_queue='FIXED_ORIGINAL_PREFIX_MEMORY_TRIAGE',scope='Separate diagnostic driver importing unchanged actual native9492.'))
folder=F/'long_memory_diagnostic_v1_configs';folder.mkdir();cells=[]
for label,allocator,end in [('default_r0',None,760000),('default_r1',None,760000),('expanded_r0','expandable_segments:True',768000)]:
 cfg=dict(experiment_id='SC_ORIGINAL_LONG_MEMORY_DIAG_V1_'+label,diagnostic_source_commit=commit,imported_neural_source_commit='9492d3f9cb35e2b2849ec020817750a221248f0e',imported_reference_plan=P+'/LONG_REFERENCE_PLAN_v1_FROZEN.json',imported_reference_plan_sha256='79b1c3ace4bd419ea998ed3dec37f73a4487122a7228d8bc00fcb15940b92efb',mode='continuous_prefix',allocator_conf=allocator,prefix_end=end,source='SC_SYNTH_S0770_24UTT_V1',original_source_frames=3656164,only_final_original_source_EOS=True,reference_only=True,actual_serving_cells=0)
 name=label+'.json';put(folder/name,cfg);cells.append(dict(label=label,config=P+'/long_memory_diagnostic_v1_configs/'+name,config_sha256=sha(folder/name),out=O+'/long_memory_diagnostic_v1/'+label,log=O+'/long_memory_diagnostic_v1/'+label+'.log'))
plan=dict(experiment_id='SC_ORIGINAL_LONG_MEMORY_DIAGNOSTIC_CAMPAIGN_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=commit,source_root=P+'/long_memory_diagnostic_source_v1',source_manifest=P+'/LONG_MEMORY_DIAGNOSTIC_SOURCE_v1.json',source_manifest_sha256=sha(M),source_files=len(rows),imported_neural_source_commit='9492d3f9cb35e2b2849ec020817750a221248f0e',environment_python=B+'/envs/revtrace-streamcorrect-20261028/bin/python',cells=cells,raw_result_location=O+'/long_memory_diagnostic_v1',scope='Repeated default95-edge original prefixes, fixed failed-input restore repeats, expandable-segment96-edge original prefix. Fixed original source/cadence/EOS/C/U/FP32; no serving claim. Same-input config binds the actual captured failed cut after it exists.')
put(F/'LONG_MEMORY_DIAGNOSTIC_v1_FROZEN.json',plan);print(json.dumps(dict(source_commit=commit,manifest_sha256=sha(M),cells=len(cells),neural_launched=False)))
