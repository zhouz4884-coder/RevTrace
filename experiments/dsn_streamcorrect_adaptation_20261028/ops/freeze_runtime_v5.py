import pathlib,subprocess,json,hashlib,sys
T=pathlib.Path(__file__).resolve().parents[1];S=T/'source_v5';P=T/'packages';snap=T/'source_snapshot_v5'
def git(*a):return subprocess.check_output(['git','-C',str(S),*a]).decode().strip()
assert not git('status','--porcelain','--untracked-files=all')
commit=git('rev-parse','HEAD');rows=[]
for rel in git('ls-files','-z').split('\x00'):
 if not rel:continue
 b=(S/rel).read_bytes();rows.append(dict(path=rel,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
mf=P/'SOURCE_v5.json';assert not mf.exists();mf.write_text(json.dumps(dict(source_commit=commit,files=rows,scope='actual native service plus private identity prediction; controlled fixed-chunk front end'),indent=2))
bundle=P/'SOURCE_v5.bundle';assert not bundle.exists();subprocess.run(['git','-C',str(S),'bundle','create',str(bundle.resolve()),'HEAD'],check=True)
snap.mkdir(exist_ok=False)
for x in rows:
 q=snap/x['path'];q.parent.mkdir(exist_ok=True,parents=True);q.write_bytes((S/x['path']).read_bytes())
r=dict(source_commit=commit,source_manifest_sha256=hashlib.sha256(mf.read_bytes()).hexdigest(),bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),files=len(rows))
(P/'FREEZE_RECORD_v5.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
