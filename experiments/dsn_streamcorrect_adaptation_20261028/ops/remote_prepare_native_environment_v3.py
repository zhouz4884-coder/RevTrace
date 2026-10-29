"""Run after asset acquisition and outside measured service runs."""
import pathlib,json,subprocess,sys,hashlib,os,wave
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028'
base=B/'envs/revbatch-cu128/bin/python';env=B/'envs/revtrace-streamcorrect-20261028';cache=B/'cache/revtrace_streamcorrect_20261028'
assert json.loads((O/'assets_v1/GATE.json').read_text())['status']=='PASS_EXACT_NATIVE_ASSETS_ACQUIRED'
cache.mkdir(parents=True,exist_ok=True)
if not env.exists():subprocess.run([str(base),'-m','venv','--system-site-packages',str(env)],check=True)
py=env/'bin/python'
subprocess.run([str(py),'-m','pip','install','--cache-dir',str(cache/'pip'),'--no-deps','peft==0.18.0'],check=True)
bundle=P/'SOURCE_v3.bundle';source=P/'runtime_source_v3'
if not source.exists():
 subprocess.run(['git','clone','--no-hardlinks',str(bundle),str(source)],check=True)
 subprocess.run(['git','-C',str(source),'config','core.autocrlf','false'],check=True)
 subprocess.run(['git','-C',str(source),'checkout','--detach','825b96f60f63f6affb42daf182d0c77e2b9fb7b2'],check=True)
manifest=json.loads((P/'SOURCE_v3.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==manifest['source_commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'],text=True)
for x in manifest['files']:
 b=(source/x['path']).read_bytes();assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256']
plan=json.loads((O/'assets_v1/PUBLIC_PLAN.json').read_text());reference=json.loads((pathlib.Path(plan['dataset_root'])/'reference.json').read_text())
summary=dict(venv=str(env),python=str(py),source=str(source),source_commit=manifest['source_commit'],source_files=len(manifest['files']),
 reference_type=type(reference).__name__,reference_rows=len(reference),
 reference_item_fields=list(reference[0]) if isinstance(reference,list) and reference else [],gpu_launched=False)
(O/'ENV_PREPARATION.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False,indent=2))
