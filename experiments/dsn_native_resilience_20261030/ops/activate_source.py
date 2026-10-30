"""Root-owned current source selector; never changes historical experiment records."""
import argparse,hashlib,json,pathlib,subprocess,sys
R=pathlib.Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser();p.add_argument('--candidate',type=pathlib.Path,required=True);p.add_argument('--record',type=pathlib.Path,required=True);p.add_argument('--backup',type=pathlib.Path,required=True);a=p.parse_args()
read=lambda p:json.loads(p.read_bytes())
c=read(a.candidate);manifest=pathlib.Path(c['source_manifest'])
assert hashlib.sha256(manifest.read_bytes()).hexdigest()==c['source_manifest_sha256']
assert subprocess.check_output(['git','-C',c['source_worktree'],'rev-parse','HEAD'],text=True).strip()==c['source_commit']
pointer=R/'experiments/repository_identity_20261027/CURRENT.json';assert not a.backup.exists() and not a.record.exists();a.backup.write_bytes(pointer.read_bytes());x=read(pointer)
for k in ('source_worktree','source_manifest','source_manifest_sha256','source_commit','GPU_queue'):x[k]=c[k]
x.update(scope='Machine-local actual next-run source identity; historical runs retain their own actual commits.',previous_pointer=str(a.backup.resolve()))
pointer.write_bytes((json.dumps(x,indent=2)+'\n').encode())
r=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],cwd=R,capture_output=True,check=True)
d=json.loads(r.stdout);assert d['gate']=='SOURCE_IDENTITY_PASS' and d['code_commit']==c['source_commit'];a.record.write_bytes(r.stdout);print(r.stdout.decode())

