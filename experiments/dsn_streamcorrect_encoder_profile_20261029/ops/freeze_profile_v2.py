"""Narrow prelaunch revision: full cost coverage and truthful E bit provenance."""
import datetime,hashlib,json,pathlib,shutil,subprocess
F=pathlib.Path(__file__).resolve().parents[1];src=F/'source_v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(src/'profile_worker.py')==sha(F/'source_v1/profile_worker.py')
assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()
tracked=subprocess.check_output(['git','ls-files'],cwd=src,text=True).splitlines()
files=[dict(path=x,bytes=(src/x).stat().st_size,sha256=sha(src/x)) for x in tracked]
cfg=json.loads((F/'PROFILE_PLAN_v1_FROZEN.json').read_text(encoding='utf-8'))
cfg.update(experiment_id='SC_ENCODER_FOUR_FIXED_PAIRS_COMPONENT_PROFILE_V2',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),profile_source_commit=commit,profile_source_files={x['path']:x['sha256'] for x in files},out=cfg['out'].replace('profile_v1','profile_v2'),
 supersedes='V1 prelaunch plan only; NN calls0. V2 covers complete pre-E and post-E taxes and separates original GPU E readback from received wire digest; worker unchanged.')
cfg['gate']=dict(original_two_GPU_mel_and_E_bits_match=True,received_wire_digest_matches_original=True,received_actual_D_C_U_full_oracle=True,received_GPU_E_independently_hashed=False,fixed_potential_exports=14,fixed_uses=4,net_expected_resource_margin_seconds_at_least=.100,positive_profile_does_not_authorize_deployed_claim=True)
cp=F/'PROFILE_PLAN_v2_FROZEN.json';assert not cp.exists();cp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
packages=F/'packages';mp=packages/'SOURCE_v2.json';assert not mp.exists()
mp.write_text(json.dumps(dict(source_commit=commit,files=files,scope='13-call E component generator; unchanged NN worker; imported runtime bdfa distinct'),indent=2)+'\n',encoding='utf-8')
(packages/'SOURCE_v2_LOCAL_PREFLIGHT.json').write_text(json.dumps(dict(code_commit=commit,source_commit=commit,files=files),indent=2)+'\n',encoding='utf-8')
snap=F/'source_snapshot_v2';snap.mkdir(exist_ok=False)
for x in tracked:shutil.copyfile(src/x,snap/x)
bundle=packages/'SOURCE_v2.bundle';subprocess.run(['git','bundle','create',str(bundle.resolve()),'HEAD'],cwd=src,check=True)
(F/'FREEZE_RECORD_v2.json').write_text(json.dumps(dict(source_commit=commit,files=len(files),manifest_sha256=sha(mp),plan_sha256=sha(cp),bundle_sha256=sha(bundle),worker_identical_to_v1=True),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(source_commit=commit,files=len(files),manifest_sha256=sha(mp),plan_sha256=sha(cp))))
