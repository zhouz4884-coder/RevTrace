"""Local-only freeze. Does not connect to the server or start analysis."""
import pathlib,subprocess,json,hashlib,datetime
T=pathlib.Path(__file__).resolve().parents[1];S=T/'analysis_old_fidelity_source_v1';P=T/'packages';snapshot=T/'analysis_old_fidelity_snapshot_v1'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
def put(p,x):assert not p.exists();p.write_bytes(json.dumps(x,ensure_ascii=False,indent=2).encode())
assert not git('status','--porcelain','--untracked-files=all');commit=git('rev-parse','HEAD');snapshot.mkdir(exist_ok=False);rows=[]
for name in git('ls-files').splitlines():
 data=(S/name).read_bytes();(snapshot/name).write_bytes(data);rows.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
manifest=P/'OLD_FIDELITY_SOURCE_v1.json';put(manifest,dict(source_commit=commit,files=rows));subprocess.run(['git','-C',str(S),'bundle','create',str((P/'OLD_FIDELITY_SOURCE_v1.bundle').resolve()),'HEAD'],check=True)
eqpath=T/'EQ_PLAN_v2_FROZEN.json';eq=json.loads(eqpath.read_bytes());refpath=T/'ORIGINAL_FIXED_REFERENCES_v1.json';ref=json.loads(refpath.read_bytes())
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';RP=B+'/projects/revtrace_dsn_streamcorrect_stage_handoff_20261029';O=B+'/results/revtrace/dsn_streamcorrect_stage_handoff_20261029'
plan=dict(experiment_id='SC_STAGE_OLD_NATIVE69_TASK_FIDELITY_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),analysis_source_commit=commit,analysis_source_root=RP+'/analysis_old_fidelity_source_v1',analysis_source_manifest=RP+'/OLD_FIDELITY_SOURCE_v1.json',analysis_source_manifest_sha256=sha(manifest),
 old_native_plan=ref['original_native_plan'],old_native_plan_sha256=ref['original_native_plan_sha256'],prior_native_audit=B+'/results/revtrace/dsn_streamcorrect_20261028/native_campaign_v8_continuation_auditfix_v1/SUMMARY.json',prior_native_audit_sha256='84b04f0e16dcf8ff7cc42aba66c8f86b8d41e6e1b56e9e3f048edbb0c332709b',
 original_fixed_references=RP+'/OLD_FIDELITY_ORIGINAL_REFERENCE_v1.json',original_fixed_references_sha256=sha(refpath),new_neural_plan=RP+'/EQ_PLAN_v2_FROZEN.json',new_neural_plan_sha256=sha(eqpath),new_neural_out=eq['raw_result_location'],neural_source_commit=eq['source_commit'],
 raw_result_location=O+'/old_native69_task_fidelity_v1',aggregate_summary_location=O+'/old_native69_task_fidelity_v1/SUMMARY.json',gate_decision_location=O+'/old_native69_task_fidelity_v1/GATE.json',environment_python=eq['environment_python'],
 allocation='WAIT: original frozen fresh neural69 scope and its worker/CPU/IO release must precede execution',expected_calls=69,expected_sources=4,allowed_state_projection='delete only exact expected contract.stage_execution from NEW states; retain source_sha and every other field',scope='saved neural task fidelity only; no GPU/inference/serving, no raw hash equality across contract tags')
put(T/'OLD_FIDELITY_PLAN_v1_FROZEN.json',plan);record=dict(analysis_source_commit=commit,files=len(rows),manifest_sha256=sha(manifest),bundle_sha256=sha(P/'OLD_FIDELITY_SOURCE_v1.bundle'),plan_sha256=sha(T/'OLD_FIDELITY_PLAN_v1_FROZEN.json'),remote_executed=False)
put(P/'OLD_FIDELITY_FREEZE_RECORD_v1.json',record);print(json.dumps(record,indent=2))
