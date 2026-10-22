"""Only CPU/raw evidence closure after existing GPU/Oracle/statistics pipeline."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

B = Path(sys.argv[1]); P = B / 'projects/revtrace_online_admission_20261022'; O = B / 'results/revtrace/online_admission_20261022'
meta = json.loads((O / 'POSTPROCESS_PID.json').read_text()); done = []


def live():
    p = Path('/proc') / str(meta['pid']) / 'cmdline'
    return p.exists() and meta['command'] in p.read_bytes().replace(b'\0', b' ').decode()


def step(name, args):
    log = O / ('CLOSURE_' + name + '.log'); assert not log.exists()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', NEURAL_AUDIT_RUNTIME=str(P / 'pilot_sdk_v3'))
    with log.open('w') as f:
        r = subprocess.run([sys.executable, '-u', *args], cwd=P, env=env, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode: raise RuntimeError('CPU closure failed: ' + name)
    done.append(name); (O / 'CLOSURE_PROGRESS.json').write_text(json.dumps({'completed': done}) + '\n')
    print(name, flush=True)


try:
    while not (O / 'POSTPROCESS_SUMMARY.json').exists():
        if (O / 'STOP_POSTPROCESS_v1.json').exists() or (O / 'STOP_FORMAL_v1.json').exists(): raise RuntimeError('Earlier pipeline stopped; no automatic experiment restart')
        assert live(), 'Existing postprocess handle missing without a terminal result'
        time.sleep(5)
    assert json.loads((O / 'POSTPROCESS_SUMMARY.json').read_text())['status'] == 'COMPLETE_FORMAL_ORACLE_AND_CPU_AUDITS'
    while live(): time.sleep(1)
    step('neural_helper_tests', ['-m', 'pytest', '-q', '-p', 'no:cacheprovider', str(P / 'test_neural_feedback_core.py')])
    step('neural_consumption', [str(P / 'audit_neural_feedback_v1.py'), str(B)])
    step('bounded_pack', [str(P / 'pack_remote_evidence_v2.py'), str(B)])
    (O / 'CLOSURE_SUMMARY.json').write_text(json.dumps({'status': 'COMPLETE_CPU_NEURAL_CHAIN_AND_REMOTE_EVIDENCE_CLOSURE',
        'completed': done, 'controller_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'GPU_runs_started_by_this_controller': 0,
        'not_goal_complete': 'Local result inspection, contribution/DSN assessment, candidate outline, GitHub upload/verification and final requirement audit remain'}, indent=2) + '\n')
except BaseException as e:
    (O / 'STOP_CLOSURE_v1.json').write_text(json.dumps({'error': repr(e), 'completed': done, 'no_silent_retry_or_GPU_execution': True}, indent=2) + '\n')
    raise
