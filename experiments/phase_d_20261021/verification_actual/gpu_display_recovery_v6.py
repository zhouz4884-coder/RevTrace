"""Actual SIGKILL after durable install, before canonical publication; owned PG only."""
import hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
B=Path(sys.argv[1]);P=B/'projects/revtrace_phaseD_20261021';S=P/'continuity_v6';O=B/'results/revtrace/phaseD_20261021/R2_gpu_recovery';O.mkdir(exist_ok=False)
CODE=json.loads((S/'SOURCE_MANIFEST.json').read_text())['code_commit']
def idle():return not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
matrix={'experiment_id':'PHASE-D-DISPLAY-RECOVERY','repeats':3,'fault':'SIGKILL at first install commit emit callback; WAL group synced, canonical publication has not executed','code_commit':CODE,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sessions':2,'consumer_policy':'two_lane','scope':'real GPU/process crash, not host/storage failure, new FIFO consumer incarnation'}
(O/'DESIGN_FREEZE.json').write_text(json.dumps(matrix,indent=2)+'\n');done=[]
try:
 for repeat in range(3):
  assert idle();wal=O/'journals'/f'r{repeat}.wal';before=O/f'crash-r{repeat}';after=O/f'restore-r{repeat}'
  def command(out):return [sys.executable,'-u',str(S/'scripts/run_tc_live_qwen.py'),'--model',str(B/'models/Qwen3-ASR-1.7B'),'--manifest',str(B/'datasets/revtrace/phaseD_20261021/manifest.json'),'--output',str(out),'--code-commit',CODE,'--study-id','PHASE-D-DISPLAY-RECOVERY','--mode','coarse','--sessions','2','--proposal-barrier','decoupled','--proposal-reconciliation','lazy','--display-protocol','canonical-snapshot-v1','--publish-canonical-display','--trusted-text-binding','--consumer-policy','two_lane','--phase-n-instrumentation','--capture-model-inputs','--durable-journal-path',str(wal),'--journal-sync-mode','group_ready','--retain-verified-private-prefix']
  args=command(before)+['--crash-after-commits','1'];started=time.perf_counter()
  with (O/f'crash-r{repeat}.log').open('w') as log:
   child=subprocess.Popen(args,cwd=S,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);deadline=time.monotonic()+180
   try:
    while True:
     if (before/'ACK_FOR_KILL.json').exists():
      try:marker=json.loads((before/'ACK_FOR_KILL.json').read_text())
      except json.JSONDecodeError:pass
      else:break
     if child.poll() is not None:raise RuntimeError('Crash target exited before boundary')
     if time.monotonic()>deadline:raise RuntimeError('No durable boundary marker in bounded wait')
     time.sleep(.05)
    pid=child.pid;cmd=Path('/proc/'+str(pid)+'/cmdline').read_bytes().replace(b'\0',b' ').decode()
    assert str(before) in cmd and str(S/'scripts/run_tc_live_qwen.py') in cmd and '--crash-after-commits' in cmd
    assert os.getpgid(pid)==pid and Path('/proc/'+str(pid)).stat().st_uid==os.getuid()
    events=[json.loads(l) for l in (before/'events.jsonl').read_text().splitlines()];assert marker['kind']=='commit'
    assert not any(e['kind']=='canonical-display' and e['session_id']==marker['session_id'] and e['version']==marker['version'] for e in events)
    frozen=wal.read_bytes();assert len(frozen)>0;(O/f'killed-prefix-r{repeat}.wal').write_bytes(frozen);os.killpg(pid,signal.SIGKILL);child.wait(timeout=20)
   except BaseException:
    if child.poll() is None:
     owned=Path('/proc/'+str(child.pid)+'/cmdline').read_bytes().replace(b'\0',b' ').decode()
     assert str(before) in owned and str(S/'scripts/run_tc_live_qwen.py') in owned and os.getpgid(child.pid)==child.pid
     assert Path('/proc/'+str(child.pid)).stat().st_uid==os.getuid()
     os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=20)
    raise
  deadline=time.monotonic()+20
  while not idle() and time.monotonic()<deadline:time.sleep(.2)
  assert idle(),'Do not kill any unrelated GPU process'
  rstart=time.perf_counter()
  with (O/f'restore-r{repeat}.log').open('w') as log:r=subprocess.run(command(after),cwd=S,stdout=log,stderr=subprocess.STDOUT)
  assert r.returncode==0,'Recovery failure retained'
  ev=[json.loads(l) for l in (after/'events.jsonl').read_text().splitlines()];views=[json.loads(l) for l in (after/'consumer.jsonl').read_text().splitlines()];pub=[e for e in ev if e['kind']=='canonical-display' and e.get('recovered')]
  assert pub and any(e['session_id']==marker['session_id'] and e['version']>=marker['version'] for e in pub)
  for e in pub:assert any(v['session_id']==e['session_id'] and v['canonical_version']==e['version'] and v['certified_text']==e['text'] and v['certified_frontier']==e['audio_end_sample'] for v in views)
  keys={(e['session_id'],e['version']) for e in pub};first_observed=min(a['observed_perf'] for a in views if (a['session_id'],a['canonical_version']) in keys)
  res=json.loads((after/'result.json').read_text());record={'repeat':repeat,'owned_pid':pid,'verified_cmd':cmd,'exit_code':child.returncode,'wal_prefix_before_kill_sha256':hashlib.sha256(frozen).hexdigest(),'wal_prefix_before_kill_bytes':len(frozen),'wal_prefix_survived':wal.read_bytes().startswith(frozen),'killed_after_install_before_publication':True,'recovered_snapshots':len(pub),'all_recovered_observed_by_real_consumer':True,'journal_recovery_seconds':res['journal_recovery_seconds'],'model_initialization_seconds':res['worker_initialization_seconds'],'restart_launch_perf':rstart,'first_recovered_consumer_perf':first_observed,'restart_to_first_certified_consumer_seconds':first_observed-rstart,'restore_process_full_wall_seconds':time.perf_counter()-rstart,'first_recovered_server_publication_since_scheduler_t0':min(e['displayed'] for e in pub),'scope':'three repeat process-kill trials; ledger/model-init/restart-to-consumer/drain clocks separate; no storage/network exactly-once'}
  assert record['wal_prefix_survived'];done.append(record);(O/'PROGRESS.json').write_text(json.dumps(done,indent=2));print(json.dumps(record),flush=True)
 (O/'SUMMARY.json').write_text(json.dumps({'status':'COMPLETE','trials':done,'code_commit':CODE},indent=2)+'\n')
except BaseException as ex:(O/'STOP.json').write_text(json.dumps({'error':repr(ex),'completed':done},indent=2));raise
