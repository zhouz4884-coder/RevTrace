"""Read-only bounded controller/process snapshot; no worker restarts."""
import datetime, hashlib, json, subprocess
from pathlib import Path

B = Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P = B / 'projects/revtrace_physical_retirement_20261028'
O = B / 'results/revtrace/physical_retirement_20261028'
out = {'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
handle_path = P / 'DSN_JOINT_GPU_HANDLE_v1.json'
if handle_path.exists():
    handle = json.loads(handle_path.read_text())
    proc = Path('/proc', str(handle['pid']))
    try:
        ticks = proc.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19]
        cmdsha = hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest()
        live = str(ticks) == str(handle['start_ticks']) and cmdsha == handle['command_sha256']
    except FileNotFoundError:
        live = False
    out.update(handle=handle, exact_process_live=live)
else:
    out['status'] = 'NOT_LAUNCHED'
for name in ['SUMMARY.json', 'GATE.json']:
    path = O / 'dsn_joint_controller_v1' / name
    if path.exists():
        out[name] = json.loads(path.read_text())
plan_path = P / 'DSN_JOINT_PLAN_v1_FROZEN.json'
if plan_path.exists():
    plan = json.loads(plan_path.read_text())
    done = []
    for cell in plan['cells']:
        path = Path(cell['output']) / 'GATE.json'
        if path.exists():
            done.append({'cell_id': cell['cell_id'], 'gate': json.loads(path.read_text())['gate']})
    out.update(planned=len(plan['cells']), recorded_cells=done)
out['gpu_processes'] = subprocess.check_output(
    ['nvidia-smi', '--query-compute-apps=pid,used_memory', '--format=csv,noheader'], text=True).strip()
print(json.dumps(out))
