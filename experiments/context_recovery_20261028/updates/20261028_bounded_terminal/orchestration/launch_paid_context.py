from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
L=Path(r'D:\VLA_QWEN\RevTrace\experiments\context_recovery_20261028');B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_freeze_boundary_20261027'
V=sys.argv[1] if len(sys.argv)>1 else 'v3'
assert V in ('v3','v4')
stage='paid_native_context_v1' if V=='v3' else 'paid_native_context_capacity_v2'
c=ssh_client()
try:
    sf=c.open_sftp();sf.get_channel().settimeout(40)
    for local,name in [(L/('source_'+V+'.bundle'),'CONTEXT_SOURCE_'+V+'.bundle'),(L/('source_'+V+'.tar.gz'),'CONTEXT_SOURCE_'+V+'.tar.gz'),(L/('SOURCE_'+V+'.json'),'CONTEXT_SOURCE_'+V+'.json')]:
        dest=P+'/packages/'+name
        try:
            with sf.open(dest,'rb') as f:old=f.read()
        except FileNotFoundError:sf.put(str(local),dest)
        else:assert hashlib.sha256(old).digest()==hashlib.sha256(local.read_bytes()).digest()
    script=r'''from pathlib import Path
import hashlib,importlib.metadata,json,os,platform,subprocess,sys,tarfile,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_freeze_boundary_20261027';O=B/'results/revtrace/freeze_boundary_20261027';A=P/'packages'
S=P/'context_analysis_v3';D=O/'paid_native_context_v1';H=O/'paid_native_context_v1_HANDLE.json';source=json.loads((A/'CONTEXT_SOURCE_v3.json').read_text());commit=source['code_commit']
def git(*x):return subprocess.check_output(['git','-C',str(S),*x],stderr=subprocess.PIPE,text=True).strip()
if not S.exists():
    S.mkdir()
    with tarfile.open(A/'CONTEXT_SOURCE_v3.tar.gz') as tar:
        for f in tar.getmembers():assert not f.issym() and not f.islnk() and (S/f.name).resolve().is_relative_to(S)
        tar.extractall(S,filter='data')
    git('init');git('config','core.autocrlf','false');git('fetch',str(A/'CONTEXT_SOURCE_v3.bundle'),'HEAD:refs/heads/frozen');git('symbolic-ref','HEAD','refs/heads/frozen');git('read-tree',commit)
assert git('rev-parse','HEAD')==commit and not git('status','--porcelain')
for f in source['files']:assert hashlib.sha256((S/f['path']).read_bytes()).hexdigest()==f['sha256']
assert not D.exists() and not H.exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
cpu=O/'context_source_cpu_v3';assert not cpu.exists();cpu.mkdir()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
argv=[sys.executable,'-B','-m','pytest','-c',str(S/'pytest.ini'),'-p','no:cacheprovider','--rootdir',str(S),'--confcutdir',str(S),'--basetemp',str(cpu/'tmp'),'--junitxml',str(cpu/'results.xml'),str(S/'test_analysis.py'),str(S/'test_context_probe.py'),'-q']
environment=dict(python=sys.version,platform=platform.platform(),packages={n:importlib.metadata.version(n) for n in ['pytest','torch','transformers','numpy','soundfile']})
(cpu/'ENVIRONMENT.json').write_text(json.dumps(environment,indent=2)+'\n')
(cpu/'FREEZE.json').write_text(json.dumps(dict(experiment_id='REVTRACE-CONTEXT-SOURCE-LINUX-CPU-V3',source_commit=commit,argv=argv,source_manifest_sha256=hashlib.sha256((A/'CONTEXT_SOURCE_v3.json').read_bytes()).hexdigest(),raw_result_location=str(cpu/'pytest.log'),aggregate_summary_location=str(cpu/'results.xml'),gate_decision_location=str(cpu/'GATE.json')),indent=2)+'\n')
with (cpu/'pytest.log').open('x') as f:r=subprocess.run(argv,env=env,cwd=S,stdout=f,stderr=subprocess.STDOUT)
(cpu/'GATE.json').write_text(json.dumps(dict(gate='PASS' if r.returncode==0 else 'FAIL_PRESERVED',source_commit=commit,returncode=r.returncode,GPU_calls=0),indent=2)+'\n');assert r.returncode==0
cmd=[sys.executable,'-B','-u',str(S/'paid_context_probe.py'),'--out',str(D),'--data-root',str(B/'datasets/revtrace/paid_context_20261028'),'--analysis-manifest',str(A/'CONTEXT_SOURCE_v3.json'),'--runtime-source',str(P/'source_v8'),'--runtime-manifest',str(A/'SOURCE_v8.json'),'--input-identity',str(O/'r7_input_reconstruction_v1/INPUT_IDENTITY.json'),'--legacy-trace',str(B/'results/revtrace/r7_efsc/whisper_base_quality/paired-128-traced.json'),'--model',str(B/'models/whisper-base.en')]
log=O/'paid_native_context_v1_controller.log'
with log.open('x') as f:child=subprocess.Popen(cmd,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc')/str(child.pid);record=dict(experiment_id='REVTRACE-PAID-NATIVE-CONTEXT-V1',source_commit=commit,runtime_commit='27804a4f7b0da57d6e431360677ec791161cb60e',pid=child.pid,linux_start_ticks=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest(),argv=cmd,result=str(D),controller_log=str(log),launched_unix=time.time(),scope='paid existing strong controls; no new algorithm or production installation')
H.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
'''
    if V=='v4':
        for old,new in [('CONTEXT_SOURCE_v3','CONTEXT_SOURCE_v4'),('context_analysis_v3','context_analysis_v4'),('context_source_cpu_v3','context_source_cpu_v4'),('CPU-V3','CPU-V4'),('paid_native_context_v1',stage),('source_v8','source_v10'),('SOURCE_v8','SOURCE_v10'),('27804a4f7b0da57d6e431360677ec791161cb60e','ffaa7ab41dd8d6099efd0eb9abe2334951dc5932')]:script=script.replace(old,new)
        script=script.replace("cmd=[sys.executable,", "assert json.loads((O/'linux_cpu_v10_native/GATE.json').read_text())['gate']=='PASS'\ncmd=[sys.executable,",1)
        script=script.replace("log=O/'"+stage+"_controller.log'","cmd+=['--whisper-context-policy','reserve-generation-tail-v1']\nlog=O/'"+stage+"_controller.log'")
    i,o,e=c.exec_command(B+'/envs/revbatch-cu128/bin/python -B -',timeout=45);i.write(script);i.channel.shutdown_write();out=o.read().decode();err=e.read().decode();rc=o.channel.recv_exit_status();print(out);print(err)
    if rc:raise RuntimeError('context CPU/source/resource gate failed')
    record=json.loads(out);(L/(stage+'_HANDLE.json')).write_text(json.dumps(record,indent=2)+'\n')
finally:c.close()
