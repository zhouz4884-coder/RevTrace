"""Approved-vault staging; no secrets enter arguments, artifacts, or output."""
import argparse,hashlib,json,pathlib,shlex,subprocess,sys
E=pathlib.Path(__file__).resolve().parents[1]
ROOT=E.parents[1]
OPS=E/'baseline_ops';PACK=E/'packages'
DISK='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
PROJECT=DISK+'/projects/revtrace_dsn_strengthening_v16_20261111/baseline_runtime_v1'
OUT=DISK+'/results/revtrace/dsn_strengthening_v16_20261111/CPU_BASELINE_V1'
PY=DISK+'/envs/revtrace-streamcorrect-20261028/bin/python'
LOCAL=OPS/'CPU_BASELINE_V1'
MODULES=['test_versioned_policy','test_resilience_owner_integration','test_resilience_policy',
 'test_resilience_inbound','test_resilience_storage','test_resilience_consumer',
 'test_resilience_transport','test_resilience_channel_close','test_fullspec_policy',
 'test_feedback_contract','test_resilience_metrics','test_service_campaign',
 'test_witness_semantics','test_native_consumer','test_stage_consumer',
 'test_long_reference','test_long_state_telemetry']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
    assert not p.exists(),p
    p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def connect():
    sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
    from contractkv_ssh_credential import ssh_client
    return ssh_client()
def execute(client,command,body=None):
    stdin,stdout,stderr=client.exec_command(command,timeout=300)
    if body is not None:stdin.write(body);stdin.flush();stdin.channel.shutdown_write()
    raw,err=stdout.read(),stderr.read();code=stdout.channel.recv_exit_status()
    return code,raw.decode('utf8'),err.decode('utf8')
