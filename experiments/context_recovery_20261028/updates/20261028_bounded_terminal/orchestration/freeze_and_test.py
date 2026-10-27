"""Freeze the exact research source, then run a recorded CPU-only gate."""
from pathlib import Path
import gzip,hashlib,importlib.metadata,json,os,platform,subprocess,sys,time
S=Path(r'D:\VLA_QWEN\RevTrace\.execution\lp1_runtime')
O=Path(r'D:\VLA_QWEN\RevTrace\experiments\input_freeze_20261027')
tag=sys.argv[1]

def git(*a,raw=False):
    r=subprocess.check_output(['git','-C',str(S),*a],stderr=subprocess.PIPE)
    return r if raw else r.decode().strip()

def put(p,x):
    if p.exists():raise FileExistsError(p)
    p.write_text(json.dumps(x,indent=2)+'\n')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

changed=['FREEZE_BOUNDARY_PROTOCOL.md','wait_pilot_controller.py','pytest.ini',
    'runtime/scripts/run_tc_live_qwen.py','runtime/scripts/tc_live_worker.py','runtime/scripts/whisper_kernel_worker.py',
    'runtime/src/revtrace/certified_display.py','runtime/src/revtrace/certified_envelope.py','runtime/src/revtrace/live_qwen.py',
    'runtime/src/revtrace/dispatch_wait.py','runtime/src/revtrace/recovery_profile.py',
    'runtime/tests/test_dispatch_wait.py','runtime/tests/test_dispatch_wait_integration.py','runtime/tests/test_recovery_profile.py']
extra=['runtime/src/revtrace/startup_overlap.py','runtime/scripts/prepare_render_descriptor.py',
       'runtime/tests/test_startup_overlap.py','runtime/tests/test_dispatch_wait_real_busy.py']
extra += ['runtime/src/revtrace/recovery_fault.py','runtime/tests/test_conditional_wait_eta.py','runtime/tests/test_wait_prior_bank.py',
          'paired_recovery_controller.py','paired_recovery_audit.py','test_paired_recovery.py','RECOVERY_PAIR_PROTOCOL.md']
extra += ['paid_wait_operator.py','test_paid_wait_operator.py']
extra += ['NATIVE_ACCOUNTING_REPAIR.md','runtime/src/revtrace/whisper_adapter.py','runtime/tests/test_whisper_capacity.py']
changed += [p for p in extra if (S/p).exists()]
native=['tasks.py','native_store.py','native_workflow.py','actual_provider.py','revtrace_adapter.py','independent_checker.py','independent_codec.py','compare_trajectories.py','test_native.py','pinned-requirements.txt','cpu_native_config.json','INTEGRATION.md']
native += ['pilot_controller.py','pilot_plan.py','native_power.py','test_pilot.py','PILOT_CONFIG.json','PILOT_PROTOCOL.md']
native += ['numeric_probe.py']
changed += ['native_lifecycle/'+p for p in native if (S/'native_lifecycle'/p).exists()]
git('add','--',*changed)
git('-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check')
if git('diff','--cached','--name-only'):
    git('-c','user.name=Research Artifact','-c','user.email=artifact@example.invalid',
        'commit','-m','Implement bounded pre-freeze waits and trusted startup profiling '+tag)
commit=git('rev-parse','HEAD')
if git('status','--porcelain'):raise RuntimeError('source must be clean before testing/freezing')
files=[dict(path=p,bytes=(S/p).stat().st_size,sha256=sha(S/p)) for p in git('ls-files').splitlines()]
manifest=dict(code_commit=commit,baseline='7c176556592c2a4fad436056b8b96be52cac9ea4',files=files,
              scope='development source; measurements require their own actual environment and config')
put(O/('SOURCE_'+tag+'.json'),manifest)
archive=O/('source_'+tag+'.tar.gz')
if archive.exists():raise FileExistsError(archive)
archive.write_bytes(gzip.compress(git('archive','--format=tar','HEAD',raw=True),mtime=0))
git('bundle','create',str(O/('source_'+tag+'.bundle')),'HEAD')
testnames=['test_dispatch_wait','test_dispatch_wait_integration','test_recovery_profile','test_live_qwen',
           'test_durable_journal','test_certified_display','test_certified_envelope','test_composed_kernel',
           'test_properties_abc','test_standard_async','test_row_lifecycle_transport','test_complete_row_stream',
           'test_consumer_bound_identity','test_envelope_failure_controls']
testnames += [n for n in ['test_startup_overlap','test_dispatch_wait_real_busy'] if (S/'runtime/tests'/(n+'.py')).exists()]
testnames += [n for n in ['test_conditional_wait_eta','test_wait_prior_bank'] if (S/'runtime/tests'/(n+'.py')).exists()]
testnames += [n for n in ['test_whisper_capacity'] if (S/'runtime/tests'/(n+'.py')).exists()]
paths=[str(S/'runtime/tests'/(n+'.py')) for n in testnames]
paths += [str(S/n) for n in ['test_content_fault.py','test_audit_contracts.py','test_historical_display.py',
                             'test_kernel_cow.py','test_prefix_plan.py']]
if (S/'native_lifecycle/test_native.py').exists():paths.append(str(S/'native_lifecycle/test_native.py'))
if (S/'native_lifecycle/test_pilot.py').exists():paths.append(str(S/'native_lifecycle/test_pilot.py'))
if (S/'test_paired_recovery.py').exists():paths.append(str(S/'test_paired_recovery.py'))
if (S/'test_paid_wait_operator.py').exists():paths.append(str(S/'test_paid_wait_operator.py'))
out=O/('cpu_'+tag);out.mkdir()
env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
env['PYTHONPATH']=os.pathsep.join([str(S/'runtime/src'),str(S/'runtime/scripts'),str(S),str(S/'native_lifecycle')])
cmd=[sys.executable,'-B','-m','pytest','-c',str(S/'pytest.ini'),'-p','no:cacheprovider','--rootdir',str(S),'--confcutdir',str(S),
     '--basetemp',str(out/'tmp'),'--junitxml',str(out/'results.xml'),'-q',*paths]
environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
    packages={x:importlib.metadata.version(x) for x in ['pytest','numpy']})
put(out/'ENVIRONMENT.json',environment)
put(out/'FREEZE.json',dict(experiment_id='REVTRACE-FREEZE-CPU-'+tag,code_commit=commit,
    source_manifest_sha256=sha(O/('SOURCE_'+tag+'.json')),environment_sha256=sha(out/'ENVIRONMENT.json'),
    argv=cmd,raw_result_location=str(out/'pytest.log'),aggregate_summary_location=str(out/'results.xml'),
    gate_decision_location=str(out/'GATE.json'),evidence_tier='CPU_TESTS_NOT_GPU'))
with (out/'pytest.log').open('x') as f:
    r=subprocess.run(cmd,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT)
put(out/'GATE.json',dict(gate='PASS' if r.returncode==0 else 'FAIL_PRESERVED',code_commit=commit,
                       returncode=r.returncode,source_tar_sha256=sha(archive),gpu_started=False))
print(json.dumps(dict(commit=commit,source_files=len(files),CPU_returncode=r.returncode,log=str(out/'pytest.log'))))
print((out/'pytest.log').read_text(encoding='utf8',errors='replace')[-7000:])
raise SystemExit(r.returncode)
