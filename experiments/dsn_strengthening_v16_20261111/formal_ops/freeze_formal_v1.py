"""Freeze an independent CPU action-invariant audit; leave CURRENT untouched."""
import datetime
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

E=Path(__file__).resolve().parents[1]
R=E.parents[1]
S=E/'formal_source_dev'
P=E/'formal_packages_v1'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
REMOTE_PROJECT=B+'/projects/revtrace_dsn_strengthening_v16_20261111/formal_action_v1'
REMOTE_OUT=B+'/results/revtrace/dsn_strengthening_v16_20261111/formal_action_v1'
PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
EXPERIMENT='REVTRACE_V16_FORMAL_PHASE_ACTION_V1_20261111'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):
    assert not p.exists(),p
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def git(where,*args):return subprocess.check_output(['git','-C',str(where),*args],text=True).strip()

def main():
    before=sha(R/'experiments/repository_identity_20261027/CURRENT.json')
    preflight=json.loads(subprocess.check_output([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],text=True,cwd=R))
    assert preflight['code_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
    assert preflight['gate']=='SOURCE_IDENTITY_PASS'
    P.mkdir(exist_ok=False)
    put(P/'DEFAULT_PREFLIGHT_BEFORE.json',preflight)
    sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
    from contractkv_ssh_credential import ssh_client
    c=ssh_client()
    try:
        code=r'''import datetime,json,os,pathlib,platform,shutil,subprocess,sys
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader'],text=True,timeout=10).strip()
assert not compute,'CPU formal launch waits for GPU quiescence'
print(json.dumps(dict(python=sys.version,executable=sys.executable,platform=platform.platform(),hostname=platform.node(),CUDA_VISIBLE_DEVICES='',execution='finite symbolic CPU specification only',model_calls=0,GPU_calls=0,resource_check=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),compute_processes=compute,disk=shutil.disk_usage(__BASE__)._asdict(),memory=[l for l in pathlib.Path('/proc/meminfo').read_text().splitlines() if l.startswith(('MemTotal:','MemAvailable:'))]))))
'''.replace('__BASE__',repr(B))
        i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=60)
        i.write(code);i.flush();i.channel.shutdown_write()
        raw,err=o.read(),e.read();rc=o.channel.recv_exit_status()
        assert rc==0,err.decode('utf8',errors='replace')
        environment=json.loads(raw)
    finally:c.close()
    put(P/'FROZEN_ENVIRONMENT.json',environment)
    originals={}
    for name in ('model.py','test_model.py'):
        old=R/'experiments/dsn_native_refinement_20261030/source_v3'/name
        assert old.read_bytes()==(S/name).read_bytes()
        originals[name]=dict(sha256=sha(old),bytes=old.stat().st_size,
                             original_source_commit='deb3260655e2f3312499a34597cc0be6fc15484b')
    subprocess.run(['git','init','--initial-branch=codex/v16-formal-phase-action'],cwd=S,check=True,capture_output=True,text=True)
    for k,v in [('core.autocrlf','false'),('user.name','RevTrace Research'),('user.email','source@revtrace.local')]:git(S,'config',k,v)
    git(S,'add','-A');git(S,'commit','-m','spec: add phase-correct action invariants over unchanged v3 model')
    commit=git(S,'rev-parse','HEAD')
    assert not git(S,'status','--porcelain','--untracked-files=all')
    files=[]
    for name in git(S,'ls-files').splitlines():
        path=S/name;files.append(dict(path=name,bytes=path.stat().st_size,sha256=sha(path)))
    manifest=P/'SOURCE.json'
    put(manifest,dict(source_commit=commit,code_commit=commit,files=files,
        original_v3_copies=originals,scope='independent bounded hand-written CPU specification design verification; no neural runtime change or whole Python/CUDA proof'))
    bundle=P/'SOURCE.bundle';git(S,'bundle','create',str(bundle),'HEAD')
    ref='refs/research/dsn-strengthening-v16-formal-phase-action-v1'
    git(R,'fetch',str(bundle),'HEAD:'+ref)
    assert git(R,'rev-parse',ref)==commit
    assert git(R,'cat-file','-t',commit)=='commit'
    plan=dict(experiment_id=EXPERIMENT,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_commit=commit,source_manifest_sha256=sha(manifest),
        original_v3_source_commit='deb3260655e2f3312499a34597cc0be6fc15484b',
        original_neural_source_anchor='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',
        frozen_environment_sha256=sha(P/'FROZEN_ENVIRONMENT.json'),
        expected_environment={k:environment[k] for k in ('python','executable','platform','CUDA_VISIBLE_DEVICES','execution','model_calls','GPU_calls')},
        profiles=dict(normal_two_frontiers=dict(frontiers=2,max_issued=3,max_depth=12,max_faults=0,state_cap=150000),
                      failure_one_frontier=dict(frontiers=1,max_issued=2,max_depth=12,max_faults=1,state_cap=150000)),
        expected_unchanged_model_counts=dict(normal_two_frontiers=dict(states=6231,edges=11142,depth_cutoffs=2144,terminal_states=16),
                      failure_one_frontier=dict(states=14074,edges=25799,depth_cutoffs=2828,terminal_states=2196)),
        expected_named_controls=35,original_controls_preserved=27,new_phase_action_controls=8,
        intended_raw_result_location=REMOTE_OUT+'/results',intended_summary_location=REMOTE_OUT+'/results/SUMMARY.json',
        intended_gate_location=REMOTE_OUT+'/results/GATE.json',
        scope='Additional phase-correct state/action obligations on unchanged v3 finite hand-written specification, preserving legal durable-before-install/crash gaps. Not runtime extraction, unbounded proof, neural result, natural prevalence or serving evidence.')
    put(P/'CONFIG.json',plan)
    record=dict(experiment_id=EXPERIMENT,source_commit=commit,source_files=len(files),source_manifest=str(manifest),
        source_manifest_sha256=sha(manifest),source_bundle=str(bundle),source_bundle_sha256=sha(bundle),
        local_resolvable_execution_ref=ref,config=str(P/'CONFIG.json'),config_sha256=sha(P/'CONFIG.json'),
        frozen_environment=str(P/'FROZEN_ENVIRONMENT.json'),frozen_environment_sha256=sha(P/'FROZEN_ENVIRONMENT.json'),
        remote_project=REMOTE_PROJECT,remote_output=REMOTE_OUT,raw_result_location=plan['intended_raw_result_location'],
        summary=plan['intended_summary_location'],gate=plan['intended_gate_location'],
        default_current_sha256_before=before,default_current_unchanged=sha(R/'experiments/repository_identity_20261027/CURRENT.json')==before,
        original_v3_copies=originals,formal_run_started=False,models_or_GPU_launched=False)
    assert record['default_current_unchanged']
    put(P/'FREEZE_RECORD.json',record)
    print(json.dumps(record,indent=2))

if __name__=='__main__':main()
