"""Tiny exact-handle status, terminal full16-only bounded SHA collection."""
import argparse,ast,datetime,hashlib,json,pathlib,sys
H=pathlib.Path(__file__).resolve().parents[1];I=H.parent/'dsn_streamcorrect_independent_20261029'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';O=B+'/results/revtrace/dsn_streamcorrect_independent_20261029'
PLAN_SHA='cab424783f30ff9b53db8deef5eba482d3b101f15336b65de8b1c7d9ced3679a'
METHOD='bdfa3b1307d267a5a4caf6484e1ad465c39a592e'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def remote_script(handle,collect):
 script="""import pathlib,json,hashlib,subprocess,datetime
O=pathlib.Path(O_VALUE);expected=HANDLE_VALUE;h=json.loads((O/'FINAL_SERVICE_HANDLE_v1.json').read_bytes());assert h==expected
proc=pathlib.Path('/proc')/str(h['pid']);alive=False;state=None;observed_start=None;observed_cmd=None
if proc.exists():
 try:
  stat=(proc/'stat').read_text().rsplit(')',1)[1].split();state=stat[0];observed_start=int(stat[19]);observed_cmd=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest();alive=observed_start==h['start_ticks'] and observed_cmd==h['cmdline_sha256'] and state!='Z'
 except FileNotFoundError:pass
out=pathlib.Path(h['out']);r=dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),exact_controller_alive=alive,process_state=state,pid=h['pid'],expected_start_ticks=h['start_ticks'],observed_start_ticks=observed_start,expected_cmdline_sha256=h['cmdline_sha256'],observed_cmdline_sha256=observed_cmd,out=str(out),source_commit=h['source_commit'],plan_sha256=h['plan_sha256'])
for name in ('PROGRESS.json','GATE.json'):
 q=out/name
 if q.exists():
  data=q.read_bytes()
  try:r[name]=dict(sha256=hashlib.sha256(data).hexdigest(),value=json.loads(data))
  except json.JSONDecodeError:r[name]=dict(temporarily_unreadable_during_nonatomic_write=True,not_process_death=True)
if (out/'failure.txt').exists():r['failure_tail']=(out/'failure.txt').read_text(errors='replace')[-6000:]
if COLLECT_VALUE:
 assert not alive and (out/'GATE.json').exists(),'wait for same exact controller exit AND full16 terminal gate'
 gate=json.loads((out/'GATE.json').read_bytes());assert gate['status']=='PASS_ALL_FROZEN_NATIVE_SERVICE_CELLS_AND_COMPLETE_TASK_FIDELITY' and gate['completed_cells']==gate['planned_cells']==16 and gate['all_full_task_fidelity_pass']
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'GPU still occupied; no collection'
 plan=json.loads((out/'CONFIG.json').read_bytes());assert h['plan_sha256']==PLAN_SHA and h['source_commit']==METHOD and len(plan['cells'])==16
 frozen_plan_bytes=pathlib.Path(h['command'][h['command'].index('--plan')+1]).read_bytes();assert hashlib.sha256(frozen_plan_bytes).hexdigest()==PLAN_SHA and plan==json.loads(frozen_plan_bytes)
 assert h['source_manifest_sha256']==plan['source_manifest_sha256']=='258c33df4eba1d27bef88339aa20b2aae2ffe69f43489255d989ad337b717521'
 assert hashlib.sha256((out/'SUMMARY.json').read_bytes()).hexdigest()==gate['summary_sha256']
 wanted=('CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','ORIGIN.json','READY.json','SUMMARY.json','GATE.json','COMPLETE_TASK_FIDELITY.json','CANONICAL_HISTORIES.json','CONSUMPTIONS.json','STAGE_ADMISSIONS.json','DISPATCHES.json','MATCHING_INFLIGHT_OPPORTUNITIES.json','ENERGY.json','PRIMARY_METRICS.json','CONTENT.json','CONTENT_EVENTS.json','CONTENT_SPANS.json','CONTENT_FRONTIERS.json','native_jobs.jsonl','events.jsonl','consumer.jsonl','canonical_wal.jsonl','accepted_input_wal.jsonl','power.jsonl')
 rows=[]
 def add(q,p):
  assert q.is_file() and not q.is_symlink() and q.stat().st_size<=8*1024*1024
  data=q.read_bytes();rows.append(dict(path=p,remote=str(q),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 for name in ('CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','PROGRESS.json','PARTIAL_RESULTS.json','SUMMARY.json','GATE.json'):add(out/name,'campaign/'+name)
 for name in ('CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','CPU_CONTROLS.log'):add(O/'service_cpu_v1'/name,'CPU/'+name)
 for cell in plan['cells']:
  d=pathlib.Path(cell['out']);assert json.loads((d/'GATE.json').read_bytes())['status']=='PASS_ACTUAL_NATIVE_SERVICE_EXECUTION'
  for name in wanted:add(d/name,cell['cell_id']+'/'+name)
  if cell['arm']=='two_full_spec_early':add(d/'FULLSPEC_LEDGER.json',cell['cell_id']+'/FULLSPEC_LEDGER.json')
  add(pathlib.Path(cell['log']),cell['cell_id']+'/worker_stdout.log')
 assert sum(x['bytes'] for x in rows)<=128*1024*1024 and len({x['path'] for x in rows})==len(rows)
 r['collection_files']=rows;r['source_manifest_sha256']=plan['source_manifest_sha256'];r['scope']=plan['scope'];r['full16_and_exact_exit_and_GPU_empty_verified']=True
print(json.dumps(r))
"""
 return script.replace('O_VALUE',repr(O)).replace('HANDLE_VALUE',repr(handle)).replace('COLLECT_VALUE',repr(collect)).replace('PLAN_SHA',repr(PLAN_SHA)).replace('METHOD',repr(METHOD))
