"""Freeze standalone data tools and recipes; never changes the global source pointer."""
import datetime,hashlib,json,pathlib,platform,shutil,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];src=F/'source_dev'
def run(*args):return subprocess.check_output(list(args),text=True).strip()
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
assert not (src/'.git').exists()
run('git','init','-q','-b','codex/sustained-inputs-20261030',str(src))
run('git','-C',str(src),'config','core.autocrlf','false')
run('git','-C',str(src),'config','user.name','RevTrace Research')
run('git','-C',str(src),'config','user.email','research@revtrace.invalid')
run('git','-C',str(src),'add','.')
run('git','-C',str(src),'commit','-qm','Freeze sustained synthetic input recipe and exact acquisition tools')
commit=run('git','-C',str(src),'rev-parse','HEAD')
assert not run('git','-C',str(src),'status','--porcelain','--untracked-files=all')
files=[dict(path=n,bytes=(src/n).stat().st_size,sha256=sha(src/n)) for n in run('git','-C',str(src),'ls-files').splitlines()]
packages=F/'packages';packages.mkdir()
manifest=dict(source_commit=commit,code_commit=commit,files=files,scope='Sustained synthetic input metadata selection and exact official public ZIP acquisition; no neural model.')
mp=packages/'DATA_SOURCE_v1.json';put(mp,manifest)
snapshot=F/'source_snapshot_v1';snapshot.mkdir()
for row in files:
 p=snapshot/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((src/row['path']).read_bytes())
bundle=packages/'DATA_SOURCE_v1.bundle';run('git','-C',str(src),'bundle','create',str(bundle.resolve()),'HEAD')
# Import complete commit without changing the legacy checkout or its HEAD.
run('git','-C',str(R),'fetch',str(bundle.resolve()),'HEAD:refs/research/dsn-sustained-input-tools-v1')
frozen=F/'source_v1';run('git','clone','-q','--no-checkout',str(bundle.resolve()),str(frozen));run('git','-C',str(frozen),'config','core.autocrlf','false');run('git','-C',str(frozen),'checkout','-q',commit)
index=R/'experiments/dsn_streamcorrect_adaptation_20261028/public_asset_metadata_v3/ARCHIVE_ENTRIES_0.json'
assert sha(index)=='efd03c4e9ef086548d353ead2efacb826afcc6440e1c5b866faf79d8e176ccc4'
env=F/'FROZEN_DATA_ENVIRONMENT_v1.json';put(env,dict(python=sys.version,executable=sys.executable,platform=platform.platform(),new_model_calls=0,new_audio_read=False))
rule=dict(experiment_id='SC_SUSTAINED_TWO_NEW_SPEAKERS_24UTTS_METADATA_V1',selection_source_commit=commit,source_manifest_sha256=sha(mp),archive_index=str(index.resolve()),archive_index_sha256=sha(index),archive_public_url='https://huggingface.co/datasets/playwithmino/StreamCorrect/resolve/16f6fd1e17418f1c4111a18fdd39543813206d96/StreamCorrect.zip',seed=2026103011,excluded_speakers=['S0764','S0765','S0767','S0768','S0908','S0916','S0913','S0905'],speaker_count=2,utterances_per_speaker=24,estimated_size_band_seconds=[8,12],source_selection='Uniform sample of two sorted unused speakers with>=24 eligible members, then uniform without-replacement24 members preserving PRNG sample order.',technical_fallback='none; only exact same-member transport retries permitted',selection_output=str((F/'METADATA_SELECTION_v1_FROZEN.json').resolve()),predecessor_neural_method_commit='bdfa3b1307d267a5a4caf6484e1ad465c39a592e',new_resilience_runtime_not_yet_frozen=True,metadata_only_before_new_audio_text_and_neural=True,synthetic_concatenated_utterances=True,no_inserted_silence=True,no_resampling=True,no_reset_or_EOS_at_part_boundaries=True,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
rp=F/'SELECTION_RULE_v1_FROZEN.json';put(rp,rule)
put(F/'SELECTION_PRELAUNCH_v1.json',dict(experiment_id=rule['experiment_id'],code_commit=commit,frozen_config=str(rp),config_sha256=sha(rp),environment_record=str(env),environment_sha256=sha(env),raw_result_location=str(index),raw_scope='Bounded existing ZIP metadata only, no new audio; large acquired data will be placed on designated8TB.',aggregate_summary_location=rule['selection_output'],gate_decision_location=str(F/'METADATA_SELECTION_v1_FROZEN.json'),planned_large_data_root='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/datasets/revtrace/native_sustained_20261030',GPU_launched=False))
put(F/'CURRENT_DATA_SELECTION_CANDIDATE_v1.json',dict(source_worktree=str(frozen.resolve()),source_manifest=str(mp.resolve()),source_manifest_sha256=sha(mp),source_commit=commit,GPU_queue='LOCAL_METADATA_AND_SYNTHETIC_CPU_CONTROLS_ONLY_NO_REMOTE_OR_NEURAL',scope='Candidate only; global CURRENT unchanged. Root must select and no-argument preflight before formal CPU/metadata execution.'))
print(json.dumps(dict(commit=commit,manifest_sha256=sha(mp),files=len(files),selection_rule_sha256=sha(rp),global_CURRENT_changed=False,selection_executed=False)))

