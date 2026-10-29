"""Fetch bounded final evidence only after the CPU/global execution gates pass."""
from pathlib import Path
import argparse,hashlib,json,sys
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
HERE=Path(__file__).resolve().parent
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
BASE=B+'/results/revtrace/physical_retirement_20261028'

def main():
    p=argparse.ArgumentParser();p.add_argument('--remote-root',default=BASE+'/dsn_service_stability_analysis_v1')
    p.add_argument('--output',type=Path,default=HERE/'RESULTS_v1');a=p.parse_args()
    assert a.remote_root.startswith(BASE+'/') and '..' not in a.remote_root.split('/')
    files=['SUMMARY.json','GATE.json','CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json']
    tables={
        'aggregate':['SUMMARY','ANALYSIS_RECORD','COVERAGE','BLOCK_COVERAGE','RUNS','SOURCE_METRICS',
            'FACTORIAL_EFFECTS','SOURCE_FACTORIAL_EFFECTS','PAIRED_EFFECTS','SOURCE_PAIRED_EFFECTS',
            'FRONTIER_PAIRED_EFFECTS','CANONICAL_HISTORY_GROUPS','SOURCE_REGISTRY'],
        'usefulness':['SUMMARY','ANALYSIS_RECORD','COVERAGE','RUNS','FACTORIAL_EFFECTS','SOURCE_FACTORIAL_EFFECTS'],
        'opportunities':['ANALYSIS_RECORD','COVERAGE','STRATIFIED_RATES','SOURCE_OPPORTUNITIES',
            'UPDATES','SAME_CANONICAL_HISTORY_GROUPS'],
        'critical_path':['SUMMARY','RUNS','FRONTIER_PATHS','ANALYSIS_RECORD']}
    files.extend(f'{component}/{name}.json' for component,names in tables.items() for name in names)
    targets=[a.remote_root+'/'+name for name in files]
    targets.extend(BASE+'/dsn_service_stability_controller_v1/'+name for name in ['GATE.json','SUMMARY.json','RUN_RECORD.json','ENVIRONMENT.json'])
    c=ssh_client()
    try:
        script='''import hashlib,json
from pathlib import Path
root=Path(ROOT)
assert json.loads((root/'GATE.json').read_text())['gate']=='PASS_CPU_RECOUNTS'
assert json.loads(Path(CONTROLLER).read_text())['gate']=='PASS_ALL_FROZEN_EXECUTION_CELLS'
paths=PATHS
print(json.dumps([dict(path=p,bytes=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest()) for p in paths]))
'''.replace('ROOT',repr(a.remote_root)).replace('CONTROLLER',repr(BASE+'/dsn_service_stability_controller_v1/GATE.json')).replace('PATHS',repr(targets))
        i,o,e=c.exec_command('python3 -B -',timeout=45);i.write(script);i.flush();i.channel.shutdown_write()
        raw=o.read();err=e.read();assert o.channel.recv_exit_status()==0,err.decode();manifest=json.loads(raw)
        assert max(r['bytes'] for r in manifest)<30_000_000 and sum(r['bytes'] for r in manifest)<65_000_000
        a.output.mkdir(parents=True,exist_ok=False);s=c.open_sftp()
        try:
            for r in manifest:
                rel=r['path'][len(a.remote_root)+1:] if r['path'].startswith(a.remote_root+'/') else 'controller/'+r['path'].rsplit('/',1)[-1]
                out=a.output/rel;out.parent.mkdir(parents=True,exist_ok=True);s.get(r['path'],str(out))
                assert out.stat().st_size==r['bytes'] and hashlib.sha256(out.read_bytes()).hexdigest()==r['sha256']
        finally:s.close()
        with (a.output/'DOWNLOAD_VERIFICATION.json').open('x',encoding='utf8') as f:json.dump(manifest,f,indent=2);f.write('\n')
        print(json.dumps(dict(output=str(a.output),files=len(manifest),bytes=sum(r['bytes'] for r in manifest),all_sha256_matched=True)))
    finally:c.close()

if __name__=='__main__':main()
