"""Authorize one fresh, scoped controller only after exact source/resource gates."""
from pathlib import Path
import argparse,hashlib,json,sys,time
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
p=argparse.ArgumentParser();p.add_argument('--kind',choices=['recovery','wait'],required=True)
p.add_argument('--sessions',type=int,choices=[4,8,16],default=8);p.add_argument('--arrival',choices=['sync','staggered'],default='staggered')
p.add_argument('--repeat',type=int,default=0);p.add_argument('--implementation',choices=['revtrace','standard'],default='revtrace')
p.add_argument('--max-wait',type=float,choices=[.15,.4,.75],default=.4);p.add_argument('--cold-prior',action='store_true')
p.add_argument('--source-tag',choices=['v7','v10'],default='v7')
a=p.parse_args();L=Path(r'D:\VLA_QWEN\RevTrace\experiments\input_freeze_20261027');T=Path(__file__).parent
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_freeze_boundary_20261027';O=B+'/results/revtrace/freeze_boundary_20261027'
name=(f'recovery_v7_c4_r{a.repeat}' if a.kind=='recovery' else f'dev_v7_c{a.sessions}_{a.arrival}_r{a.repeat}_{a.implementation}_b{round(a.max_wait*100):03}_'+('cold' if a.cold_prior else 'prior'))
if a.source_tag=='v10':name=name.replace('_v7_','_v10_')
request=dict(vars(a),stage=name)
if a.kind=='wait' and not a.cold_prior:
    bank=T/'WARM_BANK_V3_IMMEDIATE_C16.json';request['bank_sha256']=hashlib.sha256(bank.read_bytes()).hexdigest()
c=ssh_client()
try:
    if a.kind=='wait' and not a.cold_prior:
        sf=c.open_sftp();sf.get_channel().settimeout(30);dest=P+'/packages/WARM_BANK_V3_IMMEDIATE_C16.json'
        try:
            with sf.open(dest,'rb') as f:old=f.read()
        except FileNotFoundError:sf.put(str(bank),dest)
        else:assert hashlib.sha256(old).hexdigest()==request['bank_sha256']
    script='request='+repr(request)+'\n'+r'''from pathlib import Path
import hashlib,importlib.metadata,json,os,platform,subprocess,sys,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_freeze_boundary_20261027';O=B/'results/revtrace/freeze_boundary_20261027';S=P/'source_v7';D=O/request['stage']
H=O/(request['stage']+'_HANDLE.json');M=B/'results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json'
source=json.loads((P/'packages/SOURCE_v7.json').read_text());commit=source['code_commit']
assert commit=='e1511deb6766ce68084128436907b8e2b8e3d417'
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==commit
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain'],text=True).strip()
for f in source['files']:assert hashlib.sha256((S/f['path']).read_bytes()).hexdigest()==f['sha256'],f['path']
assert json.loads((O/'linux_cpu_v7_native/GATE.json').read_text())['status']=='PASS'
assert not D.exists() and not H.exists(),'existing stage must be inspected, not relaunched'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'GPU currently belongs to another live task'
assert hashlib.sha256(M.read_bytes()).hexdigest()=='8904fa5b16cb5d2c1f75d101079c6b7f640c2817b873cb92e816eecb694ea1bc'
if request['kind']=='recovery':
    desc=P/'packages/QWEN_RENDER_DESCRIPTOR_v3.json';ds='541dfa058405dd7600c9800a9b96336f247e50c3b0db375e3e7ca85b152ebdc8'
    assert hashlib.sha256(desc.read_bytes()).hexdigest()==ds
    cmd=[sys.executable,'-B','-u',str(S/'paired_recovery_controller.py'),'--output',str(D),'--source-manifest',str(P/'packages/SOURCE_v7.json'),'--manifest',str(M),'--render-descriptor',str(desc),'--render-descriptor-sha256',ds,'--repeats','1','--start-repeat',str(request['repeat']),'--sessions','4','--arrival','staggered','--fault-target','0:192000']
else:
    cmd=[sys.executable,'-B','-u',str(S/'wait_pilot_controller.py'),'--output',str(D),'--source-manifest',str(P/'packages/SOURCE_v7.json'),'--manifest',str(M),'--sessions',str(request['sessions']),'--arrival',request['arrival'],'--repeat',str(request['repeat']),'--implementation',request['implementation'],'--max-wait',str(request['max_wait']),'--deadline-reserve','raw_slack','--eta-mode','conditional','--rho','1']
    if not request['cold_prior']:cmd+=['--prior-bank',str(P/'packages/WARM_BANK_V3_IMMEDIATE_C16.json'),'--prior-bank-sha256',request['bank_sha256']]
launch=dict(experiment_id='REVTRACE-V7-'+request['kind'].upper()+'-'+request['stage'],request=request,code_commit=commit,source_manifest_sha256=hashlib.sha256((P/'packages/SOURCE_v7.json').read_bytes()).hexdigest(),environment=dict(python=sys.version,packages={n:importlib.metadata.version(n) for n in ['torch','transformers','qwen-asr','tokenizers']},host=platform.node()),raw_result_location=str(D),aggregate_summary_location=str(D/'SUMMARY.json'),gate_decision_location=str(D/'GATE.json'),argv=cmd)
launchpath=O/(request['stage']+'_PRELAUNCH.json');assert not launchpath.exists();launchpath.write_text(json.dumps(launch,indent=2)+'\n')
log=O/(request['stage']+'_controller.log')
env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
with log.open('x') as f:child=subprocess.Popen(cmd,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc')/str(child.pid)
record=dict(experiment_id=launch['experiment_id'],source_commit=commit,pid=child.pid,linux_start_ticks=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest(),launched_unix=time.time(),argv=cmd,result=str(D),controller_log=str(log),prelaunch_record=str(launchpath),scope='fresh bounded development; no superiority assumed')
H.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
'''
    if a.source_tag=='v10':
        for old,new in [('source_v7','source_v10'),('SOURCE_v7','SOURCE_v10'),('linux_cpu_v7_native','linux_cpu_v10_native'),('e1511deb6766ce68084128436907b8e2b8e3d417','ffaa7ab41dd8d6099efd0eb9abe2334951dc5932'),('REVTRACE-V7-','REVTRACE-V10-')]:script=script.replace(old,new)
    i,o,e=c.exec_command(B+'/envs/revbatch-cu128/bin/python -B -',timeout=40);i.write(script);i.channel.shutdown_write()
    raw=o.read().decode();err=e.read().decode();rc=o.channel.recv_exit_status();print(raw);print(err)
    if rc:raise RuntimeError('source/resource/launch gate failed, no automatic retry')
    r=json.loads(raw);dest=L/(name+'_HANDLE.json');assert not dest.exists();dest.write_text(json.dumps(r,indent=2)+'\n')
finally:c.close()
