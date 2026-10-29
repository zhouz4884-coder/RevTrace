import pathlib,subprocess,json,hashlib,ast
T=pathlib.Path(__file__).resolve().parents[1];S=T/'feedback_characterization_source_v1';P=T/'packages';snap=T/'feedback_characterization_snapshot_v1'
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
assert not git('status','--porcelain','--untracked-files=all')
ast.parse((S/'native_feedback_characterization.py').read_text())
commit=git('rev-parse','HEAD');rows=[]
for name in git('ls-files','-z').split('\0'):
 if name:
  b=(S/name).read_bytes();rows.append(dict(path=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
mf=P/'FEEDBACK_CHARACTERIZATION_SOURCE_v1.json';assert not mf.exists();mf.write_text(json.dumps(dict(source_commit=commit,code_commit=commit,files=rows,scope='independent post-run CPU-only raw/whitespace/surface/empty feedback and exact same-input fullstate characterization; no original gate change'),indent=2))
bundle=P/'FEEDBACK_CHARACTERIZATION_SOURCE_v1.bundle';assert not bundle.exists();subprocess.run(['git','-C',str(S),'bundle','create',str(bundle.resolve()),'HEAD'],check=True)
snap.mkdir(exist_ok=False)
for row in rows:
 p=snap/row['path'];p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes((S/row['path']).read_bytes())
record=dict(source_commit=commit,source_manifest_sha256=hashlib.sha256(mf.read_bytes()).hexdigest(),bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),files=len(rows),syntax_checked=True,native_neural_calls=0)
(P/'FEEDBACK_CHARACTERIZATION_FREEZE_v1.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
