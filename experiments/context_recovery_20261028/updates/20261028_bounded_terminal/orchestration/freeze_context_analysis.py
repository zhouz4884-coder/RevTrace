from pathlib import Path
import gzip,hashlib,importlib.metadata,json,os,platform,subprocess,sys
R=Path(r'D:\VLA_QWEN\RevTrace\experiments\context_recovery_20261028');S=R/'source';V=sys.argv[1]
assert V in ('v1','v2','v3','v4','v5','v6','v7','v8','v9','v10','v11','v12')
def git(*a,raw=False):
    out=subprocess.check_output(['git','-C',str(S),*a],stderr=subprocess.PIPE)
    return out if raw else out.decode().strip()
if not (S/'.git').exists():git('init');git('config','core.autocrlf','false')
names=['audit_recovery.py','test_analysis.py','pytest.ini','PROTOCOL.md']
names += [x for x in ['prepare_holdout.py','holdout_source.json','audit_legacy_contracts.py','paid_context_probe.py','test_context_probe.py'] if (S/x).exists()]
names += [x for x in ['audit_context.py','test_context_audit.py'] if (S/x).exists()]
names += [x for x in ['decide_context.py'] if (S/x).exists()]
names += [x for x in ['native_prompt_probe.py','test_native_prompt.py'] if (S/x).exists()]
names += [x for x in ['merge_anomaly_evidence.py','test_anomaly_merge.py'] if (S/x).exists()]
names += [x for x in ['audit_wait_closure.py','test_wait_closure.py'] if (S/x).exists()]
git('add','--',*names)
git('diff','--cached','--check')
if git('diff','--cached','--name-only'):git('-c','user.name=Research Artifact','-c','user.email=artifact@example.invalid','commit','-m','Freeze independent native recovery asset/input and clock audit')
commit=git('rev-parse','HEAD');assert not git('status','--porcelain')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
    assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n')
files=[dict(path=p,bytes=(S/p).stat().st_size,sha256=sha(S/p)) for p in git('ls-files').splitlines()]
put(R/('SOURCE_'+V+'.json'),dict(code_commit=commit,files=files,baseline_archive='4af44aac707ba84119ea13f05f6a9130c869dec4',scope='independent CPU analysis source; GPU runtime source is separately identified'))
(R/('source_'+V+'.tar.gz')).write_bytes(gzip.compress(git('archive','HEAD',raw=True),mtime=0));git('bundle','create',str(R/('source_'+V+'.bundle')),'HEAD')
subprocess.run(['git','-C',r'D:\VLA_QWEN\RevTrace','fetch',str(R/('source_'+V+'.bundle')),'HEAD:refs/archive/revtrace/context-analysis/'+commit],check=True)
D=R/('cpu_'+V);D.mkdir();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
environment=dict(python=sys.version,platform=platform.platform(),pytest=importlib.metadata.version('pytest'))
put(D/'ENVIRONMENT.json',environment)
cmd=[sys.executable,'-B','-m','pytest','-c',str(S/'pytest.ini'),'-p','no:cacheprovider','--rootdir',str(S),'--confcutdir',str(S),'--basetemp',str(D/'tmp'),'--junitxml',str(D/'results.xml'),str(S/'test_analysis.py'),'-q']
if (S/'test_context_probe.py').exists():cmd.append(str(S/'test_context_probe.py'))
if (S/'test_context_audit.py').exists():cmd.append(str(S/'test_context_audit.py'))
if (S/'test_native_prompt.py').exists():cmd.append(str(S/'test_native_prompt.py'))
if (S/'test_anomaly_merge.py').exists():cmd.append(str(S/'test_anomaly_merge.py'))
if (S/'test_wait_closure.py').exists():cmd.append(str(S/'test_wait_closure.py'))
put(D/'FREEZE.json',dict(experiment_id='REVTRACE-CONTEXT-ANALYSIS-CPU-'+V.upper(),source_commit=commit,source_manifest_sha256=sha(R/('SOURCE_'+V+'.json')),environment_sha256=sha(D/'ENVIRONMENT.json'),argv=cmd,raw_result_location=str(D/'pytest.log'),aggregate_summary_location=str(D/'results.xml'),gate_decision_location=str(D/'GATE.json'),GPU_calls=0))
with (D/'pytest.log').open('x') as f:r=subprocess.run(cmd,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT)
put(D/'GATE.json',dict(gate='PASS' if r.returncode==0 else 'FAIL_PRESERVED',source_commit=commit,returncode=r.returncode,GPU_calls=0))
print(json.dumps(dict(source_commit=commit,returncode=r.returncode)));print((D/'pytest.log').read_text()[-3500:]);raise SystemExit(r.returncode)
