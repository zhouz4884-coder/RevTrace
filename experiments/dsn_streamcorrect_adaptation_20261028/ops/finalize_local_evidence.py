import pathlib,json,hashlib,subprocess,shutil,datetime
T=pathlib.Path(__file__).resolve().parents[1];S=T/'source_v1';P=T/'packages'
mf=P/'SOURCE_v1.json';m=json.loads(mf.read_text());bundle=P/'SOURCE_v1.bundle'
snap=T/'source_snapshot_v1';snap.mkdir(exist_ok=False)
for x in m['files']:
 b=(S/x['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==x['sha256']
 q=snap/x['path'];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
root=T.parents[1]
assert subprocess.check_output(['git','-C',str(root),'cat-file','-t',m['source_commit']],text=True).strip()=='commit'
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain','--untracked-files=all'],text=True)
r=dict(time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=m['source_commit'],
 source_manifest_sha256=hashlib.sha256(mf.read_bytes()).hexdigest(),source_bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),
 source_checkout_clean=True,root_commit_resolvable=True,source_snapshot_files=len(m['files']),
 cpu_gate=json.loads((T/'cpu_gate_v1/GATE.json').read_text()),
 status='PAUSED_FOR_REQUIRED_NATIVE_BACKBONE_ACCESS',native_neural_calls=0,real_application_service_cells=0,
 missing_precondition='authorized exact original meta-llama/Llama-3.2-1B-Instruct backbone',
 correction_witness_available=False,scientific_failure_claim=False)
(P/'FREEZE_RECORD_v1.json').write_text(json.dumps(r,indent=2))
readme=T/'README.zh.md';c=readme.read_text(encoding='utf-8');c=c.replace('fd878ec2f743af581103c972b2d41f303c4fbc02',m['source_commit']);readme.write_text(c,encoding='utf-8')
print(json.dumps(r,indent=2))
