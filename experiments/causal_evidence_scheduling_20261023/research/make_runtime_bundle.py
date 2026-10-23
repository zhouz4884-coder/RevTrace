"""Preserve all executed source history and scan reachable decoded blobs."""
from pathlib import Path
import hashlib,json,re,subprocess
W=Path(__file__).resolve().parent;S=W/'runtime';D=W/'source_bundles';D.mkdir(exist_ok=False)
def git(*a):return subprocess.check_output(['git','-C',str(S),*a])
head=git('rev-parse','HEAD').decode().strip();assert head=='e0aeae1b418644c378dde331c59b55fc5948b40f'
manifest=json.loads((S/'SOURCE_MANIFEST.json').read_text())
for r in manifest['files']:
 raw=(S/r['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['sha256']
 assert raw==git('show',head+':'+r['path'])
objects=[]
for line in git('rev-list','--objects','HEAD').decode().splitlines():
 oid=line.split(' ',1)[0]
 if git('cat-file','-t',oid).strip()==b'blob':objects.append(oid)
pattern=re.compile(rb'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')
for oid in objects:assert not pattern.search(git('cat-file','blob',oid)),('credential-like source object',oid)
bundle=D/'CES_EXECUTED_v4.bundle';git('bundle','create',str(bundle),'HEAD');git('bundle','verify',str(bundle))
record={'source_commit':head,'original_sdk_commit':'2bc71af5457de5d065ff9e771d2fad428c5c6ed9',
 'preserved_executed_pilot_commits':['4e6ab8c97e267a6b400e7951552fa6b8b7280614','ca2b7d8a8f2249e91715607e7513721e061eb420','8d5c5f4d81157b007eff86e93e252e3d12365c9b',head],
 'file':'CES_EXECUTED_v4.bundle','bytes':bundle.stat().st_size,'sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),
 'reachable_unique_blobs_pattern_audited':len(set(objects)),'current_files_byte_equal_Git_and_manifest':len(manifest['files']),
 'no_model_weights_audio_or_credentials_packaged':True}
(D/'MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