def main():
 p=argparse.ArgumentParser();p.add_argument('--collect',action='store_true');p.add_argument('--self-test',action='store_true');a=p.parse_args()
 if a.self_test:
  for c in (False,True):ast.parse(remote_script(dict(pid=1,source_commit=METHOD),c))
  print('PASS_EXPANDED_REMOTE_AST_BOTH_MODES_NO_REMOTE_IO');return
 handle=json.loads((I/'FINAL_SERVICE_HANDLE_v1.json').read_bytes());assert handle['pid']==1833614 and handle['start_ticks']==502958286 and handle['plan_sha256']==PLAN_SHA and handle['source_commit']==METHOD
 script=remote_script(handle,a.collect);ast.parse(script)
 sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
 c=ssh_client()
 try:
  i,o,e=c.exec_command('python3 -B -',timeout=45);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();assert rc==0,stderr.decode();r=json.loads(stdout)
  if a.collect:
   target=I/'SERVICE_RESULTS_v1';target.mkdir(exist_ok=True);assert not (target/'COLLECTION_MANIFEST.json').exists(),'completed receipt already exists; never replace'
   s=c.open_sftp()
   try:
    for row in r['collection_files']:
     dest=target/row['path'];dest.parent.mkdir(parents=True,exist_ok=True)
     if not dest.exists():s.get(row['remote'],str(dest))
     assert dest.stat().st_size==row['bytes'] and sha(dest)==row['sha256'],'bounded collection SHA mismatch: '+row['path']
   finally:s.close()
   receipt=dict(files=r['collection_files'],all_bytes_equal=True,total_bytes=sum(x['bytes'] for x in r['collection_files']),source_commit=METHOD,source_manifest_sha256=r['source_manifest_sha256'],plan_sha256=PLAN_SHA,complete_scope=r['scope'],full16_and_exact_exit_and_GPU_empty_verified=True,raw_packets='All packet payloads, models, datasets, environments and unselected raw remain designated8TB; no packet payload fetched',controller_handle=handle,observed_utc=r['observed_utc'])
   (target/'COLLECTION_MANIFEST.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());(target/'CONTROLLER_TERMINAL_STATUS.json').write_bytes((json.dumps({k:v for k,v in r.items() if k!='collection_files'},indent=2)+'\n').encode())
   print(json.dumps(dict(status='COMPLETE16_BOUNDED_BYTES_VERIFIED_NOT_YET_INDEPENDENT_ANALYSIS',files=len(receipt['files']),bytes=receipt['total_bytes'],output=str(target),collection_manifest_sha256=sha(target/'COLLECTION_MANIFEST.json'),campaign_gate_sha256=sha(target/'campaign/GATE.json'),IO_released=True),indent=2))
  else:
   folder=I/'service_status_polls_v1';folder.mkdir(exist_ok=True);stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');(folder/(stamp+'.json')).write_bytes((json.dumps(r,indent=2)+'\n').encode());print(json.dumps(r,indent=2))
 finally:c.close()
if __name__=='__main__':main()
