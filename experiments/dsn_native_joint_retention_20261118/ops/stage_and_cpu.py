"""Stage immutable sources and run source-bound CPU readiness/controls, no models."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1]
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_joint_retention_20261118';O=B+'/results/revtrace/dsn_native_joint_retention_20261118'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
with m.Remote()as c:
 for label,folder in [('RUNTIME_SOURCE_V1','runtime_v1'),('READINESS_SOURCE','readiness')]:
  mf=E/'packages'/(label+'.json');bundle=E/'packages'/(label+'.bundle');x=json.loads(mf.read_bytes());target=P+'/'+folder
  c.python('from pathlib import Path\nPath('+repr(target)+').mkdir(parents=True,exist_ok=True)\n')
  c.put(mf,target+'/SOURCE.json');c.put(bundle,target+'/SOURCE.bundle')
  code='C='+repr(dict(root=target,commit=x['source_commit'],manifest_sha=sha(mf)))+'\n'+r'''
from pathlib import Path
import hashlib,json,subprocess
t=Path(C['root']);s=t/'source';m=t/'SOURCE.json'
assert hashlib.sha256(m.read_bytes()).hexdigest()==C['manifest_sha']
if not s.exists():subprocess.run(['git','clone',str(t/'SOURCE.bundle'),str(s)],check=True,capture_output=True)
subprocess.run(['git','-C',str(s),'config','core.autocrlf','false'],check=True,capture_output=True)
assert subprocess.check_output(['git','-C',str(s),'rev-parse','HEAD'],text=True).strip()==C['commit']
assert not subprocess.check_output(['git','-C',str(s),'status','--porcelain','--untracked-files=all'],text=True).strip()
x=json.loads(m.read_bytes());assert set(subprocess.check_output(['git','-C',str(s),'ls-files'],text=True).splitlines())=={r['path']for r in x['files']}
for r in x['files']:
 p=s/r['path'];assert p.stat().st_size==r['bytes']and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
print(json.dumps(dict(status='PASS_COMPLETE_REMOTE_SOURCE',commit=C['commit'],files=len(x['files']),root=str(s))))
'''
  raw=c.python(code,timeout=30);(E/'baseline'/('REMOTE_'+label+'.json')).write_bytes(raw+b'\n');print(raw.decode(),flush=True)
 # Reuse the original prespecified eight-source bank, preserving its identity.
 receipt=json.loads((R/'experiments/dsn_strengthening_v16_20261111/baseline_ops/FOCUSED_CONFIRMATION_PREPARATION_V2/SELECTION_RECEIPT.json').read_bytes())['parent_bank_receipt']
 raw=c.get(receipt['path'],E/'baseline/ORIGINAL_SELECTION_BANK.json');assert hashlib.sha256(raw).hexdigest()==receipt['sha256'];selection=json.loads(raw)
 template=json.loads((R/'experiments/dsn_strengthening_v16_20261111/baseline_ops/FOCUSED_CONFIRMATION_PREPARATION_V2/configs/SC_V16_CONFIRM_BAC009S0902W0343_fullcall_r0.json').read_bytes())
 put(E/'baseline/ORIGINAL_TEMPLATE.json',template);oldenv=json.loads((R/'experiments/dsn_strengthening_v16_20261111/baseline_ops/PILOT_PREPARATION_V2/ENVIRONMENT.json').read_bytes())
 audio={s['path']:s for s in selection['sources']+template['settings']['model_sources']}
 C=dict(paths=list(audio),packages=oldenv['packages'],root=P,out=O)
 raw=c.python('C='+repr(C)+'\n'+r'''
from pathlib import Path
import datetime,importlib.metadata,json,os,subprocess,sys
for p in [C['root'],C['out']]:Path(p).mkdir(parents=True,exist_ok=True)
versions={k:importlib.metadata.version(k)for k in C['packages']};assert versions==C['packages']
print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),executable=sys.executable,packages=versions,audio_files=[dict(path=p,bytes=Path(p).stat().st_size)for p in C['paths']],no_neural_imports=True,compute_owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip())))
''',timeout=25);fresh=json.loads(raw);assert not fresh['compute_owners'];(E/'baseline/FRESH_ENVIRONMENT_METADATA.json').write_bytes(raw+b'\n')
 config=dict(experiment_id='REVTRACE_NATIVE_RS_CPU_READINESS_V1',disk_root=B,raw_result_location=O+'/CPU_READINESS_V1',packages=oldenv['packages'],executable=oldenv['executable'],assets_manifest=oldenv['assets_manifest_path'],assets_manifest_sha256=oldenv['assets_manifest_sha256'],audio_files=[dict(**a,sha256=audio[a['path']]['audio_sha256'])for a in fresh['audio_files']])
 cfg=E/'plans/READINESS_CONFIG.json';put(cfg,config);pre=E/'plans/READINESS_PRELAUNCH.json';put(pre,dict(source_commit='3fb1951ba58b74110403c72d885efa8077e3140c',config_sha256=sha(cfg),new_model_calls=0))
 c.put(cfg,P+'/readiness/CONFIG.json');c.put(pre,P+'/readiness/PRELAUNCH.json')
 command=[fresh['executable'],'-B',P+'/readiness/source/readiness.py','--manifest',P+'/readiness/SOURCE.json','--config',P+'/readiness/CONFIG.json','--prelaunch',P+'/readiness/PRELAUNCH.json']
 raw=c.python('import subprocess\np=subprocess.run('+repr(command)+',capture_output=True,text=True)\nprint(p.stdout)\nassert p.returncode==0,p.stderr[-6000:]\n',timeout=180)
 (E/'baseline/READINESS_STDOUT.json').write_bytes(raw);print(raw.decode(),flush=True)
 for n in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json']:c.get(O+'/CPU_READINESS_V1/'+n,E/'baseline/CPU_READINESS_V1'/n)
 nn=json.loads((E/'packages/RUNTIME_SOURCE_V1.json').read_bytes());C=dict(source=P+'/runtime_v1/source',commit=nn['source_commit'],out=O+'/CPU_RUNTIME_V1',tmp=B+'/cache/revtrace_native_rs_20261118/cpu_tmp')
 raw=c.python('C='+repr(C)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
out=Path(C['out']);out.mkdir(exist_ok=False);Path(C['tmp']).mkdir(parents=True,exist_ok=True)
def put(n,x):(out/n).write_text(json.dumps(x,indent=2)+'\n')
cmd=[sys.executable,'-B','-m','unittest','discover','-s',C['source'],'-p','test_*.py','-v'];env=dict(os.environ,TMPDIR=C['tmp'],PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='')
put('CONFIG.json',dict(experiment_id='REVTRACE_NATIVE_RS_CPU_RUNTIME_V1',command=cmd,source_commit=C['commit'],model_calls=0))
put('ENVIRONMENT.json',dict(executable=sys.executable,python=sys.version,CUDA_VISIBLE_DEVICES='',cpu_only=True))
put('RUN_RECORD.json',dict(experiment_id='REVTRACE_NATIVE_RS_CPU_RUNTIME_V1',code_commit=C['commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=hashlib.sha256((out/'CONFIG.json').read_bytes()).hexdigest(),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=hashlib.sha256((out/'ENVIRONMENT.json').read_bytes()).hexdigest(),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
p=subprocess.run(cmd,cwd=C['source'],env=env,capture_output=True,text=True);(out/'CPU_CONTROLS.log').write_text(p.stdout+p.stderr)
s=dict(status='PASS_FROZEN_RUNTIME_CPU_CONTROLS'if p.returncode==0 else'FAIL_FROZEN_RUNTIME_CPU_CONTROLS_PRESERVED',returncode=p.returncode,code_commit=C['commit'],new_model_calls=0,tail=(p.stdout+p.stderr)[-1500:]);put('SUMMARY.json',s);put('GATE.json',dict(status=s['status']));print(json.dumps(s));assert p.returncode==0
''',timeout=120);(E/'baseline/CPU_RUNTIME_STDOUT.json').write_bytes(raw+b'\n');print(raw.decode(),flush=True)
 for n in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','CPU_CONTROLS.log']:c.get(O+'/CPU_RUNTIME_V1/'+n,E/'baseline/CPU_RUNTIME_V1'/n)
 env=dict(oldenv);env.update(record_type='FRESH_NATIVE_RS_ENVIRONMENT_NOT_MODEL_READY',actual_NN_source_commit=nn['source_commit'],current_readiness=dict(path=O+'/CPU_READINESS_V1/SUMMARY.json',sha256=sha(E/'baseline/CPU_READINESS_V1/SUMMARY.json'),source_commit='3fb1951ba58b74110403c72d885efa8077e3140c'),cache_temperature='Full asset hashes verified in this phase; no cold-cache claim')
 put(E/'plans/ENVIRONMENT.json',env);c.put(E/'plans/ENVIRONMENT.json',P+'/ENVIRONMENT.json')
 put(E/'WORKING_STATE.json',dict(status='NEW_RUNTIME_CPU_PASS_REFERENCE_PREPARATION_PENDING',runtime_commit=nn['source_commit'],planned_factorial_cells=64,planned_conservative_anchor_cells=16,reference_generation_required=True,paper_edits=False))
