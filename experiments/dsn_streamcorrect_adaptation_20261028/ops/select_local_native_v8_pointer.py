import pathlib,json,hashlib
T=pathlib.Path(__file__).resolve().parents[1];root=T.parents[1];p=root/'experiments/repository_identity_20261027/CURRENT.json';b=p.read_bytes();x=json.loads(b)
assert x['source_commit']=='6ec7612d26a6664bc28a656217175637d98e1f5a'
backup=T/'CURRENT_BEFORE_NATIVE_v8_20261029.json';assert not backup.exists();backup.write_bytes(b)
mf=T/'packages/SOURCE_v8_LOCAL_PREFLIGHT.json';m=json.loads(mf.read_text());x.update(source_worktree=str(T/'source_v8'),source_commit=m['code_commit'],source_manifest=str(mf),source_manifest_sha256=hashlib.sha256(mf.read_bytes()).hexdigest(),previous_pointer=str(backup),GPU_queue='NATIVE_V8_SIGNED_MEDIAN_CONTROLS_THEN_ORIGINAL_SCOPE',updated_date='2026-10-29',scope='Machine-local source pointer only; v6 API failure and v7 invalid nonnegative-domain control are preserved; v8 requires actual signed finite GPU oracle gate before new service campaign.')
p.write_text(json.dumps(x,indent=2));print(json.dumps(dict(source_commit=x['source_commit'],source_manifest_sha256=x['source_manifest_sha256']),indent=2))
