import pathlib,subprocess,json,hashlib,ast
T=pathlib.Path(__file__).resolve().parents[1];S=T/'auditfix_source_v1';P=T/'packages';snap=T/'auditfix_snapshot_v1'
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
assert not git('status','--porcelain','--untracked-files=all');rows=[]
for rel in git('ls-files','-z').split('\0'):
 if not rel:continue
 b=(S/rel).read_bytes()
 if rel.endswith('.py'):ast.parse(b.decode())
 rows.append(dict(path=rel,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
commit=git('rev-parse','HEAD');manifest=P/'AUDITFIX_SOURCE_v1.json';assert not manifest.exists();manifest.write_text(json.dumps(dict(source_commit=commit,code_commit=commit,files=rows,scope='corrective offline auditor/controller only; actual native execution retains source61c9afac00561f7ff1351f3eba9fd95adb239e8c'),indent=2))
bundle=P/'AUDITFIX_SOURCE_v1.bundle';assert not bundle.exists();subprocess.run(['git','-C',str(S),'bundle','create',str(bundle.resolve()),'HEAD'],check=True);snap.mkdir(exist_ok=False)
for row in rows:(snap/row['path']).write_bytes((S/row['path']).read_bytes())
r=dict(source_commit=commit,files=len(rows),source_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),actual_native_execution_source_unchanged='61c9afac00561f7ff1351f3eba9fd95adb239e8c')
(P/'AUDITFIX_FREEZE_v1.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
