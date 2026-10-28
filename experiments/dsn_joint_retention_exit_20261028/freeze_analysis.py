"""Make an independent byte-frozen Git source package; leave runtime untouched."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys

W=Path(__file__).resolve().parent
S=W/'analysis_source_v1'
FILES=['PROTOCOL.zh.md','build_plan.py','joint_recount.py','development_recount.py','test_joint_analysis.py']

def git(*args):return subprocess.check_output(['git','-C',str(S),*args],text=True).strip()
def put(path,value):
    with path.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')

def main():
    S.mkdir(exist_ok=False)
    for name in FILES:shutil.copyfile(W/name,S/name)
    (S/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf8')
    git('init','--initial-branch=codex/dsn-joint-analysis-v1');git('config','core.autocrlf','false')
    git('config','user.name','RevTrace Research');git('config','user.email','revtrace-research@users.noreply.github.com')
    git('add','--all');git('commit','-m','Freeze independent retention x coverage-exit experiment analysis')
    commit=git('rev-parse','HEAD');tracked=sorted(set(git('ls-files','-z').split('\0'))-{''})
    rows=[dict(path=n,bytes=(S/n).stat().st_size,sha256=hashlib.sha256((S/n).read_bytes()).hexdigest()) for n in tracked]
    put(W/'ANALYSIS_SOURCE_v1.json',dict(code_commit=commit,files=rows,
        scope='Independent CPU/offline plan and analysis package; neural execution remains frozen f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf'))
    bundle=W/'ANALYSIS_SOURCE_v1.bundle';git('bundle','create',str(bundle),'HEAD')
    test=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(S),'-p','test_joint_analysis.py','-v'],capture_output=True,text=True)
    (W/'CPU_TESTS_v1.log').write_text(test.stdout+test.stderr,encoding='utf8')
    put(W/'ANALYSIS_SOURCE_GATE_v1.json',dict(gate='PASS_ANALYSIS_SOURCE_AND_ADVERSARIAL_CPU' if not test.returncode else 'FAIL_CPU_PRESERVED',
        code_commit=commit,git_clean=not git('status','--porcelain','--untracked-files=all'),files=len(rows),
        manifest_sha256=hashlib.sha256((W/'ANALYSIS_SOURCE_v1.json').read_bytes()).hexdigest(),
        bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),
        test_returncode=test.returncode,tests='5 tests: fixed factorial/shared actuator and adversarial exact ancestry',
        python=sys.version,log_sha256=hashlib.sha256((W/'CPU_TESTS_v1.log').read_bytes()).hexdigest()))
    print((W/'ANALYSIS_SOURCE_GATE_v1.json').read_text())
    if test.returncode:raise SystemExit(test.returncode)

if __name__=='__main__':main()
