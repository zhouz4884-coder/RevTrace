"""Stage a frozen CPU-only analyzer and bind its prelaunch inputs on8TB."""
import hashlib,json,pathlib,shlex,subprocess,sys
E=pathlib.Path(__file__).resolve().parents[1];R=E.parents[1]
F=R/'experiments/dsn_native_resilience_20261030'
env=json.loads((F/'FROZEN_ENVIRONMENT_v2.json').read_bytes());PY=env['executable'];B=PY.split('/envs/')[0]
P=B+'/projects/revtrace_dsn_strengthening_20261031';O=B+'/results/revtrace/dsn_strengthening_20261031'
package=E/'diagnostic_source_freeze_v2';M=package/'DIAGNOSTIC_SOURCE_v2.json';bundle=package/'DIAGNOSTIC_SOURCE_v2.bundle';noarg=E/'DIAG_SOURCE_ACTIVATION_v3.json'
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
manifest=json.loads(M.read_bytes());assert manifest['code_commit']=='ff95f04465d006f76a0e729d3fd5457c32769c1e'
gate=json.loads(noarg.read_bytes());assert gate['code_commit']==manifest['code_commit'] and gate['manifest_sha256']==sha(M)
remote=dict(project=P,output=O,base=B,source=P+'/diagnostic_source_v2',manifest=P+'/DIAGNOSTIC_SOURCE_v2.json',bundle=P+'/DIAGNOSTIC_SOURCE_v2.bundle',noarg=P+'/DIAG_ROOT_NOARG_v2.json',manifest_sha=sha(M),bundle_sha=sha(bundle),noarg_sha=sha(noarg),python=PY,control=O+'/diagnostic_v2_control',results=O+'/diagnostic_v2_results',old_project=B+'/projects/revtrace_dsn_native_resilience_20261030',audit=B+'/results/revtrace/dsn_native_refinement_20261030/formal_actual36_v1')
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
    i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=30)
    i.write('from pathlib import Path\nfor p in '+repr([P,O])+':\n x=Path(p).resolve();assert x.is_relative_to(Path('+repr(B)+').resolve());x.mkdir(parents=True,exist_ok=True)\n');i.flush();i.channel.shutdown_write();err=e.read();assert o.channel.recv_exit_status()==0,err.decode()
    s=c.open_sftp()
    for local,target in [(M,remote['manifest']),(bundle,remote['bundle']),(noarg,remote['noarg'])]:
        raw=local.read_bytes()
        try:
            with s.open(target,'rb') as f:assert f.read()==raw,'staged immutable file differs'
        except FileNotFoundError:
            with s.open(target,'wx') as f:f.write(raw);f.flush()
    s.close()
    script='C='+repr(remote)+'\n'+r'''
import hashlib,json,os,pathlib,subprocess,sys
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for x in iter(lambda:f.read(4*1024*1024),b''):h.update(x)
 return h.hexdigest()
assert sha(C['manifest'])==C['manifest_sha'] and sha(C['bundle'])==C['bundle_sha'] and sha(C['noarg'])==C['noarg_sha']
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=20).strip(),'GPU is occupied; no heavy CPU/IO while another serving job owns it'
source=pathlib.Path(C['source'])
if not source.exists():
 subprocess.run(['git','clone','-q','--no-checkout',C['bundle'],str(source)],check=True)
 subprocess.run(['git','-C',str(source),'config','core.autocrlf','false'],check=True)
 subprocess.run(['git','-C',str(source),'checkout','-q','ff95f04465d006f76a0e729d3fd5457c32769c1e'],check=True)
sys.path.insert(0,str(source));from evidence_io import identity
ident=identity(source,C['manifest']);assert ident['files_verified']==19
tmp=pathlib.Path(C['output'])/'bootstrap_tmp_v2';tmp.mkdir(exist_ok=True)
runenv=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(tmp))
cmd=[C['python'],'-B',str(source/'prepare_config.py'),'--base',C['base'],'--manifest',C['manifest'],'--plans',C['old_project']+'/FORMAL_SHORT28_v1_FROZEN.json',C['old_project']+'/FORMAL_SUSTAINED8_v1_FROZEN.json','--prior-audit-root',C['audit'],'--root-noarg-record',C['noarg'],'--control-out',C['control'],'--results-out',C['results'],'--experiment-id','SC_ACTUAL36_PAIRING_LONG8_BOUNDARY_20261031_V2']
r=subprocess.run(cmd,capture_output=True,env=runenv)
log=pathlib.Path(C['output'])/'diagnostic_v2_prepare.log';assert not log.exists();log.write_bytes(r.stdout+r.stderr)
if r.returncode:print(r.stdout.decode(errors='replace'));print(r.stderr.decode(errors='replace'),file=sys.stderr);raise SystemExit(r.returncode)
print(r.stdout.decode(),end='')
'''
    i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=900);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status()
    for name,data in [('DIAG_REMOTE_PREPARE_STDOUT_v2.txt',stdout),('DIAG_REMOTE_PREPARE_STDERR_v2.txt',stderr)]:
        p=E/name;assert not p.exists();p.write_bytes(data)
    assert rc==0,stderr.decode('utf8',errors='replace')[-3000:]
    local=E/'diagnostic_v2_control_mirror';local.mkdir()
    s=c.open_sftp()
    for name in ('CONFIG_FROZEN.json','ENVIRONMENT.json','RAW_INPUT_INDEX.json','RUN_RECORD_PRELAUNCH.json'):
        with s.open(remote['control']+'/'+name,'rb') as f:data=f.read()
        (local/name).write_bytes(data)
    s.close()
    run=json.loads((local/'RUN_RECORD_PRELAUNCH.json').read_bytes());run['frozen_config']=str((local/'CONFIG_FROZEN.json').resolve());run['environment_record']=str((local/'ENVIRONMENT.json').resolve());run['mirror_scope']='Exact byte copies of actual remote frozen config/environment for Windows root preflight; original remote run record preserved separately.'
    mirror=local/'RUN_RECORD_ROOT_CHECK.json';mirror.write_text(json.dumps(run,indent=2)+'\n',encoding='utf8')
    receipt=E/'DIAG_COMPLETE_PRELAUNCH_ROOT_GATE_v2.json';assert not receipt.exists()
    result=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--run-record',str(mirror)],cwd=R,capture_output=True,check=True);receipt.write_bytes(result.stdout)
    s=c.open_sftp()
    with s.open(P+'/DIAG_COMPLETE_PRELAUNCH_ROOT_GATE_v2.json','wx') as f:f.write(receipt.read_bytes());f.flush()
    s.close();record=E/'DIAG_STAGED_v2.json';assert not record.exists();record.write_text(json.dumps(dict(status='PASS_FROZEN_SOURCE_AND_COMPLETE_PRELAUNCH_BINDINGS',**remote,root_prelaunch_sha256=sha(receipt),new_model_calls=0,formal_scan_completed=False),indent=2)+'\n',encoding='utf8');print(stdout.decode());print(result.stdout.decode())
finally:c.close()
