import pathlib,json,hashlib,subprocess
T=pathlib.Path(__file__).resolve().parents[1];S=T/'analysis_source_v1';P=T/'packages';snapshot=T/'analysis_snapshot_v1'
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
assert not git('status','--porcelain','--untracked-files=all');commit=git('rev-parse','HEAD');rows=[];snapshot.mkdir(exist_ok=False)
for name in git('ls-files').splitlines():
 data=(S/name).read_bytes();rows.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()));(snapshot/name).write_bytes(data)
(P/'ANALYSIS_SOURCE_v1.json').write_text(json.dumps(dict(source_commit=commit,files=rows),indent=2),encoding='utf-8');subprocess.run(['git','-C',str(S),'bundle','create',str((P/'ANALYSIS_SOURCE_v1.bundle').resolve()),'HEAD'],check=True)
print(json.dumps(dict(source_commit=commit,files=len(rows),source_manifest_sha256=hashlib.sha256((P/'ANALYSIS_SOURCE_v1.json').read_bytes()).hexdigest()),indent=2))
