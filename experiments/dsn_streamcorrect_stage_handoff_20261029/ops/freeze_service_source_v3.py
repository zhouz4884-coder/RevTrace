import pathlib,subprocess,json,hashlib
T=pathlib.Path(__file__).resolve().parents[1];S=T/'source_v3';P=T/'packages';snapshot=T/'source_snapshot_v3'
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert not git('status','--porcelain','--untracked-files=all');commit=git('rev-parse','HEAD');rows=[];snapshot.mkdir(exist_ok=False)
for rel in git('ls-files').splitlines():
 data=(S/rel).read_bytes();rows.append(dict(path=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()));(snapshot/rel).write_bytes(data)
m=dict(source_commit=commit,files=rows,scope='actual original full/conservative, full speculative and protected ASR ready-only composition service; no service result inferred by source freeze')
for name,value in [('SOURCE_v3.json',m),('SOURCE_v3_LOCAL_PREFLIGHT.json',dict(m,code_commit=commit))]:(P/name).write_bytes(json.dumps(value,indent=2).encode())
subprocess.run(['git','-C',str(S),'bundle','create',str((P/'SOURCE_v3.bundle').resolve()),'HEAD'],check=True)
r=dict(source_commit=commit,files=len(rows),manifest_sha256=sha(P/'SOURCE_v3.json'),preflight_manifest_sha256=sha(P/'SOURCE_v3_LOCAL_PREFLIGHT.json'),bundle_sha256=sha(P/'SOURCE_v3.bundle'),neural_equivalence_execution_source='99e83a466fee7f1d16830b640cc99e0040d2f147')
(P/'FREEZE_RECORD_v3.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2))
