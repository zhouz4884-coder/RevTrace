"""Small bounded source deployment and read-only CPU execution on 8 TB disk."""
import hashlib,importlib.util,json,shlex,sys
from pathlib import Path
F=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('revtrace_authorized_ssh',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_dsn_timely_continuity_20261029'
PY=B+'/envs/revbatch-cu128/bin/python'
client=m.ssh_client()
def run(cmd):
    _,out,err=client.exec_command(cmd,timeout=90)
    text=out.read().decode(); error=err.read().decode(); code=out.channel.recv_exit_status()
    if text:print(text,end='')
    if error:print(error,end='',file=sys.stderr)
    if code:raise RuntimeError('remote command failed: '+str(code))
try:
    run('nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader')
    _,out,err=client.exec_command('nvidia-smi --query-compute-apps=pid --format=csv,noheader',timeout=15)
    if out.read().decode().strip():raise RuntimeError('GPU busy: postpone CPU until timed cells end')
    run('mkdir -p '+shlex.quote(P))
    sftp=client.open_sftp()
    for name in ['SOURCE_v1.bundle','SOURCE_v1.json','CONFIG_v1.json']:
        sftp.put(str(F/name),P+'/'+name)
    sftp.close()
    program='''import hashlib,json,pathlib,subprocess,sys,platform
P=pathlib.Path(P_VALUE);S=P/'source_v1'; M=json.loads((P/'SOURCE_v1.json').read_bytes())
if not S.exists(): subprocess.run(['git','clone',str(P/'SOURCE_v1.bundle'),str(S)],check=True)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==M['code_commit']
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=S,text=True).strip()
for r in M['files']:
 b=(S/r['path']).read_bytes(); assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
config=json.loads((P/'CONFIG_v1.json').read_bytes()); O=pathlib.Path(config['output'])
assert not O.exists()
control=subprocess.run([sys.executable,'-B','-m','unittest','-v','test_continuity'],cwd=S,capture_output=True,text=True)
C=P/'CPU_CONTROLS_v1.json'
assert not C.exists()
C.write_text(json.dumps(dict(experiment_id=config['experiment_id']+'-CPU-CONTROLS',code_commit=M['code_commit'],frozen_config_sha256=hashlib.sha256((P/'CONFIG_v1.json').read_bytes()).hexdigest(),environment=dict(python=sys.version,platform=platform.platform()),raw_result_location=str(C),aggregate_summary_location=str(C),gate_decision_location=str(C),stdout=control.stdout,stderr=control.stderr,returncode=control.returncode,gate='PASS_6_SYNTHETIC_CPU_CONTROLS' if control.returncode==0 else 'FAIL_CPU_CONTROLS'),indent=2)+'\\n')
assert control.returncode==0,control.stderr
subprocess.run([sys.executable,'-B',str(S/'continuity.py'),'--config',str(P/'CONFIG_v1.json'),'--manifest',str(P/'SOURCE_v1.json')],cwd=S,check=True)
print(json.dumps(dict(cpu_controls=str(C),results=str(O))))
'''.replace('P_VALUE',repr(P))
    stdin,out,err=client.exec_command(shlex.quote(PY)+' -B -',timeout=90)
    stdin.write(program);stdin.channel.shutdown_write()
    output=out.read().decode();error=err.read().decode();code=out.channel.recv_exit_status()
    if output:print(output,end='')
    if error:print(error,end='',file=sys.stderr)
    results=F/'RESULTS_v1';results.mkdir(exist_ok=False)
    config=json.loads((F/'CONFIG_v1.json').read_text(encoding='utf8'))
    sftp=client.open_sftp();receipt=[]
    names=sftp.listdir(config['output']) if code==0 else ['GATE.json','CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json']
    for name in names:
        remote=config['output']+'/'+name
        try:
            with sftp.open(remote,'rb') as f:b=f.read()
        except IOError:continue
        (results/name).write_bytes(b);receipt.append(dict(file=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
    with sftp.open(P+'/CPU_CONTROLS_v1.json','rb') as f:(F/'CPU_CONTROLS_v1.json').write_bytes(f.read())
    sftp.close()
    (results/'DOWNLOAD_VERIFICATION.json').write_text(json.dumps(dict(files=receipt,method='direct SFTP byte reads, local SHA256 of received immutable output bytes',remote_directory=config['output']),indent=2)+'\n',encoding='utf8')
    if code:raise RuntimeError('secondary recount failed; failure evidence preserved: '+str(code))
finally:client.close()
