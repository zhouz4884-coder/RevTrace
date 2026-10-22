"""One exact-owner SIGKILL after durable early commit; cold resume, no adoption."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys,time

def main():
 B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/row_completion_20261023'
 S=P/'source_row_sdk_v2';D=O/'row_gpu_crash_v1';assert not D.exists()
 assert json.loads((O/'row_live_pilot_v1/SUMMARY.json').read_text())['status']=='COMPLETE_ALL10_LIVE_PILOTS_INDEPENDENT_AUDIT_PASS'
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
 D.mkdir();sys.path[:0]=[str(S/'src'),str(S/'scripts'),str(S/'scripts/v100')]
 from audit_dsn_journal import audit as audit_wal
 from audit_tc_live_qwen import audit as audit_certificates
 from run_v100_matrix import PowerSampler
 def read(p):return json.loads(p.read_text())
 def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
 meta=read(S/'SOURCE_MANIFEST.json')
 for r in meta['files']:assert hashlib.sha256((S/r['path']).read_bytes()).hexdigest()==r['sha256']
 control=read(P/'PHASE_CONTROL_SOURCE_v1.json')
 assert control['files']['run_row_gpu_crash.py']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 wal=D/'state.wal';initial=D/'initial';resumed=D/'resumed'
 common=[sys.executable,'-u',str(S/'scripts/run_tc_live_qwen.py'),'--model',str(B/'models/Qwen3-ASR-1.7B'),
   '--manifest',str(B/'datasets/revtrace/phaseD_20261021/manifest.json'),'--code-commit',meta['code_commit'],
   '--study-id','REVTRACE-ROW-GPU-PROCESS-CRASH-v1','--sessions','16','--arrival','sync','--seed','20261023',
   '--trusted-text-binding','--display-protocol','canonical-snapshot-v1','--publish-canonical-display',
   '--consumer-policy','two_lane','--retain-verified-private-prefix','--phase-n-instrumentation','--capture-model-inputs',
   '--online-study-method','dgft','--online-traffic','clean','--online-donors',str(B/'projects/revtrace_online_admission_20261022/DONORS.json'),
   '--online-fallback-layout','selective','--durable-journal-path',str(wal),'--journal-sync-mode','group_ready',
   '--result-delivery','row','--receipt-trace']
 save(D/'RUN.json',{'experiment_id':'REVTRACE-ROW-GPU-SIGKILL-v1','runtime_code_commit':meta['code_commit'],
    'controller_code_commit':control['code_commit'],
    'controller_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'argv_common':common,
    'scope':'one real GPU owner-process crash; no host-power-loss or warm-worker adoption claim'})
 sampler=PowerSampler([0,1],interval=.2);sampler.start();owner=None;handles=[]
 def proc_identity(pid):
  root=Path('/proc')/str(pid)
  if not root.exists():return None
  return {'start':root.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
    'command_sha':hashlib.sha256(root.joinpath('cmdline').read_bytes()).hexdigest(),
    'ppid':int(root.joinpath('stat').read_text().rsplit(')',1)[1].split()[1])}
 def same_owned(h):
  x=proc_identity(h['pid'])
  return bool(x and x['start']==h['linux_start_ticks'] and x['command_sha']==h['command_sha256'])
 def cleanup_owned():
  for h in handles:
   if same_owned(h):os.kill(h['pid'],signal.SIGTERM)
  deadline=time.time()+10
  while time.time()<deadline and any(same_owned(h) for h in handles):time.sleep(.05)
  for h in handles:
   if same_owned(h):os.kill(h['pid'],signal.SIGKILL)
 try:
  with (D/'initial.log').open('w') as log:owner=subprocess.Popen(common+['--output',str(initial),'--crash-after-commits','1'],cwd=S,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
  started=time.perf_counter();marker_path=initial/'ACK_FOR_KILL.json'
  while not marker_path.exists():
   assert owner.poll() is None,'owner exited before durable kill marker'
   if time.perf_counter()-started>600:raise TimeoutError('owner did not reach bounded kill marker')
   time.sleep(.01)
  marker=read(marker_path);handles=read(initial/'OWNED_WORKER_HANDLES.json')
  assert handles and all(same_owned(h) and proc_identity(h['pid'])['ppid']==owner.pid for h in handles)
  cmd=Path('/proc')/str(owner.pid)/'cmdline';assert str(initial).encode() in cmd.read_bytes() and str(S/'scripts/run_tc_live_qwen.py').encode() in cmd.read_bytes()
  trace=initial/'worker-authority-1-receipts.jsonl';receipt_lines=[json.loads(x) for x in trace.read_text().splitlines()]
  selected=next(r for r in receipt_lines if r['kind']=='row-complete' and r['message']['binding']['job_id']==marker['job_id'])
  bid=selected['message']['binding']['batch_id']
  before_drained=not any(r['kind']=='batch-drained' and r['message']['batch_id']==bid for r in receipt_lines)
  kill=time.perf_counter();os.kill(owner.pid,signal.SIGKILL);assert owner.wait(timeout=20)==-signal.SIGKILL;owner=None
  save(D/'KILL.json',{'kill_perf':kill,'durable_marker':marker,'physical_batch':bid,
     'observed_before_batch_drained':before_drained,'owned_worker_identities':handles})
  # Give already running old GPU work a bounded opportunity to finish; all time
  # remains inside the independent full fault-campaign power observation.
  time.sleep(2);cleanup_owned();handles=[]
  until=time.time()+15
  while subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():
   if time.time()>until:raise RuntimeError('GPU still occupied; do not kill unowned tasks or start resume')
   time.sleep(.1)
  before=audit_wal(wal);save(D/'WAL_AFTER_KILL_AUDIT.json',before)
  restart=time.perf_counter()
  with (D/'resume.log').open('w') as log:q=subprocess.run(common+['--output',str(resumed)],cwd=S,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
  assert q.returncode==0,'fresh owner resume failed'
  after=audit_wal(wal);cert=audit_certificates(resumed)
  save(D/'WAL_AFTER_RESUME_AUDIT.json',after);save(D/'RESUME_CERTIFICATE_AUDIT.json',cert)
  views=[json.loads(x) for x in (resumed/'consumer.jsonl').read_text().splitlines()]
  first=min(v['observed_perf'] for v in views if v['session_id']==marker['session_id'] and v['certified_frontier']>=marker['audio_end_sample'])
  # The persisted pre-resume state contains all group-ready rows, including any
  # durable-but-unacknowledged peer; never assume exactly one durable transition.
  starts=read(resumed/'initial_states.json');matched=next(s['state'] for s in starts if s['session_id']==marker['session_id'])
  assert matched['audio_frontier_window']>=marker['audio_end_sample']
  assert marker['segment_id'] in matched['committed_segment_ids']
  assert matched['contract_epoch']>=2
  result=read(resumed/'result.json');ids=[tid for st in result['final_states'] for tid in st['state']['committed_segment_ids']]
  assert len(ids)==len(set(ids))==59,'duplicate or lost formal source admissions'
  save(D/'POWER.json',{'campaign':sampler.stop(),'samples':sampler.rows,'scope':'full fault campaign including initialization/discarded-work wait/cleanup/resume;not normal serving J/audio-s'})
  save(D/'SUMMARY.json',{'status':'PASS_REAL_GPU_EARLY_ROW_OWNER_SIGKILL_AND_COLD_RESUME',
    'observed_before_batch_drained':before_drained,'acknowledged_segment_survives':True,'unique_final_admissions':59,
    'duplicate_admissions':0,'restart_to_first_certified_consumer_s':first-restart,'kill_to_first_certified_consumer_s':first-kill,
    'no_warm_worker_adoption':True,'not_host_power_loss_or_millisecond_service_RTO':True})
 except BaseException as e:
  save(D/'STOP.json',{'error':repr(e),'all_raw_retained':True,'no_silent_retry':True});raise
 finally:
  if owner is not None and owner.poll() is None:
   cmd=Path('/proc')/str(owner.pid)/'cmdline'
   if cmd.exists() and str(initial).encode() in cmd.read_bytes():os.kill(owner.pid,signal.SIGKILL);owner.wait(timeout=20)
   if (initial/'OWNED_WORKER_HANDLES.json').exists():handles=read(initial/'OWNED_WORKER_HANDLES.json')
  if handles:cleanup_owned()
  sampler.stop()

if __name__=='__main__':main()
