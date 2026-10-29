"""Bounded read-only monitor for this active acquisition, every 120 seconds."""
import datetime
import json
import pathlib
import subprocess
import sys
import time

monitor = pathlib.Path(__file__).with_name('independent_acquisition_monitor_v1.py')
started = time.monotonic()
failures = 0
while time.monotonic() - started < 7200:
    run = subprocess.run([sys.executable, str(monitor), '--summary'], capture_output=True, text=True)
    if run.returncode:
        failures += 1
        print(json.dumps(dict(observation_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            status='OBSERVATION_ERROR_NOT_WORKER_DEATH', consecutive_observation_errors=failures)), flush=True)
        if failures >= 3:
            raise SystemExit(2)
    else:
        failures = 0
        state = json.loads(run.stdout)
        print(json.dumps(dict(observed_utc=state['observed_utc'], evidence=state['evidence'],
            process=state.get('process'), exact_worker_pids=state['exact_worker_pids'],
            completed_final_files=state['completed_final_files'], partial_assets=state['partial_assets'],
            gate=state['gate'], gate_newer_than_active=state['gate_newer_than_active'],
            manifest_present=state['manifest_present'], last_safe_log_line=state['last_safe_log_line'])), flush=True)
        if state['manifest_present'] and state['gate_newer_than_active']:
            raise SystemExit(0)
        if state['gate_newer_than_active'] and state['gate'].get('status') == 'INCOMPLETE_ACQUISITION_PRESERVED':
            raise SystemExit(1)
    time.sleep(120)
print(json.dumps(dict(status='BOUNDED_MONITOR_LIMIT_REACHED_NOT_WORKER_DEATH')), flush=True)
