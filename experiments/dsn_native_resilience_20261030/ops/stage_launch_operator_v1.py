"""Stage the frozen operator and launch only the unexecuted fixed pilot suffix."""
import argparse,hashlib,json,pathlib,shlex,sys,subprocess
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1]
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_resilience_20261030';O=B+'/results/revtrace/dsn_native_resilience_20261030';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['stage','launch'],required=True);a=ap.parse_args()
mp=F/'packages/OPERATOR_SOURCE_v1.json';bundle=F/'packages/OPERATOR_SOURCE_v1.bundle';pre=F/'RUNTIME_PREREQUISITE_v1_r2.json';plan=F/'SHORT_PILOT_v1_FROZEN.json'
current=json.loads((R/'experiments/repository_identity_20261027/CURRENT.json').read_bytes());assert current['source_commit']=='e7122b97f7864792770a47a798293794a098ab67'
subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],check=True,capture_output=True)
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 if a.mode=='stage':
  s=c.open_sftp()
  for f,name in [(mp,'OPERATOR_SOURCE_v1.json'),(bundle,'OPERATOR_SOURCE_v1.bundle')]:
   target=P+'/'+name
   try:
    with s.open(target,'rb') as stream:assert stream.read()==f.read_bytes()
   except FileNotFoundError:
    with s.open(target,'wx') as stream:stream.write(f.read_bytes())
  s.close()
  code=r"""import pathlib,json,subprocess,sys,hashlib,os,datetime
P=pathlib.Path(PROJECT);O=pathlib.Path(OUTPUT);S=P/'operator_source_v1';m=P/'OPERATOR_SOURCE_v1.json'
assert hashlib.sha256(m.read_bytes()).hexdigest()==MSHA
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
if not S.exists():
 subprocess.run(['git','clone','-q','--no-checkout',str(P/'OPERATOR_SOURCE_v1.bundle'),str(S)],check=True)
 subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True)
 subprocess.run(['git','-C',str(S),'checkout','-q','e7122b97f7864792770a47a798293794a098ab67'],check=True)
sys.path.insert(0,str(S));from run_campaign import verify_checkout
identity=verify_checkout(S,m,'e7122b97f7864792770a47a798293794a098ab67',5)
out=O/'operator_cpu_v1';out.mkdir();tmp=out/'tmp';tmp.mkdir();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(tmp))
config=dict(experiment_id='SC_RESILIENCE_OPERATOR_CPU_V1',source_commit=identity['source_commit'],manifest_sha256=MSHA,neural_calls=0,scope='CPU fixture controls only')
put=lambda n,x:(out/n).write_text(json.dumps(x,indent=2)+'\n')
put('CONFIG.json',config);put('ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,scope='stdlib CPU controls; no torch/models'));put('RUN_RECORD.json',dict(experiment_id=config['experiment_id'],code_commit=config['source_commit'],frozen_config=str(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),raw_result_location=str(out/'unittest.log'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
result=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(S),'-p','test_*.py','-v'],cwd=S,capture_output=True,env=env);(out/'unittest.log').write_bytes(result.stdout+result.stderr)
text=(result.stdout+result.stderr).decode();assert result.returncode==0 and 'Ran 16 tests' in text and 'skipped' not in text
verify_checkout(S,m,'e7122b97f7864792770a47a798293794a098ab67',5)
g=dict(status='PASS_FROZEN_OPERATOR_16_CPU_ZERO_SKIP',operator_source_commit=identity['source_commit'],operator_manifest_sha256=MSHA,tests=16,skipped=0,neural_launched=False);put('SUMMARY.json',g);put('GATE.json',g);print(json.dumps(g))
"""
 else:
  assert (F/'operator_cpu_remote_v1/GATE.json').exists()
  code=r"""import pathlib,json,subprocess,sys,hashlib,os,datetime
P=pathlib.Path(PROJECT);O=pathlib.Path(OUTPUT);S=P/'operator_source_v1'
gate=json.loads((O/'operator_cpu_v1/GATE.json').read_bytes());assert gate['status']=='PASS_FROZEN_OPERATOR_16_CPU_ZERO_SKIP'
plan=P/'SHORT_PILOT_v1_FROZEN.json';pre=O/'RUNTIME_PREREQUISITE_v1_r2.json'
assert hashlib.sha256(plan.read_bytes()).hexdigest()==PLANSHA and hashlib.sha256(pre.read_bytes()).hexdigest()==PRESHA
sys.path.insert(0,str(S));from run_campaign import verify_checkout,gpu_empty
verify_checkout(S,P/'OPERATOR_SOURCE_v1.json','e7122b97f7864792770a47a798293794a098ab67',5);gpu_empty()
cmd=[sys.executable,'-B',str(S/'run_campaign.py'),'--plan',str(plan),'--manifest',str(P/'OPERATOR_SOURCE_v1.json'),'--prerequisite',str(pre),'--prerequisite-sha256',PRESHA,'--out',str(O/'short_pilot_v1')]
log=O/'operator_short_pilot_v1.log';handle=O/'OPERATOR_PILOT_HANDLE_v1.json';assert not log.exists() and not handle.exists()
with log.open('x') as stream:child=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
proc=pathlib.Path('/proc')/str(child.pid);r=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=cmd,operator_source_commit='e7122b97f7864792770a47a798293794a098ab67',neural_source_commit='9492d3f9cb35e2b2849ec020817750a221248f0e',plan_sha256=PLANSHA,prerequisite_sha256=PRESHA,log=str(log),out=str(O/'short_pilot_v1'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());handle.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
"""
 code=code.replace('PROJECT',repr(P)).replace('OUTPUT',repr(O)).replace('MSHA',repr(sha(mp))).replace('PLANSHA',repr(sha(plan))).replace('PRESHA',repr(sha(pre)))
 # Validate the actually expanded subprocess script before SSH execution.
 import ast;ast.parse(code)
 i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=60);i.write(code);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();rc=o.channel.recv_exit_status();(F/('OPERATOR_'+a.mode.upper()+'_STDOUT_v1.txt')).write_bytes(b);(F/('OPERATOR_'+a.mode.upper()+'_STDERR_v1.txt')).write_bytes(err);assert rc==0,err.decode()
 if a.mode=='stage':
  dest=F/'operator_cpu_remote_v1';dest.mkdir();s=c.open_sftp()
  for name in ('CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','unittest.log'):s.get(O+'/operator_cpu_v1/'+name,str(dest/name))
  s.close()
 else:(F/'OPERATOR_PILOT_HANDLE_v1.json').write_bytes(b)
 print(b.decode())
finally:c.close()

