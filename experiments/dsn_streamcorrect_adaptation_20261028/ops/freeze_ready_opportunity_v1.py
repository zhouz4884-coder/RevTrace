import pathlib,subprocess,json,hashlib,ast
T=pathlib.Path(__file__).resolve().parents[1];S=T/'ready_opportunity_source_v1';P=T/'packages';snap=T/'ready_opportunity_snapshot_v1'
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
assert not git('status','--porcelain','--untracked-files=all');rows=[]
for rel in git('ls-files','-z').split('\0'):
 if rel:
  b=(S/rel).read_bytes()
  if rel.endswith('.py'):ast.parse(b.decode())
  rows.append(dict(path=rel,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
mf=P/'READY_OPPORTUNITY_SOURCE_v1.json';assert not mf.exists();mf.write_text(json.dumps(dict(source_commit=git('rev-parse','HEAD'),code_commit=git('rev-parse','HEAD'),files=rows),indent=2));bundle=P/'READY_OPPORTUNITY_SOURCE_v1.bundle';assert not bundle.exists();subprocess.run(['git','-C',str(S),'bundle','create',str(bundle.resolve()),'HEAD'],check=True);snap.mkdir(exist_ok=False)
for row in rows:(snap/row['path']).write_bytes((S/row['path']).read_bytes())
r=dict(code_commit=git('rev-parse','HEAD'),manifest_sha256=hashlib.sha256(mf.read_bytes()).hexdigest(),bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest());(P/'READY_OPPORTUNITY_FREEZE_v1.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
