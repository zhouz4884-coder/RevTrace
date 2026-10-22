"""One post-serving CPU pipeline only. It never starts a GPU or a rescue job."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/row_completion_20261023'
assert not (O/'POST_ROW_CPU_RUN_v1.json').exists()
meta=json.loads((P/'POST_ANALYSIS_SOURCE_v1.json').read_text())
for name,sha in meta['files'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==sha,name
def save(name,x):(O/name).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
save('POST_ROW_CPU_RUN_v1.json',{'code_commit':meta['code_commit'],'source_files':meta['files'],
 'never_starts_GPU_or_Rescue':True,'formal_expected':150,'status':'WAIT_FORMAL_TERMINAL'})
try:
    while not (O/'FORMAL_ROW_SUMMARY_v1.json').exists():
        if (O/'STOP_FORMAL_ROW_v1.json').exists():raise RuntimeError('formal matrix STOP; preserve partial scope, do not run complete-matrix inference')
        time.sleep(15)
    assert json.loads((O/'FORMAL_ROW_SUMMARY_v1.json').read_text())['status']=='COMPLETE_ALL150_INDEPENDENT_AUDITS_PASS'
    pid=json.loads((O/'FORMAL_ROW_PID_v1.json').read_text())['pid']
    while (Path('/proc')/str(pid)/'cmdline').exists():
        cmd=(Path('/proc')/str(pid)/'cmdline').read_bytes()
        if b'run_formal_row_v1.py' not in cmd:break
        time.sleep(.2)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false',
      PYTHONPATH=str(P)+':'+str(B/'projects/revtrace_online_admission_20261022'))
    commands=[('CPU_STATISTIC_TESTS',[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',str(P/'test_row_stats_core.py'),str(P/'test_row_timing_core.py')]),
      ('CORE_INPUT_RESTAGING',[sys.executable,'-B',str(P/'replay_row_processor_inputs.py'),str(B),'formal_row_v1']),
      ('VALIDATION_INPUT_RESTAGING',[sys.executable,'-B',str(P/'replay_row_processor_inputs.py'),str(B),'validation_row_v1']),
      ('ACTUAL_CLOCKS_COSTS',[sys.executable,'-B',str(P/'analyze_row_timing.py'),str(B)]),
      ('FIXED_STATISTICS',[sys.executable,'-B',str(P/'summarize_row_formal.py'),str(B)]),
      ('CLOSED_RAW_HASH_INDEX',[sys.executable,'-B',str(P/'index_closed_row_evidence.py'),str(B)])]
    completed=[]
    for name,cmd in commands:
        save('POST_ROW_CPU_PROGRESS_v1.json',{'status':'RUNNING','stage':name,'completed':completed,'new_model_calls':0})
        with (O/('POST_ROW_CPU_'+name+'.log')).open('w') as log:q=subprocess.run(cmd,cwd=P,env=env,stdout=log,stderr=subprocess.STDOUT)
        assert q.returncode==0,'postanalysis step failed: '+name
        completed.append(name);print('POST_CPU_COMPLETE',name,flush=True)
    save('POST_ROW_CPU_SUMMARY_v1.json',{'status':'COMPLETE_CPU_RESTAGING_TIMING_STATISTICS_AND_RAW_INDEX','completed':completed,
       'source_code_commit':meta['code_commit'],'new_model_calls':0,'Rescue_not_started':True,'GitHub_final_delivery_and_decisions_still_required':True})
except BaseException as e:
    save('POST_ROW_CPU_STOP_v1.json',{'error':repr(e),'raw_retained':True,'no_silent_retry_or_GPU_restart':True});raise
