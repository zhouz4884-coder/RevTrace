"""Freeze local generic generator only; no source IDs/config/GPU execution."""
import pathlib,subprocess,json,hashlib,datetime
T=pathlib.Path(__file__).resolve().parents[1];S=T/'reference_generator_source_v1';P=T/'packages';snapshot=T/'reference_generator_snapshot_v1'
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert not git('status','--porcelain','--untracked-files=all');commit=git('rev-parse','HEAD');snapshot.mkdir(exist_ok=False);rows=[]
for name in git('ls-files').splitlines():
 data=(S/name).read_bytes();(snapshot/name).write_bytes(data);rows.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
manifest=P/'NEW_REFERENCE_GENERATOR_SOURCE_v1.json';assert not manifest.exists();manifest.write_bytes(json.dumps(dict(source_commit=commit,code_commit=commit,files=rows,scope='generic offline original-full reference generator; no selected new sources or executed neural calls'),indent=2).encode())
bundle=P/'NEW_REFERENCE_GENERATOR_SOURCE_v1.bundle';subprocess.run(['git','-C',str(S),'bundle','create',str(bundle.resolve()),'HEAD'],check=True)
record=dict(generator_source_commit=commit,source_manifest_sha256=sha(manifest),bundle_sha256=sha(bundle),files=len(rows),method_runtime_commit='bdfa3b1307d267a5a4caf6484e1ad465c39a592e',prepared_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),selected_sources=False,final_new_source_config_frozen=False,remote_staged=False,neural_oracle_executed=False,gpu_launched=False)
dest=P/'NEW_REFERENCE_GENERATOR_FREEZE_RECORD_v1.json';assert not dest.exists();dest.write_bytes(json.dumps(record,indent=2).encode());print(json.dumps(record,indent=2))
