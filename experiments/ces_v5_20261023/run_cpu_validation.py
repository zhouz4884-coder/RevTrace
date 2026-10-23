"""Record the complete scoped CPU regression and mathematical audit."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time

W=Path(__file__).resolve().parent
S=W/'runtime'
parser=argparse.ArgumentParser();parser.add_argument('--version',default='v1');args=parser.parse_args()
D=W/('cpu_validation_'+args.version)
assert not D.exists()
D.mkdir()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join(str(p) for p in [S/'src',S/'scripts',S/'tests',W]))
scope=['test_ces.py','test_ces_v5_policy.py','test_ces_v5_integration.py',
 'test_online_admission.py','test_dgft.py','test_live_qwen.py','test_properties_abc.py',
 'test_continuity_proof.py','test_consumer_bound_identity.py','test_localagreement_display.py',
 'test_certified_display.py','test_durable_journal.py','test_standard_async.py',
 'test_lazy_reconciliation.py','test_model_lifecycle_telemetry.py','test_result_delivery_hold.py',
 'test_execution_context_fault_seam.py','test_diagnostic_switch.py','test_row_progress_integration.py',
 'test_row_executor_protocol.py','test_row_lifecycle_transport.py','test_row_worker_provenance.py',
 'test_complete_row_stream.py']
commands=[('runtime_regression',[sys.executable,'-m','pytest',*[str(S/'tests'/n) for n in scope],
 '-q','--tb=short','--basetemp',str(W/('cpu_tmp_full_'+args.version)),'-o','pythonpath='+str(S/'src')]),
 ('independent_math_accounting',[sys.executable,'-m','pytest',*[str(W/n) for n in
 ['test_cpu_planning_oracle.py','test_deadline_backprop.py','test_cpu_repairs.py','test_v5_analysis.py','test_vectorized_plan_metrics.py']],
 '-q','--tb=short','--basetemp',str(W/('cpu_tmp_math_'+args.version)),'-o','pythonpath='+str(S/'src')]),
 ('same_input_repaired_counterexamples',[sys.executable,str(W/'math_counterexamples_v5.py'),'--expect','repaired']),
 ('finite_model_oracle',[sys.executable,str(W/'cpu_planning_oracle.py')]),
 ('vectorization_parity',[sys.executable,str(W/'test_vectorized_plan_metrics.py')])]
rows=[]
for name,cmd in commands:
    started=time.perf_counter()
    r=subprocess.run(cmd,cwd=S,env=env,capture_output=True,text=True)
    (D/(name+'.log')).write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
    rows.append({'name':name,'returncode':r.returncode,'seconds':time.perf_counter()-started,'argv':cmd})
    print(name,r.returncode,r.stdout[-1500:],r.stderr[-500:],flush=True)
result={'status':'PASS' if all(r['returncode']==0 for r in rows) else 'FAIL',
 'evidence_tier':'CPU_regression_and_synthetic_mathematical_oracle_only','GPU_calls':0,
 'runs':rows,'source_sha256':{p.relative_to(S).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
  for p in S.rglob('*.py') if '.git' not in p.parts},
 'research_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in W.glob('*.py')}}
(D/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
raise SystemExit(0 if result['status']=='PASS' else 1)
