from pathlib import Path
import argparse,hashlib,json,sys
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
p=argparse.ArgumentParser();p.add_argument('--stage',choices=['smoke','development'],default='smoke');p.add_argument('--variant',choices=['original','strong'],default='original');a=p.parse_args()
L=Path(r'D:\VLA_QWEN\RevTrace\experiments\context_recovery_20261028');B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
c=ssh_client()
try:
    if a.variant=='strong':
        sf=c.open_sftp();sf.get_channel().settimeout(30);local=L/'NATIVE_STRONG_CONFIG.json';dest=B+'/projects/revtrace_freeze_boundary_20261027/packages/NATIVE_STRONG_CONFIG_v1.json'
        try:
            with sf.open(dest,'rb') as f:old=f.read()
        except FileNotFoundError:sf.put(str(local),dest)
        else:assert hashlib.sha256(old).digest()==hashlib.sha256(local.read_bytes()).digest()
    script='stage='+repr(a.stage)+'\n'+r'''from pathlib import Path
import hashlib,json,os,subprocess,sys,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_freeze_boundary_20261027';O=B/'results/revtrace/freeze_boundary_20261027'
S=P/'source_v8';D=O/'native_v8_pilot_v1';H=O/('native_v8_'+stage+'_HANDLE.json');A=P/'packages'
source=json.loads((A/'SOURCE_v8.json').read_text());assert source['code_commit']=='27804a4f7b0da57d6e431360677ec791161cb60e'
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==source['code_commit']
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain'],text=True).strip()
for f in source['files']:assert hashlib.sha256((S/f['path']).read_bytes()).hexdigest()==f['sha256']
assert not H.exists(),'inspect existing native stage, do not relaunch'
if stage=='smoke':assert not D.exists()
else:assert json.loads((D/'SMOKE_GATE.json').read_text())['status']=='GO_FOR_SEPARATELY_REQUESTED_DEVELOPMENT'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
for name in ['context_holdout_freeze_v1','recovery_v7_native_asset_audit_v1']:
    h=json.loads((O/(name+'_HANDLE.json')).read_text());proc=Path('/proc')/str(h['pid'])
    if proc.exists():
        f=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()
        assert not (f[19]==h['linux_start_ticks'] and f[0]!='Z'),'CPU/data work still active; do not contaminate cost window'
cmd=[sys.executable,'-B','-u',str(S/'native_lifecycle/pilot_controller.py'),'--source-root',str(S),'--source-manifest',str(A/'SOURCE_v8.json'),'--cpu-gate',str(O/'linux_cpu_v8_native/GATE.json'),'--model-manifest',str(A/'NATIVE_QWEN25_ASSETS_v1.json'),'--config',str(S/'native_lifecycle/PILOT_CONFIG.json'),'--output',str(D),'--stage',stage]
pre=O/('native_v8_'+stage+'_PRELAUNCH.json');assert not pre.exists()
pre.write_text(json.dumps(dict(experiment_id='REVTRACE-NATIVE-V8-'+stage.upper(),source_commit=source['code_commit'],source_manifest_sha256=hashlib.sha256((A/'SOURCE_v8.json').read_bytes()).hexdigest(),config_sha256=hashlib.sha256((S/'native_lifecycle/PILOT_CONFIG.json').read_bytes()).hexdigest(),model_manifest_sha256=hashlib.sha256((A/'NATIVE_QWEN25_ASSETS_v1.json').read_bytes()).hexdigest(),CPU_gate=json.loads((O/'linux_cpu_v8_native/GATE.json').read_text()),raw_result_location=str(D),aggregate_summary_location=str(D/(stage.upper()+'_SUMMARY.json')),gate_decision_location=str(D/(stage.upper()+'_GATE.json')),argv=cmd),indent=2)+'\n')
log=O/('native_v8_'+stage+'_controller.log');env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
with log.open('x') as f:child=subprocess.Popen(cmd,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc')/str(child.pid);r=dict(experiment_id='REVTRACE-NATIVE-V8-'+stage.upper(),source_commit=source['code_commit'],pid=child.pid,linux_start_ticks=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest(),result=str(D),controller_log=str(log),argv=cmd,launched_unix=time.time(),scope='actual native multicycle model lifecycle pilot; not online ASR capacity')
H.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
'''
    if a.variant=='strong':
        for old,new in [('source_v8','source_v10'),('SOURCE_v8','SOURCE_v10'),('linux_cpu_v8_native','linux_cpu_v10_native'),('27804a4f7b0da57d6e431360677ec791161cb60e','ffaa7ab41dd8d6099efd0eb9abe2334951dc5932'),('native_v8_pilot_v1','native_strong_v10_v1'),('native_v8_','native_strong_v10_'),('NATIVE-V8-','NATIVE-STRONG-V10-'),('NATIVE_QWEN25_ASSETS_v1','NATIVE_QWEN3_4B_ASSETS_v1')]:script=script.replace(old,new)
        script=script.replace("str(S/'native_lifecycle/PILOT_CONFIG.json')","str(A/'NATIVE_STRONG_CONFIG_v1.json')")
        script=script.replace("(S/'native_lifecycle/PILOT_CONFIG.json').read_bytes()","(A/'NATIVE_STRONG_CONFIG_v1.json').read_bytes()")
    i,o,e=c.exec_command(B+'/envs/revtrace_native_20261027/bin/python -B -',timeout=45);i.write(script);i.channel.shutdown_write();out=o.read().decode();err=e.read().decode();rc=o.channel.recv_exit_status();print(out);print(err)
    if rc:raise RuntimeError('native launch gates failed; inspect without retry')
    record=json.loads(out);prefix='native_v8_' if a.variant=='original' else 'native_strong_v10_';dest=L/(prefix+a.stage+'_HANDLE.json');assert not dest.exists();dest.write_text(json.dumps(record,indent=2)+'\n')
finally:c.close()
