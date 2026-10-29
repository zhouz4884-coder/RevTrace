"""CPU-only isolated package overlay and complete own-source preparation."""
import pathlib,subprocess,json,hashlib,os,sys,datetime
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028';cache=B/'cache/revtrace_streamcorrect_20261028'
assert json.loads((O/'assets_v1/GATE.json').read_text())['status']=='PASS_EXACT_NATIVE_ASSETS_ACQUIRED'
base=B/'envs/revbatch-cu128/bin/python';target=B/'envs/revtrace-streamcorrect-20261028';cache.mkdir(parents=True,exist_ok=True)
if not target.exists():subprocess.run([str(base),'-m','venv','--system-site-packages',str(target)],check=True)
py=target/'bin/python'
base_site=subprocess.check_output([str(base),'-c','import sysconfig;print(sysconfig.get_paths()["purelib"])'],text=True).strip()
target_site=pathlib.Path(subprocess.check_output([str(py),'-c','import sysconfig;print(sysconfig.get_paths()["purelib"])'],text=True).strip())
assert pathlib.Path(base_site).is_relative_to(B) and target_site.is_relative_to(B)
pth=target_site/'revtrace_validated_base_readonly.pth';body=base_site+'\n'
if pth.exists():assert pth.read_text()==body
else:pth.write_text(body)
e=dict(os.environ,CUDA_VISIBLE_DEVICES='',PIP_CACHE_DIR=str(cache/'pip'),HF_HOME=str(cache/'huggingface'),TORCH_HOME=str(cache/'torch'),TRITON_CACHE_DIR=str(cache/'triton'),XDG_CACHE_HOME=str(cache/'xdg'),NUMBA_CACHE_DIR=str(cache/'numba'),PYTHONDONTWRITEBYTECODE='1')
subprocess.run([str(py),'-m','pip','install','--no-deps','--cache-dir',str(cache/'pip'),'peft==0.18.0'],check=True,env=e)
source=P/'runtime_source_v8';bundle=P/'SOURCE_v8.bundle'
assert hashlib.sha256(bundle.read_bytes()).hexdigest()=='3d57a1245b6897ef73371c512d32a76127a47f6442d9d74687ef296ead1f734e'
if not source.exists():
 subprocess.run(['git','clone','--no-hardlinks',str(bundle),str(source)],check=True)
 subprocess.run(['git','-C',str(source),'config','core.autocrlf','false'],check=True)
 subprocess.run(['git','-C',str(source),'checkout','--detach','61c9afac00561f7ff1351f3eba9fd95adb239e8c'],check=True)
manifest=json.loads((P/'SOURCE_v8.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==manifest['source_commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'],text=True)
for r in manifest['files']:
 b=(source/r['path']).read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
probe='''import json,importlib.metadata,torch,transformers,peft,torchaudio,datasets,tiktoken,soundfile,numpy
print(json.dumps(dict(packages={k:importlib.metadata.version(k) for k in ("torch","transformers","peft","torchaudio","datasets","tiktoken","soundfile","numpy")},cuda_initialized=torch.cuda.is_initialized(),torch_file=torch.__file__,peft_file=peft.__file__)))'''
result=subprocess.check_output([str(py),'-B','-c',probe],env=e,text=True);details=json.loads(result)
assert not details['cuda_initialized']
record=dict(status='PASS_ISOLATED_NATIVE_IMPORTS_CPU_ONLY',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),python=str(py),base_readonly_package_layer=base_site,overlay_site=str(target_site),overlay_pth_sha256=hashlib.sha256(pth.read_bytes()).hexdigest(),source_commit=manifest['source_commit'],source_files=len(manifest['files']),**details,gpu_launched=False)
(O/'CPU_ENV_PREPARATION_v8.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
