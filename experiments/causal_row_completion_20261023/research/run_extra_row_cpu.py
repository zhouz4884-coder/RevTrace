"""Serial follow-on CPU audit only; no model or rescue execution."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/row_completion_20261023'
assert not (O/'EXTRA_ROW_CPU_RUN_v1.json').exists()
meta=json.loads((P/'EXTRA_ANALYSIS_SOURCE_v1.json').read_text())
for n,sha in meta['files'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==sha
def save(n,x):(O/n).write_text(json.dumps(x,indent=2)+'\n')
save('EXTRA_ROW_CPU_RUN_v1.json',{'status':'WAIT_EXISTING_CPU_PIPELINE','code_commit':meta['code_commit'],'new_model_calls':0})
try:
    while not (O/'POST_ROW_CPU_SUMMARY_v1.json').exists():
        if (O/'POST_ROW_CPU_STOP_v1.json').exists():raise RuntimeError('previous CPU analysis stopped; do not silently bypass')
        time.sleep(15)
    assert json.loads((O/'POST_ROW_CPU_SUMMARY_v1.json').read_text())['status']=='COMPLETE_CPU_RESTAGING_TIMING_STATISTICS_AND_RAW_INDEX'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
    commands=[('OWNER_FAILCLOSED',[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',str(P/'test_row_owner_failclosed.py')]),
      ('PRIVATE_DECISION_FACTS',[sys.executable,'-B',str(P/'audit_private_blockers.py'),str(B)])]
    for name,cmd in commands:
        save('EXTRA_ROW_CPU_PROGRESS_v1.json',{'status':'RUNNING','stage':name,'new_model_calls':0})
        with (O/('EXTRA_ROW_CPU_'+name+'.log')).open('w') as log:q=subprocess.run(cmd,cwd=P,env=env,stdout=log,stderr=subprocess.STDOUT)
        assert q.returncode==0,'extra CPU audit failed: '+name
        print('EXTRA_CPU_COMPLETE',name,flush=True)
    save('EXTRA_ROW_CPU_SUMMARY_v1.json',{'status':'COMPLETE_EXTRA_OWNER_AND_ACTUAL_PRIVATE_DECISION_AUDITS','new_model_calls':0,
      'code_commit':meta['code_commit'],'Rescue_not_started':True,'final_union_raw_index_and_GitHub_delivery_still_required':True})
except BaseException as e:
    save('EXTRA_ROW_CPU_STOP_v1.json',{'error':repr(e),'new_model_calls':0,'raw_preserved':True});raise
