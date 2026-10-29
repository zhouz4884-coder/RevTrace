"""Read-only bounded analysis status, with exact detached process identity."""
from pathlib import Path
import datetime
import hashlib
import json

B = Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P = B / 'projects/revtrace_physical_retirement_20261028'
O = B / 'results/revtrace/physical_retirement_20261028'
result = {'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
handle_path = P / 'DSN_JOINT_ANALYSIS_HANDLE_v2.json'
if handle_path.exists():
    handle = json.loads(handle_path.read_text())
    process = Path('/proc', str(handle['pid']))
    try:
        ticks = process.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19]
        command = hashlib.sha256(process.joinpath('cmdline').read_bytes()).hexdigest()
        live = str(ticks) == str(handle['start_ticks']) and command == handle['command_sha256']
    except FileNotFoundError:
        live = False
    result.update(handle=handle, exact_process_live=live)
    for name in ['SUMMARY.json', 'GATE.json']:
        path = Path(handle['output']) / name
        if path.exists():
            result[name] = json.loads(path.read_text())
    log = Path(handle['log'])
    if log.exists():
        result['log_tail'] = log.read_text()[-3000:]
else:
    result['status'] = 'NOT_LAUNCHED'
print(json.dumps(result))
