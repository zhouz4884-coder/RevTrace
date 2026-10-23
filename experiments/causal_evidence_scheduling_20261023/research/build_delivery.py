"""Additive bounded artifact; do not include weights/audio/large raw traces."""
from pathlib import Path
import gzip,hashlib,json,re,shutil
W=Path(__file__).resolve().parent;D=W/'delivery_final';assert not D.exists();D.mkdir()
def copy(p,rel):
 q=D/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def tree(root,rel):
 for p in sorted(root.rglob('*')):
  if p.is_file():copy(p,rel+'/'+p.relative_to(root).as_posix())
copy(W/'README_DELIVERY.md','README.md')
(D/'.gitattributes').write_text('* -text\n')
tree(W/'collected','evidence')
tree(W/'reports','reports')
tree(W/'source_bundles','source_bundles')
source=json.loads((W/'runtime/SOURCE_MANIFEST.json').read_text())
for r in source['files']:copy(W/'runtime'/r['path'],'runtime/'+r['path'])
copy(W/'runtime/SOURCE_MANIFEST.json','runtime/SOURCE_MANIFEST.json')
for p in sorted(W.glob('*.py')):copy(p,'research/'+p.name)
for p in sorted(W.glob('*.sh')):copy(p,'research/'+p.name)
for n in ['PROTOCOL.md','FORMAL_FREEZE.md','CES_ALGORITHM.md','SAFETY_OBLIGATIONS.md','METRIC_SCOPE.md','WORKLOG.md','OBSERVED_FAILURE_NOTES.zh.md']:
 copy(W/n,'protocol/'+n)
for n in ['INTAKE.json','SOURCE_SCOPE_AUDIT.json','FULL_CES_POLICY_EQUIVALENCE_v4.json','COLLECTION_AUDIT.json',
 'INDEPENDENT_ACTUAL_RECOMPUTE.json','PAPER_AFTER_AUDIT.json','FORMAL_RELEASE_BYTE_AUDIT.json','FORMAL_RELEASE_REMOTE.json',
 'MATRIX_IDENTITY_REMOTE.json','INDEX_AND_RELEASE_REMOTE.json','RAW_EVIDENCE_INDEX_REMOTE.json','BOUNDED_ARCHIVE_REMOTE.json',
 'RUNTIME_SOURCE_EXECUTED_v1.json','RUNTIME_SOURCE_EXECUTED_v2.json','RUNTIME_SOURCE_EXECUTED_v3.json','RUNTIME_SOURCE_EXECUTED_v4.json']:
 copy(W/n,'provenance/'+n)
for name in ['cpu_tests_v1','cpu_tests_v2','cpu_tests_v3','cpu_tests_v4','cpu_tests_v5']:tree(W/name,'reports/local_cpu/'+name)
pattern=re.compile(rb'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')
rows=[]
for p in sorted(D.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(D).as_posix();raw=p.read_bytes();assert '.git' not in p.parts and p.suffix not in ['.wav','.flac','.safetensors','.pt','.bin','.pyc']
 assert len(raw)<20_000_000,(rel,len(raw))
 assert not pattern.search(raw),('credential-pattern',rel)
 if p.suffix=='.gz':assert not pattern.search(gzip.decompress(raw)),('credential-pattern-gzip',rel)
 rows.append({'path':rel,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
assert not any('password=' in (D/p['path']).read_text(errors='ignore') for p in rows if p['path'].endswith('.sh'))
meta={'experiment_id':'REVTRACE-CES-20261023','status':'COMPLETE_RESEARCH_CES_V4_INDEPENDENT_INCREMENT_NO_GO',
 'research_complete':True,'formal_cells':180,'pilot_cells':33,'source_commit':source['code_commit'],
 'evidence_base_commit':'23ba88cfc2ff73cfa209847d4a8866ef5272c8ad','independent_new_C2_algorithm':'NO_GO',
 'all_original_and_negative_results_preserved':True,'paper_unchanged_files':1298,
 'raw_index_sha256':'e6b502b4f478fe275350bb16dc079277559a250ae95982daa6b29e0ce470ef32','files':rows}
(D/'MANIFEST.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps({'files':len(rows)+1,'bytes':sum(r['bytes'] for r in rows),'manifest_sha256':hashlib.sha256((D/'MANIFEST.json').read_bytes()).hexdigest()}))
