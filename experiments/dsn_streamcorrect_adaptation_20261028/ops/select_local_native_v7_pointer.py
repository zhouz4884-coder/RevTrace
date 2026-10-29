import pathlib,json,hashlib,datetime
T=pathlib.Path(__file__).resolve().parents[1];root=T.parents[1];p=root/'experiments/repository_identity_20261027/CURRENT.json';b=p.read_bytes();x=json.loads(b)
assert x['source_commit']=='a720d02a8cb81db6545d7d9ec6bdc31419dd091d'
backup=T/'CURRENT_BEFORE_NATIVE_v7_20261029.json';assert not backup.exists();backup.write_bytes(b)
mf=T/'packages/SOURCE_v7_LOCAL_PREFLIGHT.json';m=json.loads(mf.read_text());x.update(source_worktree=str(T/'source_v7'),source_commit=m['code_commit'],source_manifest=str(mf),source_manifest_sha256=hashlib.sha256(mf.read_bytes()).hexdigest(),previous_pointer=str(backup),GPU_queue='NATIVE_V7_FROZEN_MEDIAN_CONTROLS_THEN_ORIGINAL_SCOPE',updated_date='2026-10-29',scope='Machine-local source pointer only; preserves v6 warmup failure. v7 requires actual median GPU oracle gate before any new service campaign.')
p.write_text(json.dumps(x,indent=2));print(json.dumps(dict(source_commit=x['source_commit'],source_manifest_sha256=x['source_manifest_sha256'],previous_pointer=str(backup)),indent=2))
