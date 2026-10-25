"""Frozen N5 controller. No inference output is used to select a workload."""
from pathlib import Path
import argparse,hashlib,json,os,signal,subprocess,sys,time

B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_dependability_20261025/n5_v3';O=B/'results/revtrace/dependability_20261025/n5_v3'
WEIGHTS={'model-00001-of-00002.safetensors':'a4cd1f1a04d90b757dc7f7dd26254e69a013b19e80efe590a83c6a3bde8608d6',
 'model-00002-of-00002.safetensors':'6e0b9d9e09e2e0238e7ef3cc8a484ab387e91b90f1900bedf88bc92d7929ccfc'}
METHODS=['fine_fair','dgft_original','standard_fair','queue_expiry','cde_age','cde_full','standard_cde']
WORKLOADS=[('nonsaturated',4,[0.]*4),('near_probe',8,[.25*i for i in range(8)]),('burst',16,[0.]*16),
 ('finite_overload',32,[.25*i for i in range(32)]),('return_low',24,[0.]*4+[20.]*16+[60.]*4),
 ('fault_recovery',8,[.25*i for i in range(8)])]
def read(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,d):
 t=p.with_name(p.name+'.partial');t.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n');t.replace(p)
def alive(h):
 p=Path('/proc')/str(h['pid'])
 if not p.exists():return False
 r=p.joinpath('stat').read_text().rsplit(')',1)[1].split()
 return r[19]==str(h.get('start_ticks',h.get('linux_start_ticks'))) and r[0]!='Z'
def idle():return not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
def source():
 m=read(P/'runtime/SOURCE_MANIFEST.json')
 for r in m['files']:assert sha(P/'runtime'/r['path'])==r['sha256'],r['path']
 return m
def rows(path):
 if not path.exists():return []
 data=path.read_text(errors='strict').splitlines();out=[]
 for i,line in enumerate(data):
  try:out.append(json.loads(line))
  except json.JSONDecodeError:
   assert i==len(data)-1,'corruption before active trace tail'
 return out
def kill_group(proc,h,C):
 assert alive(h) and os.getpgid(proc.pid)==proc.pid
 handles=read(C/'OWNED_WORKER_HANDLES.json')
 for w in handles:
  if alive(w):assert os.getpgid(w['pid'])==proc.pid,'not this owned process group'
 at=time.perf_counter();os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=20)
 deadline=time.perf_counter()+30
 while any(alive(w) for w in handles) and time.perf_counter()<deadline:time.sleep(.1)
 assert not any(alive(w) for w in handles)
 return dict(kill_perf=at,returncode=proc.returncode,owned_workers=handles,workers_exited_or_zombie=True)
