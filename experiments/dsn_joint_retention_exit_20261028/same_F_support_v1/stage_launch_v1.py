"""Dry-run by default; execute only in root's native-postanalysis CPU window.

No SSH is opened without --execute and exact completed native scope/postanalysis
gate paths plus their caller-observed final statuses.  Negative completed gates
are permitted when explicitly supplied; no scientific result is manufactured.
"""
from pathlib import Path
import argparse,hashlib,json,shlex,sys

HERE=Path(__file__).resolve().parent
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_physical_retirement_20261028/dsn_joint_same_F_support_v1'
O=B+'/results/revtrace/physical_retirement_20261028/dsn_joint_same_F_support_v1'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true')
    parser.add_argument('--native-scope-gate');parser.add_argument('--native-scope-status')
    parser.add_argument('--native-postanalysis-gate');parser.add_argument('--native-postanalysis-status');args=parser.parse_args()
    plan=HERE/'PLAN_v1.json';manifest=HERE/'SOURCE_v1.json';m=json.loads(manifest.read_text())
    inputs=['PLAN_v1.json','NEURAL_PLAN_v1.json','TARGET_BATCHES_v1.json','PRIOR_INPUT_RECORD_v1.json']
    files=inputs+['SOURCE_v1.json','SOURCE_v1.bundle']
    hashes={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in files}
    frozen=json.loads((HERE/'FREEZE_RECEIPT_v1.json').read_text());expected={r['path']:r['sha256'] for r in frozen['files']}
    assert all(hashes[n]==expected[n] for n in files),'local frozen input/source changed'
    payload=dict(experiment_id='REVTRACE-DSN-RXK-SAMEF-SUPPORT-20261029-v1',project=P,output=O,
                 input_hashes=hashes,orchestration_source_commit=m['code_commit'],primary_analysis_commit='fde6272b494db43a66eebea7444d7c9d1037e687',
                 native_scope_gate=args.native_scope_gate,native_scope_status=args.native_scope_status,
                 native_postanalysis_gate=args.native_postanalysis_gate,native_postanalysis_status=args.native_postanalysis_status)
    if not args.execute:
        print(json.dumps(dict(status='LOCAL_DRY_RUN_ONLY_NO_SSH',launch=payload,new_GPU_calls=0,
            requirement='Root allocates after full native scope plus postanalysis and before midpoint GPU. Supply both actual completed gate paths and exact final statuses with --execute.')))
        return
    for name in ['native_scope_gate','native_scope_status','native_postanalysis_gate','native_postanalysis_status']:
        assert payload[name],name+' required after root CPU window allocation'
    for key in ['native_scope_gate','native_postanalysis_gate']:
        path=payload[key];assert path.startswith(B+'/results/revtrace/dsn_streamcorrect_20261028/') and '..' not in path.split('/')
    sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
    from contractkv_ssh_credential import ssh_client
    client=ssh_client()
    try:
        check=r'''
import json,subprocess
from pathlib import Path
v=PAYLOAD
for p,s in [(v['native_scope_gate'],v['native_scope_status']),(v['native_postanalysis_gate'],v['native_postanalysis_status'])]:
 g=json.loads(Path(p).read_text());assert g.get('gate',g.get('status'))==s,'native completion/postanalysis gate is not the exact allocated final state'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'GPU not drained; no CPU IO staging during timed scope'
for name,status in [('dsn_joint_controller_v1','PASS_ALL_FROZEN_EXECUTION_CELLS'),('dsn_joint_analysis_v2','PASS_OFFLINE_RECOUNT'),('dsn_joint_detail_v2','PASS_SUPPLEMENTAL_OFFLINE_AUDIT')]:
 p=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/physical_retirement_20261028')/name/'GATE.json';assert json.loads(p.read_text())['gate']==status
print('PASS_ALLOCATED_CPU_WINDOW_AND_PRIOR_GATES')
'''.replace('PAYLOAD',repr(payload))
        def remote(program):
            i,o,e=client.exec_command(shlex.quote(B+'/envs/revbatch-cu128/bin/python')+' -B -',timeout=45)
            i.write(program);i.flush();i.channel.shutdown_write();raw=o.read();error=e.read();assert o.channel.recv_exit_status()==0,error.decode('utf8',errors='replace');return raw.decode('utf8')
        print(remote(check))
        sftp=client.open_sftp()
        try:
            for path in [P,P+'/inputs']:
                try:sftp.stat(path)
                except FileNotFoundError:sftp.mkdir(path)
            for name in files:
                target=P+('/inputs/' if name in inputs else '/')+name
                try:
                    with sftp.open(target,'rb') as stream:previous=stream.read()
                    assert previous==(HERE/name).read_bytes(),'never replace staged frozen input/source'
                except FileNotFoundError:sftp.put(str(HERE/name),target)
        finally:sftp.close()
        launch=r'''
from pathlib import Path
import datetime,hashlib,json,os,subprocess
v=PAYLOAD
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=Path(v['project']);O=Path(v['output'])
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
for p,s in [(v['native_scope_gate'],v['native_scope_status']),(v['native_postanalysis_gate'],v['native_postanalysis_status'])]:
 g=json.loads(Path(p).read_text());assert g.get('gate',g.get('status'))==s
for name,expected in v['input_hashes'].items():
 p=P/('inputs/'+name if name not in ['SOURCE_v1.json','SOURCE_v1.bundle'] else name);assert hashlib.sha256(p.read_bytes()).hexdigest()==expected
source=P/'source_v1';manifest=P/'SOURCE_v1.json'
if not source.exists():subprocess.run(['git','-c','core.autocrlf=false','clone','--quiet',str(P/'SOURCE_v1.bundle'),str(source)],check=True)
subprocess.run(['git','-C',str(source),'config','core.autocrlf','false'],check=True)
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==v['orchestration_source_commit']
handle=P/'HANDLE_v1.json';log=O.with_suffix('.log');assert not O.exists() and not handle.exists() and not log.exists()
allocation=P/'CPU_WINDOW_RECORD_v1.json'
with allocation.open('x') as stream:json.dump(dict(**v,allocated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),GPU_processes=''),stream,indent=2);stream.write('\n')
argv=[str(B/'envs/revbatch-cu128/bin/python'),'-B','-u',str(source/'quality_recount.py'),'--inputs',str(P/'inputs'),'--plan-sha256',v['input_hashes']['PLAN_v1.json'],'--source-manifest',str(manifest),'--out',str(O)]
with log.open('x') as stream:child=subprocess.Popen(argv,cwd=source,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES=''),stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc',str(child.pid));h=dict(experiment_id=v['experiment_id'],pid=child.pid,start_ticks=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest(),argv=argv,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),output=str(O),log=str(log),source_commit=v['orchestration_source_commit'],primary_analysis_commit=v['primary_analysis_commit'],new_GPU_calls=0)
with handle.open('x') as stream:json.dump(h,stream,indent=2);stream.write('\n')
print(json.dumps(h))
'''.replace('PAYLOAD',repr(payload))
        result=remote(launch);print(result)
        with (HERE/'HANDLE_v1.json').open('x',encoding='utf8') as stream:json.dump(json.loads(result),stream,indent=2);stream.write('\n')
    finally:client.close()

if __name__=='__main__':main()
