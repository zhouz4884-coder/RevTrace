"""Record bounded local CPU controls; never run a GPU controller."""
from pathlib import Path
import hashlib,json,os,platform,subprocess,sys,time
P=Path(__file__).resolve().parent
R=Path(r'D:\VLA_QWEN\RevTrace\.execution\lp1_runtime')
env=dict(os.environ,PYTHONPATH=str(R),PYTHONDONTWRITEBYTECODE='1')
started=time.time()
cmd=[sys.executable,'-B','-m','unittest','-v','test_paired_recovery.py']
tests=subprocess.run(cmd,cwd=P,env=env,text=True,capture_output=True)
patch=subprocess.run(['git','-C',str(R),'apply','--check',str(P/'recovery_runner.patch')],text=True,capture_output=True)
reverse=subprocess.run(['git','-C',str(R),'apply','--reverse','--check',str(P/'recovery_runner.patch')],text=True,capture_output=True)
patch_state='APPLIES_TO_BASELINE' if patch.returncode==0 else 'ALREADY_INTEGRATED_BY_PARENT' if reverse.returncode==0 else 'CONTEXT_CHANGED_UNVERIFIED'
for name,content in [('CPU_TEST.log',tests.stdout+tests.stderr),('PATCH_CHECK.log',patch.stdout+patch.stderr)]:
    (P/name).write_text(content,encoding='utf8')
result=dict(gate='PASS_CPU24_AND_PATCH_CONTEXT' if tests.returncode==0 and patch_state!='CONTEXT_CHANGED_UNVERIFIED' else 'FAIL',
    expected_tests=24,tests_returncode=tests.returncode,patch_returncode=patch.returncode,
    reverse_check_returncode=reverse.returncode,patch_state=patch_state,
    python=sys.version,platform=platform.platform(),started_unix=started,ended_unix=time.time(),
    GPU_calls=0,remote_calls=0,runtime_mutations=0,argv=cmd,
    source={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in P.glob('*.py')},
    baseline_runner_sha256=hashlib.sha256((R/'runtime/scripts/run_tc_live_qwen.py').read_bytes()).hexdigest(),
    test_log_sha256=hashlib.sha256((P/'CPU_TEST.log').read_bytes()).hexdigest(),
    scope='ownership/fault/clock/parser fixtures only; GPU recovery unexecuted')
(P/'CPU_GATE.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(result,indent=2));sys.exit(0 if result['gate'].startswith('PASS') else 1)
