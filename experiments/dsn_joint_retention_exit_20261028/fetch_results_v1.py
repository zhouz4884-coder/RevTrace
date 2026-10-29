"""Bounded, byte-verified delivery after the frozen 24-cell offline recount.

Raw worker/event/consumer logs remain on the designated experiment disk.  This
copies the complete independent recount, its frozen run metadata, per-cell
audit/frontier tables, and exact acquisition hashes.  It runs no inference.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import sys

sys.path.insert(0, r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client

HERE = Path(__file__).resolve().parent
B = '/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
O = B + '/results/revtrace/physical_retirement_20261028'
P = B + '/projects/revtrace_physical_retirement_20261028'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=HERE / 'RESULTS_v1')
    args = parser.parse_args()
    plan = json.loads((HERE / 'PLAN_v1.json').read_text(encoding='utf8'))
    targets = {}
    analysis = O + '/dsn_joint_analysis_v1'
    for name in ['RUNS', 'FACTORIAL_EFFECTS', 'MATCHED_ROWS', 'ANALYSIS_RECORD', 'SUMMARY', 'GATE']:
        targets[f'analysis/{name}.json'] = f'{analysis}/{name}.json'
    controller = O + '/dsn_joint_controller_v1'
    for name in ['SUMMARY', 'GATE', 'RUN_RECORD', 'ENVIRONMENT']:
        targets[f'controller/{name}.json'] = f'{controller}/{name}.json'
    targets['controller/GPU_HANDLE.json'] = P + '/DSN_JOINT_GPU_HANDLE_v1.json'
    targets['analysis/HANDLE.json'] = P + '/DSN_JOINT_ANALYSIS_HANDLE_v1.json'
    for name in ['INPUT_AUDIT_PRESENCE', 'MATCHED_AUDIT_PRESENCE', 'OWNER_TO_ACTUAL_CONSUMER',
                 'LEGAL_PRESSURE_CONSUMER', 'EXIT_FOLLOWING_CONSUMER', 'SUMMARY', 'GATE', 'RUN_RECORD']:
        targets[f'detail/{name}.json'] = O + f'/dsn_joint_detail_v1/{name}.json'
    targets['detail/HANDLE.json'] = P + '/DSN_JOINT_DETAIL_HANDLE_v1.json'
    targets['detail/PREFLIGHT.json'] = P + '/DSN_JOINT_DETAIL_PREFLIGHT_v1.json'
    for cell in plan['cells']:
        for name in ['GATE.json', 'RUN_RECORD.json', 'FREEZE.json',
                     'audit/SUMMARY.json', 'audit/FRONTIERS.json', 'audit/SESSIONS.json',
                     'audit/BATCHES.json', 'attempt0/config.json', 'attempt0/power_samples.json']:
            targets[f"cells/{cell['cell_id']}/{name}"] = cell['output'] + '/' + name
    client = ssh_client()
    try:
        code = '''import datetime,hashlib,json,subprocess
from pathlib import Path
assert json.loads(Path(ANALYSIS_GATE).read_text())['gate']=='PASS_OFFLINE_RECOUNT'
assert json.loads(Path(CONTROLLER_GATE).read_text())['gate']=='PASS_ALL_FROZEN_EXECUTION_CELLS'
assert json.loads(Path(DETAIL_GATE).read_text())['gate']=='PASS_SUPPLEMENTAL_OFFLINE_AUDIT'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
targets=TARGETS
print(json.dumps(dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=[dict(relative=k,path=v,bytes=Path(v).stat().st_size,sha256=hashlib.sha256(Path(v).read_bytes()).hexdigest()) for k,v in targets.items()])))
'''.replace('ANALYSIS_GATE', repr(analysis + '/GATE.json')).replace('CONTROLLER_GATE', repr(controller + '/GATE.json')).replace('DETAIL_GATE', repr(O + '/dsn_joint_detail_v1/GATE.json')).replace('TARGETS', repr(targets))
        stdin, stdout, stderr = client.exec_command('python3 -B -', timeout=45)
        stdin.write(code)
        stdin.flush()
        stdin.channel.shutdown_write()
        payload, error = stdout.read(), stderr.read()
        if stdout.channel.recv_exit_status() != 0:
            raise RuntimeError(error.decode('utf8', errors='replace'))
        manifest = json.loads(payload)
        assert max(r['bytes'] for r in manifest['files']) < 30_000_000
        assert sum(r['bytes'] for r in manifest['files']) < 90_000_000
        args.output.mkdir(parents=True, exist_ok=False)
        sftp = client.open_sftp()
        try:
            for row in manifest['files']:
                target = args.output / row['relative']
                target.parent.mkdir(parents=True, exist_ok=True)
                sftp.get(row['path'], str(target))
                assert target.stat().st_size == row['bytes']
                assert hashlib.sha256(target.read_bytes()).hexdigest() == row['sha256']
        finally:
            sftp.close()
        receipt = dict(
            experiment_id=plan['experiment_id'] + '-BOUNDED-DELIVERY',
            fetched_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            acquisition_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            all_remote_sha256_matched=True, **manifest)
        with (args.output / 'DOWNLOAD_VERIFICATION.json').open('x', encoding='utf8') as stream:
            json.dump(receipt, stream, indent=2)
            stream.write('\n')
        print(json.dumps(dict(output=str(args.output), files=len(manifest['files']),
                              bytes=sum(r['bytes'] for r in manifest['files']),
                              all_sha256_matched=True)))
    finally:
        client.close()


if __name__ == '__main__':
    main()
