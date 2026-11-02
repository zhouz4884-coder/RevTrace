"""Launch an explicit frozen CPU job after complete root input bindings."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
from remote import Remote,E,B,P,O,PY
R=E.parents[1]
p=argparse.ArgumentParser();p.add_argument('--job',type=Path,required=True);a=p.parse_args()
jobpath=a.job.resolve(strict=True);job=json.loads(jobpath.read_bytes());tag=job['tag'];assert tag.replace('_','').isalnum()
source=R/job['local_source'];M=R/job['local_manifest'];m=json.loads(M.read_bytes());commit=m['code_commit']
assert job['code_commit']==commit and job['command'][0]==PY and job['out'].startswith(O+'/')
sha=lambda b:hashlib.sha256(b).hexdigest();folder=jobpath.parent/(tag+'_PRELAUNCH');folder.mkdir(exist_ok=False)
with Remote() as c:
    c.put(jobpath,P+'/'+tag+'_JOB.json')
    script='C='+repr(dict(source=job['remote_source'],commit=commit))+'\n'+r'''
from pathlib import Path
import datetime,json,platform,subprocess,sys
assert subprocess.check_output(['git','-C',C['source'],'rev-parse','HEAD'],text=True).strip()==C['commit']
assert not subprocess.check_output(['git','-C',C['source'],'status','--porcelain','--untracked-files=all'],text=True).strip()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
print(json.dumps(dict(executable=sys.executable,python=sys.version,platform=platform.platform(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),code_commit=C['commit'],CUDA_VISIBLE_DEVICES='',scope='Explicit source-bound CPU-only analysis/audit; no model call')))
'''
    env=c.python(script);ep=folder/'ENVIRONMENT.json';ep.write_bytes(env);c.put(ep,P+'/'+tag+'_ENVIRONMENT.json')
    record=dict(experiment_id=job['experiment_id'],code_commit=commit,
        frozen_config=str(jobpath),frozen_config_sha256=sha(jobpath.read_bytes()),environment_record=str(ep.resolve()),environment_record_sha256=sha(env),
        raw_result_location=job['out'],aggregate_summary_location=job['out']+'/SUMMARY.json',gate_decision_location=job['out']+'/GATE.json',
        remote_config=P+'/'+tag+'_JOB.json',remote_environment=P+'/'+tag+'_ENVIRONMENT.json',
        source_manifest_sha256=sha(M.read_bytes()),launcher_sha256=sha(Path(__file__).read_bytes()),
        mirror_scope='Windows byte-exact inputs for root preflight; remote paths bound separately.')
    rec=folder/'RUN_RECORD_PRELAUNCH.json';rec.write_bytes((json.dumps(record,indent=2)+'\n').encode())
    r=subprocess.run([sys.executable,'-B',str(E/'ops/activate_source.py'),'--source',str(source),'--manifest',str(M),'--tag',tag,'--run-record',str(rec)],cwd=R,capture_output=True,check=True)
    print(r.stdout.decode(),flush=True);gate=E/('ROOT_NOARG_'+tag+'.json');c.put(gate,P+'/'+gate.name);c.put(rec,P+'/'+tag+'_PRELAUNCH.json')
    entry_files={}
    if 'entry_prelaunch_file' in job:
        body=dict(job.get('entry_prelaunch_extra',{}),config_sha256=job['entry_config_sha256'],
                  root_noarg_preflight=P+'/'+gate.name,root_noarg_preflight_sha256=sha(gate.read_bytes()))
        extra=folder/'ENTRY_PRELAUNCH.json';extra.write_bytes((json.dumps(body,indent=2)+'\n').encode())
        c.put(extra,job['entry_prelaunch_file']);entry_files[job['entry_prelaunch_file']]=sha(extra.read_bytes())
    C=dict(job=P+'/'+tag+'_JOB.json',jobsha=record['frozen_config_sha256'],environment=record['remote_environment'],envsha=record['environment_record_sha256'],gate=P+'/'+gate.name,gatesha=sha(gate.read_bytes()),log=O+'/'+tag.lower()+'.log',handle=O+'/'+tag.lower()+'_HANDLE.json',tmp=O+'/cpu_job_tmp',entry_files=entry_files)
    script='C='+repr(C)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,subprocess
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(C['job'])==C['jobsha'] and sha(C['environment'])==C['envsha'] and sha(C['gate'])==C['gatesha']
for p,h in C['entry_files'].items():assert sha(p)==h
j=json.loads(Path(C['job']).read_bytes());g=json.loads(Path(C['gate']).read_bytes());assert g['code_commit']==j['code_commit'] and g['run_record_prelaunch_checked']
assert not Path(j['out']).exists() and not Path(C['log']).exists() and not Path(C['handle']).exists()
Path(C['tmp']).mkdir(exist_ok=True)
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',TMPDIR=C['tmp'])
with Path(C['log']).open('xb') as f:p=subprocess.Popen(j['command'],cwd=j['remote_source'],env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc')/str(p.pid)
h=dict(pid=p.pid,start_ticks=int((proc/'stat').read_text().split()[21]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=j['command'],out=j['out'],log=C['log'],code_commit=j['code_commit'],root_gate=C['gate'],root_gate_sha256=C['gatesha'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_model_calls=0)
Path(C['handle']).write_text(json.dumps(h,indent=2));print(json.dumps(h))
'''
    raw=c.python(script);(E/'history'/(tag+'_HANDLE.json')).write_bytes(raw);print(raw.decode())
