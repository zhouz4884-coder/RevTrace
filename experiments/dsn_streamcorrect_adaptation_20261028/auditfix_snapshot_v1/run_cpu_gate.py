"""Frozen-source CPU-only contract gate; does not validate neural inference."""
import argparse,datetime,hashlib,importlib.metadata,json,os,pathlib,platform,re,subprocess,sys
R=pathlib.Path(__file__).resolve().parent
def put(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def git(*args):return subprocess.check_output(['git','-C',str(R),*args],text=True).strip()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True);a=p.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);manifest=json.loads(a.manifest.read_text(encoding='utf-8'))
 commit=git('rev-parse','HEAD');assert re.fullmatch('[a-f0-9]{40}',commit) and commit==manifest['source_commit']
 assert not git('status','--porcelain','--untracked-files=all')
 tracked=set(git('ls-files','-z').split('\x00'))-{''};assert tracked=={x['path'] for x in manifest['files']}
 for x in manifest['files']:
  b=(R/x['path']).read_bytes();assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256']
 config=dict(experiment_id='DSN_STREAMCORRECT_CPU_INTERFACE_V8',scope='synthetic CPU state-cut, native-audio roundtrip, actual FIFO Consumer and nonempty witness controls only',models_loaded=False,gpu_launched=False,source_commit=commit)
 env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),packages={k:importlib.metadata.version(k) for k in ('torch','numpy')},CUDA_VISIBLE_DEVICES='')
 put(out/'CONFIG.json',config);put(out/'ENVIRONMENT.json',env)
 record=dict(experiment_id=config['experiment_id'],source_commit=commit,source_root=str(R),source_manifest=str(a.manifest.resolve()),source_manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),config_sha256=hashlib.sha256((out/'CONFIG.json').read_bytes()).hexdigest(),environment_sha256=hashlib.sha256((out/'ENVIRONMENT.json').read_bytes()).hexdigest(),raw_result=str(out/'unittest.log'),summary=str(out/'SUMMARY.json'),gate=str(out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 put(out/'RUN_RECORD.json',record)
 e=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
 r=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(R),'-p','test_*.py','-v'],capture_output=True,text=True,env=e)
 (out/'unittest.log').write_text(r.stdout+r.stderr,encoding='utf-8')
 n=re.search(r'Ran (\d+) tests?',r.stdout+r.stderr)
 summary=dict(returncode=r.returncode,tests=int(n[1]) if n else None,native_neural_calls=0,real_service_cells=0,cpu_only=True)
 put(out/'SUMMARY.json',summary);gate=dict(status='PASS_CPU_STATE_CONTRACT_TESTS_ONLY' if r.returncode==0 else 'FAIL_CPU_INTERFACE_PRESERVED',**summary)
 put(out/'GATE.json',gate);print(json.dumps(gate,indent=2));return r.returncode
if __name__=='__main__':raise SystemExit(main())
