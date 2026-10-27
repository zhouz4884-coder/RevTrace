"""Read-only portable verification of bounded formal delivery, no SSH/GPU."""
from pathlib import Path
import hashlib,json,re
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
manifest=read(P/'PACKAGE_MANIFEST.json')
expected={x['path'] for x in manifest['files']}
actual={p.relative_to(P).as_posix() for p in P.rglob('*') if p.is_file() and p.name!='PACKAGE_MANIFEST.json'}
assert actual==expected,('missing',sorted(expected-actual),'extra',sorted(actual-expected))
for f in manifest['files']:
    p=P/f['path'];assert p.stat().st_size==f['bytes'] and sha(p)==f['sha256'],f['path']
source=read(P/'FORMAL_SOURCE_v5.json')
assert source['code_commit']=='996430d24d110facb242b352ba69c2f42f26e69c'
for f in source['files']:assert sha(P/'source_v5'/f['path'])==f['sha256'],f['path']
runset=read(P/'source_v5/RUNS.json');summary=read(P/'formal_results/full_v5/SUMMARY.json')
assert summary['status']=='COMPLETE_EXPECTED' and summary['stage']=='full'
assert summary['source_commit']==source['code_commit']
exp={r['id']:r for r in runset['runs']};got={r['id']:r for r in summary['TLC']}
assert set(exp)==set(got) and len(got)==21
for name,x in exp.items():
    d=P/'formal_results/full_v5'/name;r=read(d/'RESULT.json')
    assert sha(d/'stdout.txt')==r['stdout_sha256'] and sha(d/'stderr.txt')==r['stderr_sha256']
    text=(d/'stdout.txt').read_text(encoding='utf8')+(d/'stderr.txt').read_text(encoding='utf8')
    assert not r['timed_out']
    if x['expected']=='PASS':assert r['exit_code']==0 and 'No error has been found' in text
    else:assert r['exit_code']!=0 and 'Invariant '+x['target']+' is violated' in text
    count=re.search(r'([\d,]+) states generated, ([\d,]+) distinct states found',text)
    assert [int(x.replace(',','')) for x in count.groups()]==[r['generated_states'],r['distinct_states']]
proof=P/'formal_results/full_v5/tlaps-ProtocolProofs';pr=read(proof/'RESULT.json')
text=(proof/'stdout.txt').read_text(encoding='utf8')+(proof/'stderr.txt').read_text(encoding='utf8')
assert pr['exit_code']==0 and 'All 20 obligations proved.' in text and '[ERROR]' not in text
print(json.dumps(dict(gate='PASS_PACKAGED_BYTES_AND_NAMED_FORMAL_OUTCOMES',files=len(expected),
 source_commit=source['code_commit'],TLC_positive=10,TLC_expected_counterexamples=11,TLAPS_obligations=20,
 scope='Read-only evidence verification; not re-execution or production proof')))