def launch(cmd,E,attempt):
 C=E/f'attempt{attempt}';log=(E/f'attempt{attempt}.log').open('xb')
 proc=subprocess.Popen(cmd,cwd=P/'runtime',stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 h=dict(pid=proc.pid,start_ticks=(Path('/proc')/str(proc.pid)/'stat').read_text().rsplit(')',1)[1].split()[19],
  cmdline_sha256=sha(Path('/proc')/str(proc.pid)/'cmdline'),launch_perf=time.perf_counter())
 save(E/f'OWNER_HANDLE_{attempt}.json',h);return proc,h,log,C
def command(E,c,m,manifest,attempt,fault):
 cmd=[sys.executable,'-u',str(P/'runtime/scripts/run_tc_live_qwen.py'),'--model',str(B/'models/Qwen3-ASR-1.7B'),
  '--manifest',str(manifest),'--output',str(E/f'attempt{attempt}'),'--code-commit',m['code_commit'],
  '--study-id','REVTRACE-N5-INDEPENDENT-20261026' if c['independent'] else 'REVTRACE-N5-RECOVERY-DEVELOPMENT-20261026',
  '--sessions',str(c['load']),'--proposal-gpus','0','--authority-gpus','1','--microbatch','16',
  '--max-new-tokens','256','--seed','20261026','--timeout','300','--result-delivery','row','--phase-n-instrumentation',
  '--journal-sync-mode','group_ready','--durable-journal-path',str(E/'canonical.wal'),
  '--envelope-config',str(E/'POLICY.json'),'--arrival-schedule',str(E/'ARRIVAL.json'),
  '--episode-context',str(E/'CONTEXT.json'),'--input-journal-path',str(E/'input.wal')]
 if fault:cmd+=['--receipt-trace']
 return cmd
def episode(E,c,m,manifest,PowerSampler):
 E.mkdir();fault=c['workload']=='fault_recovery'
 cfg=dict(method=c['method'],budget_audio_seconds=96,warning_age=4,critical_age=8,clear_age=2,
  display_slo=2,commit_slo=8,queue_threshold=8,reject_new_after_seconds=8,tick_seconds=.005,model_weight_sha256=WEIGHTS)
 save(E/'POLICY.json',cfg);save(E/'ARRIVAL.json',dict(offsets=c['offsets']))
 sampler=PowerSampler([0,1],interval=.2);sampler.start();began=time.perf_counter();proc=h=log=C=None
 try:
  cmd=command(E,c,m,manifest,0,fault);save(E/'COMMAND_0.json',dict(cell=c,argv=cmd))
  proc,h,log,C=launch(cmd,E,0)
  if fault:
   trigger=None;wait_until=time.perf_counter()+120
   while time.perf_counter()<wait_until:
    if proc.poll() is not None:raise RuntimeError('owner exited before frozen fault point')
    if (E/'CONTEXT.json').exists():
     origin=read(E/'CONTEXT.json')['origin_perf'];es=rows(C/'events.jsonl')
     trigger=next((e for e in es if e['kind']=='batch-dispatched' and e['role']=='authority' and
       next(x['t0_perf'] for x in es if x['kind']=='run-start')+e['time']>=origin+14),None)
     if trigger:break
     if time.perf_counter()>origin+22:raise RuntimeError('frozen Authority-dispatch fault point unavailable')
    time.sleep(.02)
   assert trigger is not None
   before_GPU=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True)
   killed=kill_group(proc,h,C);log.close();proc=None
   es=rows(C/'events.jsonl');killed.update(trigger=trigger,episode_origin_perf=origin,
    actual_fault_delay_after_original14=time.perf_counter()-origin-14,prekill_GPU_processes=before_GPU,
    server_input_ACKs=[e for e in es if e['kind']=='input-ack'],published_commits=[e for e in es if e['kind']=='commit'],
    clock_scope='process-group fault; both GPU workers cold restarted; original input deadlines retained')
   for name in ['input.wal','canonical.wal']:
    data=(E/name).read_bytes();copy=E/(name+'.pre-recovery');copy.write_bytes(data)
    killed[name+'_pre_recovery_sha256']=hashlib.sha256(data).hexdigest()
   save(E/'KILL.json',killed);assert idle(),'unexpected GPU occupancy after own group exit'
   cmd=command(E,c,m,manifest,1,True);save(E/'COMMAND_1.json',dict(cell=c,argv=cmd))
   proc,h,log,C=launch(cmd,E,1)
  rc=proc.wait(timeout=390);log.close();assert rc==0,'raw failure retained; no automatic rerun'
  r=read(C/'result.json');assert r['fine_window_accounting_complete']
  handles=read(C/'OWNED_WORKER_HANDLES.json');assert not any(alive(w) for w in handles)
  assert idle(),'own lease not drained or different task started'
  end=time.perf_counter();power=sampler.stop();raw_power=sampler.rows;sampler=None
  save(E/'EPISODE_POWER.json',dict(samples=raw_power,power_summary=power,outer_launch_perf=began,outer_end_perf=end,
   scope='observed GPU power only, includes killed work and cold reload; primary audit clips original episode window'))
  save(E/'RUN_COMPLETE_PENDING_AUDIT.json',dict(cell=c,owned_workers=handles,source=m['code_commit'],
   actual_episode_end_perf=end,fault_injected=fault,final_attempt=1 if fault else 0))
 except BaseException:
  if proc is not None and proc.poll() is None:
   if C is not None and (C/'OWNED_WORKER_HANDLES.json').exists():kill_group(proc,h,C)
   elif alive(h) and os.getpgid(proc.pid)==proc.pid:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=20)
  if log is not None:log.close()
  if sampler is not None:
   q=sampler.stop();save(E/'FAILED_POWER.json',dict(samples=sampler.rows,power_summary=q,all_failed_work_retained=True))
  raise

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['recovery_development','formal_normal','formal_fault'],required=True);a=ap.parse_args()
 assert idle();m=source()
 for name,value in WEIGHTS.items():assert sha(B/'models/Qwen3-ASR-1.7B'/name)==value
 sys.path.insert(0,str(P/'runtime/scripts/v100'));from run_v100_matrix import PowerSampler
 manifest=P/('DEVELOPMENT_MANIFEST.json' if a.stage=='recovery_development' else 'INDEPENDENT_MANIFEST_v1.json')
 if a.stage=='formal_fault':
  gate=read(O/'RECOVERY_DEVELOPMENT_INDEPENDENT_GATE.json');assert gate['decision']=='GO_SAFETY_ONLY'
  assert gate['runtime_commit']==m['code_commit']
 cells=[]
 if a.stage=='recovery_development':
  for method in ['fine_fair','cde_full']:
   _,load,offsets=WORKLOADS[-1];cells.append(dict(method=method,workload='fault_recovery',load=load,offsets=offsets,repeat=0,independent=False))
 else:
  ws=WORKLOADS[:-1] if a.stage=='formal_normal' else WORKLOADS[-1:]
  for repeat in range(3):
   for wi,(workload,load,offsets) in enumerate(ws):
    shift=(repeat+wi)%len(METHODS);ordered=METHODS[shift:]+METHODS[:shift]
    for method in ordered:cells.append(dict(method=method,workload=workload,load=load,offsets=offsets,repeat=repeat,independent=True))
 dest=O/a.stage;dest.mkdir(exist_ok=False)
 save(dest/'FREEZE.json',dict(cells=cells,expected=len(cells),runtime_commit=m['code_commit'],
  runtime_manifest_sha256=sha(P/'runtime/SOURCE_MANIFEST.json'),source_manifest_sha256=sha(manifest),
  protocol_sha256=sha(P/'N5_VALIDATION_PROTOCOL_v1.md'),controller_sha256=sha(Path(__file__)),model_weights=WEIGHTS,
  no_automatic_retry=True,fault_scope='process group, not host/power',PID=os.getpid()))
 done=[];active=None
 try:
  for c in cells:
   assert idle();source();active=f"{c['method']}-{c['workload']}-r{c['repeat']}"
   episode(dest/active,c,m,manifest,PowerSampler);done.append(active)
   save(dest/'PROGRESS.json',dict(status='RUNNING',completed=done,expected=len(cells)));print('COMPLETE',len(done),active,flush=True)
  for name,value in WEIGHTS.items():assert sha(B/'models/Qwen3-ASR-1.7B'/name)==value
  save(dest/'SUMMARY.json',dict(status='COMPLETE_REAL_GPU_PENDING_INDEPENDENT_AUDIT',completed=done,cells=len(done),expected=len(cells),GPU_queue_closed=True))
 except BaseException as e:
  save(dest/'STOP.json',dict(active=active,completed=done,error=repr(e),no_automatic_retry=True,all_raw_retained=True));raise
if __name__=='__main__':main()
