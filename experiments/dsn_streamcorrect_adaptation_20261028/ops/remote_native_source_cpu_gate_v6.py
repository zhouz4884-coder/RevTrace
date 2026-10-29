import pathlib,json,hashlib,subprocess,os,sys
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028'
author=P/'author_StreamCorrect_bbb9f7f';identity=json.loads((O/'public_asset_discovery_v1/SUMMARY.json').read_text())
assert subprocess.check_output(['git','-C',str(author),'rev-parse','HEAD'],text=True).strip()==identity['author_commit']
assert not subprocess.check_output(['git','-C',str(author),'status','--porcelain','--untracked-files=all'],text=True)
for x in identity['source_files']:
 b=(author/x['path']).read_bytes();assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256']
cache=B/'cache/revtrace_streamcorrect_20261028'
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',HF_HOME=str(cache/'huggingface'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',CUDA_VISIBLE_DEVICES='',
 TRITON_CACHE_DIR=str(cache/'triton'),TORCHINDUCTOR_CACHE_DIR=str(cache/'inductor'),TORCH_HOME=str(cache/'torch'),XDG_CACHE_HOME=str(cache/'xdg'),NUMBA_CACHE_DIR=str(cache/'numba'))
source=P/'runtime_source_v6';out=O/'cpu_native_v6'
r=subprocess.run([sys.executable,'-B',str(source/'run_cpu_gate.py'),'--manifest',str(P/'SOURCE_v6.json'),'--out',str(out)],env=env,capture_output=True,text=True)
print(r.stdout);print(r.stderr,file=sys.stderr)
(O/'AUTHOR_DEPENDENCY_GATE_v6.json').write_text(json.dumps(dict(status='PASS_COMPLETE_PINNED_AUTHOR_SOURCE',source=str(author),commit=identity['author_commit'],files=len(identity['source_files']),wrapper_cpu_returncode=r.returncode),indent=2))
raise SystemExit(r.returncode)
