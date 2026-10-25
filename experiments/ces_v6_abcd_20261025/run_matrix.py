"""Bounded sequential serving matrix. Explicit plans, no automatic retuning."""
from pathlib import Path
import argparse,csv,hashlib,json,os,subprocess,sys,time
P=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,x,replace=False):
 if p.exists() and not replace:raise FileExistsError(p)
 p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def idle():return not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
def name(c):return f"{c['pool']}-{c['arrival']}-{c['traffic']}-{c['label']}-r{c['repeat']}"
def released(C):
 for h in read(C/'OWNED_WORKER_HANDLES.json'):
  p=Path('/proc')/str(h['pid'])
  if p.exists():assert p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]!=str(h['linux_start_ticks']),'original Worker still present'
def execute(base,stage,plan):
 O=base/'results/revtrace/ces_v6_abcd_20261025';cells=plan['cells'];assert len({name(c) for c in cells})==len(cells)
 assert not (O/(stage+'_GPU_STARTED.json')).exists()
 assert idle(),'GPU occupied; do not terminate another task'
 save(O/(stage+'_FREEZE.json'),plan);save(O/(stage+'_GPU_STARTED.json'),{'pid':os.getpid(),'time_unix':time.time(),'cells':len(cells),'plan_sha256':sha(a.plan)})
 done=[];groups={};active=None
 try:
  for c in cells:
   assert idle(),'unexpected GPU ownership at cell boundary'
   source=base/plan['sources'][c['source']];manifest=read(source/'SOURCE_MANIFEST.json')
   source.resolve().relative_to((base/'projects').resolve())
   for r in manifest['files']:assert sha(source/r['path'])==r['sha256'],r['path']
   data=base/c['manifest'];cal=base/c['calibration'];assert sha(data)==c['manifest_sha256'] and sha(cal)==c['calibration_sha256']
   active=name(c);folder=O/stage;folder.mkdir(exist_ok=True);(folder/'journals').mkdir(exist_ok=True)
   C=folder/active;assert not C.exists();closed=P/'configs'/c['closed'];options=P/'configs'/c['options'] if c.get('options') else None
   cmd=[sys.executable,'-u',str(source/'scripts/run_tc_live_qwen.py'),'--model',str(base/'models/Qwen3-ASR-1.7B'),
    '--manifest',str(data),'--output',str(C),'--code-commit',manifest['code_commit'],'--study-id','REVTRACE-CES-V6-ABCD-20261025',
    '--sessions',str(c.get('sessions',16)),'--arrival',c['arrival'],'--seed',str(c['seed']),'--trusted-text-binding',
    '--display-protocol','canonical-snapshot-v1','--publish-canonical-display','--consumer-policy','two_lane',
    '--retain-verified-private-prefix','--phase-n-instrumentation','--capture-model-inputs','--ces-method',c['method'],
    '--ces-traffic',c['traffic'],'--ces-calibration',str(cal),'--ces-closed-config',str(closed),
    '--ces-proposer-policy','ready','--online-donors',str(base/'projects/revtrace_online_admission_20261022/DONORS.json'),
    '--online-fallback-layout',c.get('fallback_layout','selective'),'--durable-journal-path',str(folder/'journals'/(active+'.wal')),
    '--journal-sync-mode','group_ready','--result-delivery','row']
   if options:cmd+=['--v6-config',str(options)]
   save(folder/(active+'.COMMAND.json'),{'cell':c,'argv':cmd,'source_commit':manifest['code_commit'],'source_manifest_sha256':sha(source/'SOURCE_MANIFEST.json')})
   with (folder/(active+'.log')).open('xb') as f:subprocess.run(cmd,cwd=source,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
   result=read(C/'result.json');assert result['fine_window_accounting_complete'];released(C)
   done.append(active);groups.setdefault(c['source'],[]).append(active)
   save(O/(stage+'_PROGRESS.json'),{'status':'RUNNING','stage':stage,'completed':done,'expected':len(cells)},True)
   print('COMPLETE',stage,len(done),active,flush=True)
  all_metrics={};summaries=[]
  for source,names in groups.items():
   expected=O/(stage+'_'+source+'_EXPECTED.json');save(expected,{'cells':names})
   output=O/(stage+'_'+source+'_audit')
   cmd=[sys.executable,str(P/'audit_v6.py'),'--root',str(O),'--stage',stage,'--source',str(base/plan['sources'][source]),'--output',str(output),
    '--model',str(base/'models/Qwen3-ASR-1.7B'),'--expected-cells',str(expected)]
   refs=sorted({c['manifest'] for c in cells})
   for ref in refs:cmd+=['--references',str(base/ref)]
   with (O/(stage+'_'+source+'_audit.log')).open('xb') as f:subprocess.run(cmd,cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
   s=read(output/'SUMMARY.json');assert not s['failures'] and s['cells']==len(names);summaries.append(s)
   for filename in ['SERVICE_CELLS.csv','COMMON_FRONTIERS.csv','SOURCE_QUALITY.csv','PHYSICAL_COSTS.csv']:
    with (output/filename).open(newline='') as f:all_metrics.setdefault(filename,[]).extend(csv.DictReader(f))
  audit=O/(stage+'_audit');audit.mkdir()
  for n,rows in all_metrics.items():
   with (audit/n).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  save(audit/'SUMMARY.json',{'status':'PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT','cells':len(done),'expected_cells':len(cells),'failures':[],
   'actual_model_calls':sum(s['actual_model_calls'] for s in summaries),'group_audits':[str(O/(stage+'_'+source+'_audit')) for source in groups],
   'source_scope':'development reused source' if stage!='D_heldout' else 'source-audited new speaker and audio confirmation'})
  save(O/(stage+'_SUMMARY.json'),{'status':'COMPLETE_GPU_MATRIX_AND_SAFETY_AUDIT','cells':len(done),'completed':done,
   'GPU_queue_closed':True,'source_groups':list(groups),'same_source_repeats_are_not_independent_audio':True})
 except BaseException as e:
  save(O/(stage+'_STOP.json'),{'error':repr(e),'active':active,'completed':done,'all_raw_retained':True,'no_silent_retry':True});raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--stage',required=True);p.add_argument('--plan',type=Path,required=True);a=p.parse_args()
 execute(a.base,a.stage,read(a.plan))
