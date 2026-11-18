"""Stage frozen controller/auditor and execute their formal CPU controls."""
from pathlib import Path
import importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_joint_retention_20261118';O=B+'/results/revtrace/dsn_native_joint_retention_20261118'
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
with m.Remote()as c:
 for label,folder in [('CAMPAIGN_SOURCE_V1','campaign_v1'),('AUDIT_SOURCE_V1','audit_v1')]:
  target=P+'/'+folder;x=json.loads((E/'packages'/(label+'.json')).read_bytes());c.python('from pathlib import Path\nPath('+repr(target)+').mkdir(parents=True,exist_ok=True)\n')
  c.put(E/'packages'/(label+'.json'),target+'/SOURCE.json');c.put(E/'packages'/(label+'.bundle'),target+'/SOURCE.bundle')
  C=dict(root=target,commit=x['source_commit'],out=O+'/CPU_'+folder.upper(),tmp=B+'/cache/revtrace_native_rs_20261118/cpu_'+folder,nn=P+'/runtime_v1/source')
  raw=c.python('C='+repr(C)+'\n'+r'''
from pathlib import Path
import hashlib,json,os,subprocess,sys
t=Path(C['root']);src=t/'source';mf=t/'SOURCE.json';m=json.loads(mf.read_bytes())
if not src.exists():subprocess.run(['git','clone',str(t/'SOURCE.bundle'),str(src)],check=True,capture_output=True)
subprocess.run(['git','-C',str(src),'config','core.autocrlf','false'],check=True,capture_output=True)
assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()==C['commit']
assert not subprocess.check_output(['git','-C',str(src),'status','--porcelain','--untracked-files=all'],text=True).strip()
for r in m['files']:
 p=src/r['path'];assert p.stat().st_size==r['bytes']and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
out=Path(C['out']);out.mkdir(exist_ok=False);Path(C['tmp']).mkdir(parents=True,exist_ok=True)
def put(n,x):(out/n).write_text(json.dumps(x,indent=2)+'\n')
command=[sys.executable,'-B','-m','unittest','discover','-s',str(src),'-p','test_*.py','-v'];env=dict(os.environ,TMPDIR=C['tmp'],PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=C['nn'],CUDA_VISIBLE_DEVICES='')
put('CONFIG.json',dict(experiment_id='REVTRACE_NATIVE_RS_'+out.name,command=command,source_commit=C['commit'],model_calls=0));put('ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,CUDA_VISIBLE_DEVICES='',cpu_only=True))
put('RUN_RECORD.json',dict(experiment_id='REVTRACE_NATIVE_RS_'+out.name,code_commit=C['commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=hashlib.sha256((out/'CONFIG.json').read_bytes()).hexdigest(),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=hashlib.sha256((out/'ENVIRONMENT.json').read_bytes()).hexdigest(),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
p=subprocess.run(command,cwd=src,env=env,capture_output=True,text=True);log=p.stdout+p.stderr;(out/'CPU_CONTROLS.log').write_text(log)
result=dict(status='PASS_FROZEN_CPU_CONTROLS'if p.returncode==0 else'FAIL_FROZEN_CPU_CONTROLS_PRESERVED',code_commit=C['commit'],returncode=p.returncode,new_model_calls=0,tail=log[-2400:]);put('SUMMARY.json',result);put('GATE.json',dict(status=result['status']));print(json.dumps(result));assert p.returncode==0
''',timeout=120)
  (E/'baseline'/(folder+'_CPU_STDOUT.json')).write_bytes(raw+b'\n');print(raw.decode(),flush=True)
  for n in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','CPU_CONTROLS.log']:c.get(C['out']+'/'+n,E/'baseline'/('CPU_'+folder.upper())/n)
