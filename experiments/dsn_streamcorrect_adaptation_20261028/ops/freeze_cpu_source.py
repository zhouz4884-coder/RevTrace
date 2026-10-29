"""Freeze own CPU adapter source and run its source-gated controls."""
import pathlib,subprocess,json,hashlib,sys
T=pathlib.Path(__file__).resolve().parents[1];S=T/'source_v1';G=T/'packages';G.mkdir(exist_ok=True)
def git(*a):return subprocess.check_output(['git','-C',str(S),*a]).decode().strip()
assert not git('status','--porcelain','--untracked-files=all')
commit=git('rev-parse','HEAD');files=[]
for rel in git('ls-files','-z').split('\x00'):
 if not rel:continue
 b=(S/rel).read_bytes();files.append(dict(path=rel,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
manifest=dict(source_commit=commit,scope='own native interface and synthetic CPU state controls only; no native model calls yet',files=files)
mf=G/'SOURCE_v1.json';assert not mf.exists();mf.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
bundle=G/'SOURCE_v1.bundle';assert not bundle.exists()
subprocess.run(['git','-C',str(S),'bundle','create',str(bundle.resolve()),'HEAD'],check=True)
subprocess.run(['git','-C',str(T.parents[1]),'fetch','--no-tags',str(bundle.resolve()),'HEAD:refs/heads/codex/streamcorrect-adapter-v1'],check=True)
out=T/'cpu_gate_v1'
r=subprocess.run([sys.executable,str(S/'run_cpu_gate.py'),'--manifest',str(mf),'--out',str(out)],text=True,capture_output=True)
print(r.stdout);print(r.stderr,file=sys.stderr)
put=dict(source_commit=commit,manifest_sha256=hashlib.sha256(mf.read_bytes()).hexdigest(),bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),cpu_gate_returncode=r.returncode,root_commit_resolvable=True)
(G/'FREEZE_RECORD_v1.json').write_text(json.dumps(put,indent=2));print(json.dumps(put,indent=2))
raise SystemExit(r.returncode)
