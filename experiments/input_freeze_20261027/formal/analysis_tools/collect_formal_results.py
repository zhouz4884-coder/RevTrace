"""SFTP-only bounded scientific outputs, independently re-check named outcomes."""
from pathlib import Path
import hashlib,importlib.util,json,re,stat
P=Path(__file__).resolve().parent;O=P/'formal_results';O.mkdir(exist_ok=True)
R='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/freeze_boundary_20261027/formal'
spec=importlib.util.spec_from_file_location('approved',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
c=helper.ssh_client();s=c.open_sftp();s.get_channel().settimeout(30);index=[];excluded=[]
try:
    def visit(remote,rel=''):
        for ent in s.listdir_attr(remote):
            localrel=(rel+'/'+ent.filename).lstrip('/')
            if stat.S_ISDIR(ent.st_mode):
                if ent.filename in ['states','.tlacache','tmp']:
                    excluded.append(dict(path=localrel,reason='engine scratch/cache; scientific stdout/stderr, proofs/configs and counterexample text retained'))
                else:visit(remote+'/'+ent.filename,localrel)
            elif stat.S_ISREG(ent.st_mode):
                if ent.st_size>2_000_000:raise RuntimeError('bounded scientific file exceeds review limit '+localrel)
                data=s.open(remote+'/'+ent.filename,'rb').read();h=hashlib.sha256(data).hexdigest()
                target=O/localrel;target.parent.mkdir(parents=True,exist_ok=True)
                if target.exists():assert target.read_bytes()==data,localrel
                else:target.write_bytes(data)
                index.append(dict(path=remote+'/'+ent.filename,relative=localrel,bytes=len(data),sha256=h))
    visit(R)
finally:s.close();c.close()
freeze=json.loads((O/'full_v5/FREEZE.json').read_text());summary=json.loads((O/'full_v5/SUMMARY.json').read_text())
expected={r['id']:r for r in freeze['runs']};actual={r['id']:r for r in summary['TLC']}
assert summary['status']=='COMPLETE_EXPECTED' and set(expected)==set(actual) and len(actual)==21
independent=[]
for name,x in expected.items():
    d=O/'full_v5'/name;r=json.loads((d/'RESULT.json').read_text())
    stdout=(d/'stdout.txt').read_bytes();stderr=(d/'stderr.txt').read_bytes()
    assert hashlib.sha256(stdout).hexdigest()==r['stdout_sha256']
    assert hashlib.sha256(stderr).hexdigest()==r['stderr_sha256']
    text=(stdout+stderr).decode()
    ok=(r['exit_code']==0 and 'No error has been found' in text) if x['expected']=='PASS' else (r['exit_code']!=0 and 'Invariant '+x['target']+' is violated' in text)
    assert ok and not r['timed_out']
    match=re.search(r'([\d,]+) states generated, ([\d,]+) distinct states found',text)
    counts=[int(v.replace(',','')) for v in match.groups()]
    assert counts==[r['generated_states'],r['distinct_states']]
    independent.append(dict(id=name,expected=x['expected'],target=x['target'],generated=counts[0],distinct=counts[1],verified=True))
proof=O/'full_v5/tlaps-ProtocolProofs';pr=json.loads((proof/'RESULT.json').read_text())
prooftext=(proof/'stdout.txt').read_text()+(proof/'stderr.txt').read_text()
assert pr['exit_code']==0 and 'All 20 obligations proved.' in prooftext and '[ERROR]' not in prooftext
sources=json.loads((P/'FORMAL_SOURCE_v5.json').read_text())
for f in sources['files']:
    local=P/'formal_v1'/f['path'];assert hashlib.sha256(local.read_bytes()).hexdigest()==f['sha256']
    if local.suffix in ['.tla','.cfg']:
        for d in (O/'full_v5').iterdir():
            candidate=d/f['path']
            if candidate.is_file():assert hashlib.sha256(candidate.read_bytes()).hexdigest()==f['sha256']
result=dict(gate='PASS_BOUNDED_RESULT_AND_SOURCE_RECOUNT',source_commit=sources['code_commit'],
 actual_TLC_configs=21,positive_checks=sum(r['expected']=='PASS' for r in independent),
 expected_counterexamples=sum(r['expected']=='VIOLATION' for r in independent),TLC=independent,
 TLAPS=dict(theorems=10,proved_obligations=20,backend='SMT/Z3 via TLAPS1.5.0; no Isabelle-C flag',
           proof_module_sha256=hashlib.sha256((proof/'ProtocolProofs.tla').read_bytes()).hexdigest()),
 scope='Independent log/source-byte recount, not a separately implemented logical proof or a GPU experiment',
 indexed_files=len(index),indexed_bytes=sum(x['bytes'] for x in index),excluded_scratch=excluded)
(O/'RAW_INDEX.json').write_text(json.dumps(dict(files=index,excluded_scratch=excluded),indent=2)+'\n')
(O/'INDEPENDENT_RECOUNT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['TLC','excluded_scratch']},indent=2))
