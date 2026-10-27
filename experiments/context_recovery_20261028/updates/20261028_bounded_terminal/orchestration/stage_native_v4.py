"""Stage the exact v4 snapshot and run real LangGraph CPU tests, no GPU inference."""
from pathlib import Path
import hashlib,json,sys,time
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
L=Path(r'D:\VLA_QWEN\RevTrace\experiments\input_freeze_20261027')
V=sys.argv[1] if len(sys.argv)>1 else 'v4'
if V not in ['v4','v7','v8','v9','v10']:raise ValueError('unfrozen version')
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_freeze_boundary_20261027';O=B+'/results/revtrace/freeze_boundary_20261027'
c=ssh_client();record={'operation':V+'_native_CPU_gate','started_unix':time.time()}
try:
    sf=c.open_sftp();sf.get_channel().settimeout(40)
    for n in ['source_'+V+'.tar.gz','source_'+V+'.bundle','SOURCE_'+V+'.json']:
        dest=P+'/packages/'+n
        try:
            with sf.open(dest,'rb') as f:old=f.read()
        except FileNotFoundError:sf.put(str(L/n),dest)
        else:assert hashlib.sha256(old).digest()==hashlib.sha256((L/n).read_bytes()).digest()
    script=r'''from pathlib import Path
import hashlib,importlib.metadata,json,os,platform,subprocess,sys,tarfile,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_freeze_boundary_20261027';O=B/'results/revtrace/freeze_boundary_20261027'
A=P/'packages';S=P/'source_v4';D=O/'linux_cpu_v4_native'
m=json.loads((A/'SOURCE_v4.json').read_text());commit=m['code_commit']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],stderr=subprocess.PIPE,text=True).strip()
def put(p,x):
    if p.exists():raise FileExistsError(p)
    p.write_text(json.dumps(x,indent=2)+'\n')
if not S.exists():
    S.mkdir()
    with tarfile.open(A/'source_v4.tar.gz') as t:
        for f in t.getmembers():
            assert not f.issym() and not f.islnk() and (S/f.name).resolve().is_relative_to(S)
        t.extractall(S,filter='data')
    git('init');git('config','core.autocrlf','false');git('fetch',str(A/'source_v4.bundle'),'HEAD:refs/heads/frozen')
    git('symbolic-ref','HEAD','refs/heads/frozen');git('read-tree',commit)
assert git('rev-parse','HEAD')==commit and not git('status','--porcelain')
for f in m['files']:assert sha(S/f['path'])==f['sha256']
assert not D.exists();D.mkdir()
names=['test_dispatch_wait','test_dispatch_wait_integration','test_recovery_profile','test_live_qwen','test_durable_journal','test_certified_display','test_certified_envelope','test_composed_kernel','test_properties_abc','test_standard_async','test_row_lifecycle_transport','test_complete_row_stream','test_consumer_bound_identity','test_envelope_failure_controls','test_startup_overlap','test_dispatch_wait_real_busy']
paths=[str(S/'runtime/tests'/(n+'.py')) for n in names]+[str(S/n) for n in ['test_content_fault.py','test_audit_contracts.py','test_historical_display.py','test_kernel_cow.py','test_prefix_plan.py']]+[str(S/'native_lifecycle/test_native.py')]
paths += [str(S/'runtime/tests'/(n+'.py')) for n in ['test_conditional_wait_eta','test_wait_prior_bank'] if (S/'runtime/tests'/(n+'.py')).exists()]
paths += [str(S/'runtime/tests'/(n+'.py')) for n in ['test_whisper_capacity'] if (S/'runtime/tests'/(n+'.py')).exists()]
paths += [str(S/n) for n in ['test_paired_recovery.py','test_paid_wait_operator.py','native_lifecycle/test_pilot.py'] if (S/n).exists()]
env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['REVTRACE_RUNTIME_SOURCE']=str(S/'runtime/src')
env['PYTHONPATH']=os.pathsep.join([str(S/'runtime/src'),str(S/'runtime/scripts'),str(S),str(S/'native_lifecycle')])
argv=[sys.executable,'-B','-m','pytest','-c',str(S/'pytest.ini'),'-p','no:cacheprovider','--rootdir',str(S),'--confcutdir',str(S),'--basetemp',str(D/'tmp'),'--junitxml',str(D/'results.xml'),'-q',*paths]
environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),packages={n:importlib.metadata.version(n) for n in ['pytest','numpy','torch','transformers','langgraph','langgraph-checkpoint-sqlite','langgraph-checkpoint','langchain-core']})
put(D/'ENVIRONMENT.json',environment)
put(D/'FREEZE.json',dict(experiment_id='REVTRACE-NATIVE-CPU-V4',source_commit=commit,source_manifest_sha256=sha(A/'SOURCE_v4.json'),environment_sha256=sha(D/'ENVIRONMENT.json'),config=argv,raw_result_location=str(D/'pytest.log'),aggregate_summary_location=str(D/'results.xml'),gate_decision_location=str(D/'GATE.json'),evidence_tier='REAL_LANGGRAPH_CPU_NO_GPU_INFERENCE'))
with (D/'pytest.log').open('x') as f:r=subprocess.run(argv,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT)
import xml.etree.ElementTree as ET
tree=ET.parse(D/'results.xml');cases=list(tree.iter('testcase'));skipped=sum(x.find('skipped') is not None for x in cases)
status='PASS' if r.returncode==0 and skipped==0 else 'FAIL_PRESERVED'
gate=dict(gate=status,status=status,returncode=r.returncode,total_tests=len(cases),skipped=skipped,source_commit=commit,GPU_calls=0,raw_test_report=str(D/'results.xml'),raw_test_sha256=sha(D/'results.xml'))
put(D/'GATE.json',gate);print(json.dumps(gate),flush=True);print((D/'pytest.log').read_text()[-6000:],flush=True)
raise SystemExit(0 if gate['gate']=='PASS' else 1)
'''
    for old,new in [('source_v4','source_'+V),('SOURCE_v4','SOURCE_'+V),('linux_cpu_v4_native','linux_cpu_'+V+'_native'),('CPU-V4','CPU-'+V.upper())]:script=script.replace(old,new)
    i,o,e=c.exec_command(B+'/envs/revtrace_native_20261027/bin/python -B -',timeout=300)
    i.write(script);i.channel.shutdown_write();out=o.read().decode(errors='replace');err=e.read().decode(errors='replace');rc=o.channel.recv_exit_status()
    record.update(returncode=rc,stdout=out,stderr=err);print(out);print(err)
    for n in ['GATE.json','ENVIRONMENT.json','FREEZE.json','results.xml','pytest.log']:
        dest=L/('LINUX_'+V+'_NATIVE_'+n);assert not dest.exists();sf.get(O+'/linux_cpu_'+V+'_native/'+n,str(dest))
    if rc:raise RuntimeError('Native Linux CPU gate failed, preserved')
finally:
    c.close();(L/('NATIVE_CPU_'+V+'_STAGE_'+str(time.time_ns())+'.json')).write_text(json.dumps(record,indent=2)+'\n')
