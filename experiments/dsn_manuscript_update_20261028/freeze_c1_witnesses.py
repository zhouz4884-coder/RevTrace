"""Freeze tiny local CPU witnesses with byte-matched upstream function modules."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
W=Path(__file__).resolve().parent;S=W/'c1_witness_source_v1'
U=W.parent/'physical_retirement_20261028/source_v3'
M=W.parent/'physical_retirement_20261028/packages/SOURCE_v3.json'

def H(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):
    with p.open('x',encoding='utf8') as f:json.dump(v,f,indent=2);f.write('\n')
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()

def main():
    upstream=json.loads(M.read_text());assert upstream['code_commit']=='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf'
    S.mkdir(exist_ok=False);(S/'upstream').mkdir()
    binding=[]
    for name in ['continuity_proof.py','certified_display.py','dgft.py']:
        rel='runtime/src/revtrace/'+name;row=next(r for r in upstream['files'] if r['path']==rel)
        f=U/rel;assert f.stat().st_size==row['bytes'] and H(f)==row['sha256']
        shutil.copyfile(f,S/'upstream'/name);binding.append(row)
    (S/'upstream/__init__.py').write_text('"""Isolated import namespace for exact copied source modules."""\n',encoding='utf8')
    shutil.copyfile(W/'c1_witnesses.py',S/'c1_witnesses.py')
    (S/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf8')
    put(S/'UPSTREAM.json',dict(upstream_source_commit=upstream['code_commit'],source_manifest_sha256=H(M),files=binding,
        scope='Exact copied function-module bytes; isolated import namespace. Not a complete runtime integration or neural execution package.'))
    git('init','--initial-branch=codex/c1-targeted-witness-v1');git('config','core.autocrlf','false')
    git('config','user.name','RevTrace Research');git('config','user.email','revtrace-research@users.noreply.github.com')
    git('add','--all');git('commit','-m','Freeze bounded C1 source-predicate and Consumer witnesses')
    commit=git('rev-parse','HEAD');files=sorted(set(git('ls-files','-z').split('\0'))-{''})
    put(W/'C1_WITNESS_SOURCE_v1.json',dict(code_commit=commit,files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=H(S/n)) for n in files]))
    git('bundle','create',str(W/'C1_WITNESS_SOURCE_v1.bundle'),'HEAD')
    put(W/'C1_WITNESS_CONFIG_v1.json',dict(experiment_id='REVTRACE-C1-TARGETED-CPU-WITNESSES-20261028-v1',
        analysis_code_commit=commit,upstream_source_commit=upstream['code_commit'],expected_cases=12,
        evidence_tier='Targeted pure CPU source-predicate fixtures; not exhaustive model checking or GPU/service results'))
    cmd=[sys.executable,'-B',str(S/'c1_witnesses.py'),'--source-manifest',str(W/'C1_WITNESS_SOURCE_v1.json'),
         '--config',str(W/'C1_WITNESS_CONFIG_v1.json'),'--out',str(W/'C1_WITNESSES_v1')]
    result=subprocess.run(cmd,capture_output=True,text=True)
    (W/'C1_WITNESS_EXECUTION_v1.log').write_text(result.stdout+result.stderr,encoding='utf8')
    print(json.dumps(dict(code_commit=commit,returncode=result.returncode,manifest_sha256=H(W/'C1_WITNESS_SOURCE_v1.json'),
        bundle_sha256=H(W/'C1_WITNESS_SOURCE_v1.bundle'),output=str(W/'C1_WITNESSES_v1'))))
    if result.returncode:print(result.stdout+result.stderr);raise SystemExit(result.returncode)

if __name__=='__main__':main()
