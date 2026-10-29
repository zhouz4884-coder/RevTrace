import datetime,hashlib,json,os,pathlib,platform,shutil,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];src=F/'analysis_source_v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip();tracked=subprocess.check_output(['git','ls-files'],cwd=src,text=True).splitlines()
files=[dict(path=p,bytes=(src/p).stat().st_size,sha256=sha(src/p)) for p in tracked]
for p in ('analyze_pilot_content.py','native_content_endpoint.py','test_pilot_content.py'):assert (src/p).read_bytes()==(F/'analysis_source_v1'/p).read_bytes()
mp=F/'packages/ANALYSIS_SOURCE_v2.json';assert not mp.exists();mp.write_text(json.dumps(dict(source_commit=commit,code_commit=commit,files=files,scope='local offline final16, pre-recount namespace repair; endpoints unchanged'),indent=2)+'\n',encoding='utf-8')
snap=F/'analysis_snapshot_v2';snap.mkdir(exist_ok=False)
for p in tracked:shutil.copyfile(src/p,snap/p)
bundle=F/'packages/ANALYSIS_SOURCE_v2.bundle';subprocess.run(['git','bundle','create',str(bundle.resolve()),'HEAD'],cwd=src,check=True)
t=read(F/'FINAL_ANALYSIS_TEMPLATE_v1_FROZEN.json');t.update(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_manifest_sha256=sha(mp),supersedes='V1 never used on actual service results. Rename frozen-config path to avoid provenance dictionary shadow; add actual main-loop CPU regression control. No endpoint/rule changes.')
t['common']['analysis_source_commit']=commit;tp=F/'FINAL_ANALYSIS_TEMPLATE_v2_FROZEN.json';assert not tp.exists();tp.write_text(json.dumps(t,indent=2)+'\n',encoding='utf-8')
out=F/'ANALYSIS_CPU_CONTROLS_v2';out.mkdir(exist_ok=False)
r=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(src),'-p','test_*.py','-v'],capture_output=True,text=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES=''))
(out/'CPU_CONTROLS.log').write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode==0 and 'Ran 23 tests' in r.stderr and 'skipped' not in r.stderr
for row in files:assert sha(src/row['path'])==row['sha256']
assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
for name,obj in [('GATE.json',dict(status='PASS_FROZEN_23_LOCAL_CPU_CONTROLS_NO_SERVICE_RECOUNT_YET',tests=23,skips=0,code_commit=commit,source_manifest_sha256=sha(mp),template_sha256=sha(tp))),('ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),model_calls=0,remote_operations=0,gpu_calls=0)),('RUN_RECORD.json',dict(experiment_id='SC_INDEPENDENT_FINAL_ANALYSIS_CPU_V2',code_commit=commit,frozen_config=str(tp.resolve()),frozen_config_sha256=sha(tp),environment_record=str((out/'ENVIRONMENT.json').resolve()),raw=str(out),gate=str(out/'GATE.json'),scope='CPU controls only; no newsource service results consumed'))]:
 (out/name).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(source_commit=commit,files=len(files),manifest_sha256=sha(mp),template_sha256=sha(tp),CPU_gate_sha256=sha(out/'GATE.json'))))
