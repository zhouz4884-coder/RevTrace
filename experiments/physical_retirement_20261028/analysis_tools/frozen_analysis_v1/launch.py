"""After all GPU cells end, run the three independent trace analyses serially."""
import hashlib,json,os,platform,subprocess,sys,time
from pathlib import Path
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_physical_retirement_20261028';O=B/'results/revtrace/physical_retirement_20261028'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
assert json.loads((O/'confirmation_controller_v3/GATE.json').read_text())['gate']=='PASS_ALL_FROZEN_EXECUTION_CELLS'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
M=P/'CONFIRMATION_PLAN_v3_FROZEN.json';assert sha(M)=='8a62b6849842aee0baa432f83c260b11686e328746b3b7f5b3831f5bc652b9ec'
AP=Path(__file__).resolve().parent
AM=P/'ANALYSIS_SOURCE_v1.json';am=json.loads(AM.read_text());analysis_commit=am['code_commit']
assert subprocess.check_output(['git','-C',str(AP),'rev-parse','--show-toplevel'],text=True).strip()==str(AP)
assert subprocess.check_output(['git','-C',str(AP),'rev-parse','HEAD'],text=True).strip()==analysis_commit
assert not subprocess.check_output(['git','-C',str(AP),'status','--porcelain','--untracked-files=all'],text=True).strip()
tracked=set(subprocess.check_output(['git','-C',str(AP),'ls-files'],text=True).splitlines())
assert tracked=={r['path'] for r in am['files']}
for r in am['files']:assert (AP/r['path']).stat().st_size==r['bytes'] and sha(AP/r['path'])==r['sha256']
D=O/'confirmation_v3_analysis_v1';assert not D.exists();D.mkdir()
py=str(B/'envs/revbatch-cu128/bin/python');jobs=[]
specs=[('aggregate','aggregate_service_v4.py','168bf74f14a8b04c8eeb194ad18e39093ea58c59f74892ccac538ca35bd8d242','SUMMARY.json','accepted_cells'),
 ('usefulness','canonical_usefulness_v1.py','72676a76fcebdabb0218d0e354b7181db04e27b6c2b53196fde034d5f4acb2c1','SUMMARY.json','recounted_cells'),
 ('opportunities','interaction_opportunities_v1.py','946b44e1ffca0226ff52ce91659b5a96e13f3dfd77bd21d1dc5f9d19692e90c0','ANALYSIS_RECORD.json','cells_recounted')]
for name,filename,digest,summary,count_key in specs:
 script=AP/filename;assert sha(script)==digest
 jobs.append(dict(name=name,script=str(script),script_sha256=digest,argv=[py,'-B',str(script),'--plan',str(M),'--output',str(D/name)],
  output=str(D/name),summary=str(D/name/summary),count_key=count_key,expected_count=110))
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(B/'tmp/physical_retirement_20261028'))
observed=json.loads(subprocess.check_output([py,'-B','-c','import json,platform,sys; print(json.dumps(dict(python=sys.version,executable=sys.executable,platform=platform.platform(),hostname=platform.node())))'],text=True))
put(D/'ENVIRONMENT.json',dict(observed,new_GPU_calls=0))
driver='''import hashlib,json,subprocess,time,traceback
from pathlib import Path
D=Path(REPLACE_D)
def put(p,v,replace=False):
 if replace:
  q=p.with_name(p.name+'.tmp')
  with q.open('x') as f:json.dump(v,f,indent=2);f.write('\\n')
  q.replace(p)
 else:
  with p.open('x') as f:json.dump(v,f,indent=2);f.write('\\n')
cfg=json.loads((D/'CONFIG.json').read_text());results=[]
for job in cfg['jobs']:
 try:
  assert hashlib.sha256(Path(job['script']).read_bytes()).hexdigest()==job['script_sha256']
  assert not Path(job['output']).exists()
  put(D/'PROGRESS.json',dict(status='RUNNING',completed=len(results),total=3,current=job['name']),True)
  with (D/(job['name']+'.log')).open('x') as stream:
   run=subprocess.run(job['argv'],stdout=stream,stderr=subprocess.STDOUT)
  result=dict(name=job['name'],returncode=run.returncode,accepted=False,output=job['output'])
  if run.returncode==0:
   summary=json.loads(Path(job['summary']).read_text());result['summary']=summary if job['name']!='opportunities' else {k:v for k,v in summary.items() if k not in ['inputs','command','environment']}
   result['accepted']=summary.get(job['count_key'])==job['expected_count']
   if job['name']=='usefulness':result['accepted'] &= summary.get('formally_source_revalidated_cells')==110
  results.append(result)
 except BaseException:
  results.append(dict(name=job['name'],accepted=False,error=traceback.format_exc()))
accepted=all(x['accepted'] for x in results)
put(D/'SUMMARY.json',dict(status='COMPLETE_INDEPENDENT_ANALYSES' if accepted else 'INCOMPLETE_ANALYSIS_REPAIR_NEEDED',results=results,new_GPU_calls=0,interpretation='Scientific effects, uncertainty and competitiveness require reading the tables.'))
put(D/'GATE.json',dict(gate='PASS_ALL_110_CELLS_IN_THREE_INDEPENDENT_RECOUNTS' if accepted else 'FAIL_ANALYSIS_PRESERVED',new_GPU_calls=0))
put(D/'PROGRESS.json',dict(status='COMPLETE' if accepted else 'FAILED_PRESERVED',completed=3,total=3),True)
'''.replace('REPLACE_D',repr(str(D)))
put(D/'CONFIG.json',dict(experiment_id='REVTRACE-H3-V3-INDEPENDENT-ANALYSES-v1',actual_GPU_execution_commit='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf',
 plan=str(M),plan_sha256=sha(M),jobs=jobs,controller_source=driver,controller_sha256=hashlib.sha256(driver.encode()).hexdigest(),
 execution='serial CPU analyses after neural workers have exited; bounded memory and no new inference'))
put(D/'RUN_RECORD.json',dict(experiment_id='REVTRACE-H3-V3-INDEPENDENT-ANALYSES-v1',code_commit=analysis_commit,analysis_source_manifest=str(AM),analysis_source_manifest_sha256=sha(AM),actual_GPU_execution_commit='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf',
 code_commit_scope='complete clean independent analysis source; measured neural execution commit separately preserved',
 frozen_config=str(D/'CONFIG.json'),frozen_config_sha256=sha(D/'CONFIG.json'),environment_record=str(D/'ENVIRONMENT.json'),environment_record_sha256=sha(D/'ENVIRONMENT.json'),
 raw_result_location=str(O/'confirmation_v3'),aggregate_summary_location=str(D/'SUMMARY.json'),gate_decision_location=str(D/'GATE.json')))
logpath=D/'controller.log';handle=O/'CONFIRMATION_ANALYSIS_v3_HANDLE.json';assert not handle.exists()
with logpath.open('x') as log:child=subprocess.Popen([py,'-B','-u','-c',driver],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc',str(child.pid));h=dict(experiment_id='REVTRACE-H3-V3-INDEPENDENT-ANALYSES-v1',pid=child.pid,
 linux_start_ticks=(proc/'stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=sha(proc/'cmdline'),launched_unix=time.time(),result=str(D),log=str(logpath))
put(handle,h);print(json.dumps(h,indent=2))
