"""Stage a committed source and execute source-bound CPU controls with full records."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
from remote import Remote,E,B,P,O,PY
R=E.parents[1]
p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--source',type=Path,required=True)
p.add_argument('--test-module',required=True);p.add_argument('--expected-tests',type=int,required=True)
p.add_argument('--run-label');a=p.parse_args()
assert a.name.replace('_','').isalnum() and a.test_module.replace('_','').isalnum()
source=a.source.resolve(strict=True);M=E/'packages'/(a.name+'_SOURCE.json');bundle=M.with_suffix('.bundle')
m=json.loads(M.read_bytes());commit=m['code_commit'];sha=lambda b:hashlib.sha256(b).hexdigest()
label=a.name if a.run_label is None else a.name+'_'+a.run_label
assert label.replace('_','').isalnum()
control=E/'controls'/label;control.mkdir(parents=True,exist_ok=False)
remote_source=P+'/'+a.name.lower();out=O+'/'+label.lower()+'_controls'
tag=label+'_CONTROLS';config_path=control/'CONFIG.json';env_path=control/'ENVIRONMENT.json';record_path=control/'RUN_RECORD_PRELAUNCH.json'
config=dict(experiment_id='REVTRACE_'+tag+'_20261102',code_commit=commit,test_module=a.test_module,
            expected_tests=a.expected_tests,source_manifest_sha256=sha(M.read_bytes()),
            source=remote_source,output=out,CUDA_VISIBLE_DEVICES='',scope='CPU controls only; no model/inference/serving result')
config_path.write_bytes((json.dumps(config,indent=2)+'\n').encode())
with Remote() as c:
    print(c.python('from pathlib import Path\nfor s in '+repr([P,O,out+'_tmp'])+':\n p=Path(s).resolve();assert p.is_relative_to(Path('+repr(B)+'));p.mkdir(parents=True,exist_ok=True)\n').decode())
    c.put(M,P+'/'+M.name);c.put(bundle,P+'/'+bundle.name);c.put(config_path,P+'/'+tag+'_CONFIG.json')
    payload=dict(source=remote_source,manifest=P+'/'+M.name,bundle=P+'/'+bundle.name,commit=commit,
                 manifest_sha256=sha(M.read_bytes()),bundle_sha256=sha(bundle.read_bytes()))
    script='C='+repr(payload)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,platform,subprocess,sys
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(C['manifest'])==C['manifest_sha256'] and sha(C['bundle'])==C['bundle_sha256']
s=Path(C['source'])
if not s.exists():
 subprocess.run(['git','clone','-q','--no-checkout',C['bundle'],str(s)],check=True)
 subprocess.run(['git','-C',str(s),'config','core.autocrlf','false'],check=True)
 subprocess.run(['git','-C',str(s),'checkout','-q',C['commit']],check=True)
def git(*a):return subprocess.check_output(['git','-C',str(s),*a],text=True).strip()
m=json.loads(Path(C['manifest']).read_bytes())
assert git('rev-parse','HEAD')==C['commit'] and not git('status','--porcelain','--untracked-files=all')
assert set(git('ls-files').splitlines())=={r['path'] for r in m['files']}
for r in m['files']:assert (s/r['path']).stat().st_size==r['bytes'] and sha(s/r['path'])==r['sha256']
print(json.dumps(dict(python=sys.version,executable=sys.executable,platform=platform.platform(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source=C['source'],code_commit=C['commit'],source_manifest=C['manifest'],source_manifest_sha256=C['manifest_sha256'],complete_files=len(m['files']),CUDA_VISIBLE_DEVICES='',scope='Source-bound CPU controls; TMPDIR on designated8TB; no inference')))
'''
    envraw=c.python(script);env_path.write_bytes(envraw)
    c.put(env_path,P+'/'+tag+'_ENVIRONMENT.json')
    record=dict(experiment_id=config['experiment_id'],code_commit=commit,
                frozen_config=str(config_path.resolve()),frozen_config_sha256=sha(config_path.read_bytes()),
                environment_record=str(env_path.resolve()),environment_record_sha256=sha(envraw),
                raw_result_location=out,aggregate_summary_location=out+'/SUMMARY.json',gate_decision_location=out+'/GATE.json',
                remote_config=P+'/'+tag+'_CONFIG.json',remote_environment=P+'/'+tag+'_ENVIRONMENT.json',
                source_manifest=str(M.resolve()),source_manifest_sha256=sha(M.read_bytes()),
                launcher_sha256=sha(Path(__file__).read_bytes()),
                mirror_scope='Windows byte-exact frozen-input mirror for root preflight; actual run record uses the corresponding remote paths.')
    record_path.write_bytes((json.dumps(record,indent=2)+'\n').encode())
    result=subprocess.run([sys.executable,'-B',str(E/'ops/activate_source.py'),'--source',str(source),'--manifest',str(M),'--tag',tag,'--run-record',str(record_path)],cwd=R,capture_output=True,check=True)
    print(result.stdout.decode(),flush=True)
    gate=E/('ROOT_NOARG_'+tag+'.json');c.put(gate,P+'/'+gate.name);c.put(record_path,P+'/'+tag+'_PRELAUNCH.json')
    params=dict(source=remote_source,commit=commit,config=record['remote_config'],environment=record['remote_environment'],
                config_sha256=record['frozen_config_sha256'],environment_sha256=record['environment_record_sha256'],
                record=P+'/'+tag+'_PRELAUNCH.json',root_gate=P+'/'+gate.name,root_gate_sha256=sha(gate.read_bytes()),
                out=out,tmp=out+'_tmp',python=PY,module=a.test_module,expected=a.expected_tests)
    script='C='+repr(params)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,re,subprocess,time
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(C['config'])==C['config_sha256'] and sha(C['environment'])==C['environment_sha256'] and sha(C['root_gate'])==C['root_gate_sha256']
g=json.loads(Path(C['root_gate']).read_bytes());assert g['code_commit']==C['commit'] and g['run_record_prelaunch_checked']
out=Path(C['out']);out.mkdir(exist_ok=False)
cmd=[C['python'],'-B','-m','unittest','-v',C['module']]
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',TMPDIR=C['tmp'])
record=json.loads(Path(C['record']).read_bytes());record.update(root_mirror_config=record['frozen_config'],root_mirror_environment=record['environment_record'],frozen_config=C['config'],environment_record=C['environment'],actual_command=cmd,actual_cwd=C['source'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(out/'RUN_RECORD.json').write_text(json.dumps(record,indent=2))
start=time.perf_counter();r=subprocess.run(cmd,cwd=C['source'],env=env,capture_output=True,timeout=90);elapsed=time.perf_counter()-start
(out/'STDOUT.txt').write_bytes(r.stdout);(out/'STDERR.txt').write_bytes(r.stderr)
text=(r.stdout+r.stderr).decode(errors='replace');match=re.search(r'Ran (\d+) tests?',text);n=int(match.group(1)) if match else None
clean=not subprocess.check_output(['git','-C',C['source'],'status','--porcelain','--untracked-files=all'],text=True).strip()
ok=r.returncode==0 and n==C['expected'] and clean
summary=dict(status='PASS_FROZEN_CPU_CONTROLS' if ok else 'FAIL_FROZEN_CPU_CONTROLS',tests=n,expected=C['expected'],exit_code=r.returncode,wall_seconds=elapsed,code_commit=C['commit'],source_clean_after=clean,new_model_calls=0)
(out/'SUMMARY.json').write_text(json.dumps(summary,indent=2));(out/'GATE.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary));print(text[-5000:])
'''
    stdout=c.python(script,timeout=120);(control/'REMOTE_STDOUT.txt').write_bytes(stdout);print(stdout.decode(),flush=True)
    for name in ['SUMMARY.json','GATE.json','RUN_RECORD.json','STDOUT.txt','STDERR.txt']:
        c.get(out+'/'+name,control/name)
