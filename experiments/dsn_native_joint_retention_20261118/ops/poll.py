"""Read the same generation-bound owned process and bounded progress artifacts."""
from pathlib import Path
import argparse,importlib.util,json,time
E=Path(__file__).resolve().parents[1];R=E.parents[1];p=argparse.ArgumentParser();p.add_argument('phase');a=p.parse_args();local=E/'launch_ops'/a.phase;handle=json.loads((local/'HANDLE.json').read_bytes())
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
script='C='+repr(handle)+'\n'+r'''
from pathlib import Path
import datetime,json,subprocess
p=Path('/proc')/str(C['pid']);owned=False;state=None
try:
 s=(p/'stat').read_text().rsplit(')',1)[1].split();owned=int(s[19])==C['start_ticks'];state=s[0]if owned else'PID_REUSED'
except FileNotFoundError:state='EXITED'
out=Path(C['out']);result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),process=dict(pid=C['pid'],start_ticks=C['start_ticks'],generation_matches=owned,state=state,active=owned and state not in('Z','X')),files={})
for name in ['GATE.json','SUMMARY.json','PROGRESS.json','MODEL_READY.json']:
 q=out/name
 if q.exists():
  x=json.loads(q.read_bytes());result['files'][name]={k:v for k,v in x.items()if k in('status','completed_trials','planned_trials','expected_sources','completed_sources','expected_original_steps','original_continuous_steps','ledger','completed','planned','current','condition','source_commit','actual_NN_source_commit','model_load_seconds','full_load_warmup_seconds','original_FP32','actual_parameter_dtypes')}
result['CUDA_owners']=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True).strip()
log=Path(C['log']);result['log_tail']=log.read_bytes()[-2200:].decode(errors='replace')if log.exists()else''
result['output_exists']=out.exists()
progress=out/'PROGRESS.json'
if progress.exists():
 current=json.loads(progress.read_bytes()).get('current');root=out/'cells'/str(current);result['current_trial']={'cell_id':current,'origin_exists':(root/'ORIGIN.json').exists(),'end_exists':(root/'SERVICE_END.json').exists()}
 if(root/'GATE.json').exists():result['current_trial']['gate']=json.loads((root/'GATE.json').read_bytes())
 q=out/'logs'/(str(current)+'.log')
 if q.exists():result['current_trial']['log_tail']=q.read_bytes()[-1000:].decode(errors='replace')
print(json.dumps(result))
'''
with m.Remote()as c:raw=c.python(script,timeout=30)
q=local/('POLL_'+str(time.time_ns())+'.json');q.write_bytes(raw+b'\n');print(raw.decode())
