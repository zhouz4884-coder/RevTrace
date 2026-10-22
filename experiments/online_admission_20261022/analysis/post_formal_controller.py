"""Follow the existing verified controller once, then close the P3 audit loop."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import time

B = Path(sys.argv[1]); P = B / 'projects/revtrace_online_admission_20261022'
O = B / 'results/revtrace/online_admission_20261022'
meta = json.loads((O / 'FORMAL_CONTROLLER_PID.json').read_text())
done = []


def live():
    f = Path('/proc') / str(meta['pid']) / 'cmdline'
    return f.exists() and meta['command'] in f.read_bytes().replace(b'\0', b' ').decode()


def step(name, args):
    log = O / ('POST_' + name + '.log')
    assert not log.exists(), 'No silent repeated post-processing attempt'
    with log.open('w') as f:
        q = subprocess.run([sys.executable, '-u', *args], cwd=P, stdout=f, stderr=subprocess.STDOUT)
    if q.returncode: raise RuntimeError('Retained post-formal failure: ' + name)
    done.append(name)
    (O / 'POSTPROCESS_PROGRESS.json').write_text(json.dumps({'status': 'RUNNING', 'completed': done}, indent=2) + '\n')
    print(name, flush=True)


try:
    while not (O / 'FORMAL_SUMMARY.json').exists():
        if (O / 'STOP_FORMAL_v1.json').exists(): raise RuntimeError('Original formal matrix failed; do not start diagnostic GPU')
        if not live(): raise RuntimeError('Original controller handle missing without terminal success; inspect, not restart')
        time.sleep(5)
    summary = json.loads((O / 'FORMAL_SUMMARY.json').read_text())
    assert summary['status'] == 'COMPLETE_72_FRESH_ONLINE_FORMAL_CELLS' and len(summary['completed']) == len(set(summary['completed'])) == 72
    assert not (O / 'STOP_FORMAL_v1.json').exists()
    while live(): time.sleep(1)
    assert not subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip(), 'GPU resource belongs to another task; do not interfere'
    step('input_plan', [str(P / 'plan_formal_oracles_v1.py'), str(B)])
    step('oracles', [str(P / 'run_formal_oracles_v1.py'), str(B)])
    step('raw_audit', [str(P / 'audit_online_v3.py'), str(B), 'formal_v1', '72'])
    step('processor_replay', [str(P / 'replay_processor_inputs_v4.py'), str(B), 'formal_v1'])
    step('fault_chains', [str(P / 'audit_fault_chains_v1.py'), str(B)])
    step('statistics', [str(P / 'summarize_formal_v1.py'), str(B)])
    (O / 'POSTPROCESS_SUMMARY.json').write_text(json.dumps({'status': 'COMPLETE_FORMAL_ORACLE_AND_CPU_AUDITS', 'completed': done,
        'not_goal_complete': 'Local independent review, cross-campaign evidence matrix, delivery and full completion audit remain',
        'no_more_GPU_issued': True, 'controller_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2) + '\n')
except BaseException as e:
    (O / 'STOP_POSTPROCESS_v1.json').write_text(json.dumps({'error': repr(e), 'completed': done,
        'no_silent_retry_or_source_change': True}, indent=2) + '\n')
    raise