def stage():
    assert not LOCAL.exists();LOCAL.mkdir()
    source=json.loads((PACK/'BASELINE_SOURCE_v1.json').read_bytes())
    c=connect()
    try:
        code,raw,err=execute(c,'python3 -B -',f"import pathlib\np=pathlib.Path({PROJECT!r})\nassert not p.exists(),p\np.mkdir(parents=True)\n")
        assert code==0,err
        with c.open_sftp() as sftp:
            for local,remote in [(PACK/'BASELINE_SOURCE_v1.bundle',PROJECT+'/SOURCE.bundle'),(PACK/'BASELINE_SOURCE_v1.json',PROJECT+'/SOURCE.json'),(OPS/'cpu_gate.py',PROJECT+'/cpu_gate.py')]:
                sftp.put(str(local),remote)
        params=dict(source_commit=source['source_commit'],source_manifest_sha256=sha(PACK/'BASELINE_SOURCE_v1.json'),cpu_gate_sha256=sha(OPS/'cpu_gate.py'),test_modules=MODULES)
        remote='''import datetime,hashlib,importlib.metadata,json,os,pathlib,platform,subprocess,sys
project=pathlib.Path(PROJECT);out=pathlib.Path(OUT);source=project/'source'
assert pathlib.Path(DISK).resolve()==pathlib.Path(DISK) and pathlib.Path(DISK).is_mount()
assert sys.version_info[:2]==(3,12)
assert not out.exists();out.mkdir(parents=True);(out/'tmp').mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\\n',encoding='utf8')
def git(*a):return subprocess.check_output(['git',*a],text=True,stderr=subprocess.PIPE).strip()
git('clone','--branch','codex/dsn-v16-baseline-runtime-v1',str(project/'SOURCE.bundle'),str(source))
git('-C',str(source),'config','core.autocrlf','false')
assert git('-C',str(source),'rev-parse','HEAD')==PARAMS['source_commit']
assert not git('-C',str(source),'status','--porcelain','--untracked-files=all')
manifest=project/'SOURCE.json';assert sha(manifest)==PARAMS['source_manifest_sha256']
m=json.loads(manifest.read_bytes());assert {r['path'] for r in m['files']}==set(git('-C',str(source),'ls-files').splitlines())
for r in m['files']:assert (source/r['path']).stat().st_size==r['bytes'] and sha(source/r['path'])==r['sha256'],r['path']
cfg=dict(experiment_id='DSN_V16_BASELINE_NATIVE_PROTOCOL_CPU_V1',source_root=str(source),source_manifest=str(manifest),raw_result_location=str(out),**PARAMS)
put(out/'CONFIG.json',cfg)
env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),host=platform.node(),numpy=importlib.metadata.version('numpy'),CUDA_VISIBLE_DEVICES='',PYTHONPATH=str(source),TMPDIR=str(out/'tmp'),source_clean=True,source_commit=PARAMS['source_commit'],model_imports='forbidden by MetaPathFinder',models_loaded=False,GPU_launched=False)
put(out/'ENVIRONMENT.json',env)
record=dict(experiment_id=cfg['experiment_id'],code_commit=cfg['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),source_manifest=str(manifest),source_manifest_sha256=sha(manifest),source_root=str(source),cpu_gate_sha256=sha(project/'cpu_gate.py'),prelaunch_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
put(out/'RUN_RECORD.json',record)
print(json.dumps(dict(record=record,environment=env,source_files=len(m['files']))))
'''
        body='PROJECT='+repr(PROJECT)+'\nOUT='+repr(OUT)+'\nDISK='+repr(DISK)+'\nPARAMS='+repr(params)+'\n'+remote
        code,raw,err=execute(c,shlex.quote(PY)+' -B -',body)
        (LOCAL/'STAGE_STDOUT.json').write_text(raw,encoding='utf8');(LOCAL/'STAGE_STDERR.log').write_text(err,encoding='utf8')
        assert code==0,err
        with c.open_sftp() as sftp:
            for name in ('CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json'):sftp.get(OUT+'/'+name,str(LOCAL/name))
        record=json.loads((LOCAL/'RUN_RECORD.json').read_bytes());record['frozen_config']=str(LOCAL/'CONFIG.json');record['environment_record']=str(LOCAL/'ENVIRONMENT.json')
        put(LOCAL/'LOCAL_PRELAUNCH_RECORD.json',record)
        command=[sys.executable,'-B',str(ROOT/'experiments/repository_identity_20261027/preflight.py'),'--source',str(E/'baseline_source_dev'),'--manifest',str(PACK/'BASELINE_SOURCE_v1.json'),'--run-record',str(LOCAL/'LOCAL_PRELAUNCH_RECORD.json'),'--output',str(LOCAL/'LOCAL_RUN_SOURCE_GATE.json')]
        result=subprocess.run(command,capture_output=True,text=True);(LOCAL/'LOCAL_PREFLIGHT_STDOUT.log').write_text(result.stdout+result.stderr,encoding='utf8');assert result.returncode==0,result.stdout+result.stderr
        print(raw)
    finally:c.close()
def run():
    assert (LOCAL/'LOCAL_RUN_SOURCE_GATE.json').exists()
    c=connect()
    try:
        env='CUDA_VISIBLE_DEVICES='+shlex.quote('')+' PYTHONPATH='+shlex.quote(PROJECT+'/source')+' TMPDIR='+shlex.quote(OUT+'/tmp')+' PYTHONDONTWRITEBYTECODE=1'
        command='env '+env+' '+shlex.quote(PY)+' -B '+shlex.quote(PROJECT+'/cpu_gate.py')+' --config '+shlex.quote(OUT+'/CONFIG.json')
        code,raw,err=execute(c,command)
        (LOCAL/'GATE_STDOUT.json').write_text(raw,encoding='utf8');(LOCAL/'GATE_STDERR.log').write_text(err,encoding='utf8')
        with c.open_sftp() as sftp:
            for name in ('SUMMARY.json','GATE.json','unittest.log','SOURCE_GATE_BEFORE.json','SOURCE_GATE_AFTER.json'):
                try:sftp.get(OUT+'/'+name,str(LOCAL/name))
                except FileNotFoundError:pass
        print(raw);print('formal_cpu_exit_code='+str(code))
        return code
    finally:c.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['stage','run']);a=p.parse_args()
    if a.phase=='stage':stage()
    else:raise SystemExit(run())
