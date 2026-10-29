import hashlib,json,pathlib,shutil,subprocess
H=pathlib.Path(__file__).resolve().parents[1];E=H/'encoder_boundary_review_v1';src=E/'source_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()
pilot=H/'SERVICE_PILOT_RESULTS_v1/SC_STAGE_SERVICE_PILOT_V1_two_full_spec_early_source0_r0'
author=H/'author_reference/simul_whisper/simul_whisper.py'
assert sha(author)=='9f016f71df780c05b04719633ed302b502a457ff18a086eb5412a394b05cacb7'
inputs=[pilot/x for x in ('FULLSPEC_LEDGER.json','DISPATCHES.json','native_jobs.jsonl')]+[author]+list((E/'author_reference').iterdir())
files={x:sha(src/x) for x in ('.gitattributes','analyze_encoder_inputs.py')}
cfg=dict(experiment_id='SC_ENCODER_DIFFERING_ROOT_STATIC_WITNESS_V1',source_commit=commit,source_files=files,
 input_files={str(x.resolve()):sha(x) for x in inputs},pilot=str(pilot.resolve()),author_infer=str(author.resolve()),
 out=str((E/'RESULTS_v1').resolve()),scope='Static CPU/readset and existing descriptor checks only. No mel/encoder timing or tensor equality assertion.')
cp=E/'FROZEN_CONFIG_v1.json';assert not cp.exists();cp.write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8')
snap=E/'snapshot_v1';snap.mkdir(exist_ok=False)
for x in files:shutil.copyfile(src/x,snap/x)
bundle=H/'packages/ENCODER_STATIC_BOUNDARY_v1.bundle';subprocess.run(['git','bundle','create',str(bundle.resolve()),'HEAD'],cwd=src,check=True)
(E/'SOURCE_v1.json').write_text(json.dumps(dict(source_commit=commit,files=files,config_sha256=sha(cp),bundle_sha256=sha(bundle),complete_manifest=True),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(source_commit=commit,config_sha256=sha(cp))))
