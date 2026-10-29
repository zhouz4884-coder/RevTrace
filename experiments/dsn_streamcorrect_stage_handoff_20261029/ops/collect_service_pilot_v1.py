"""Collect only bounded completed service evidence; raw candidate packets stay B-only."""
import argparse,hashlib,json,pathlib,shlex,sys
p=argparse.ArgumentParser();p.add_argument('--campaign',choices=['pilot','confirmation'],default='pilot');args=p.parse_args()
T=pathlib.Path(__file__).resolve().parents[1];plan=json.loads((T/('SERVICE_PILOT_v1_FROZEN.json' if args.campaign=='pilot' else 'SERVICE_CONFIRMATION_v1_FROZEN.json')).read_text(encoding='utf8'));expected=plan['expected_cells'];dest=T/('SERVICE_PILOT_RESULTS_v1' if args.campaign=='pilot' else 'SERVICE_CONFIRMATION_RESULTS_v1');assert not dest.exists()
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client();rows=[]
try:
 code="import subprocess,json,pathlib; p=pathlib.Path("+repr(plan['gate_decision_location'])+"); g=json.loads(p.read_text()); assert g['status']=='PASS_ALL_FROZEN_NATIVE_SERVICE_CELLS_AND_COMPLETE_TASK_FIDELITY' and g['completed_cells']=="+str(expected)+"; assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(); print('COMPLETE_ALL_AND_GPU_RELEASED')"
 i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=30);i.write(code);i.flush();i.channel.shutdown_write();check=o.read().decode();error=e.read().decode();assert o.channel.recv_exit_status()==0,error;assert 'COMPLETE_ALL' in check
 s=c.open_sftp();dest.mkdir();pairs=[]
 for name in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','PROGRESS.json','PARTIAL_RESULTS.json','SUMMARY.json','GATE.json']:pairs.append((plan['campaign_output']+'/'+name,'campaign/'+name,True))
 common=['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','ORIGIN.json','READY.json','SUMMARY.json','GATE.json','COMPLETE_TASK_FIDELITY.json','CANONICAL_HISTORIES.json','CONSUMPTIONS.json','STAGE_ADMISSIONS.json','DISPATCHES.json','MATCHING_INFLIGHT_OPPORTUNITIES.json','ENERGY.json','PRIMARY_METRICS.json','CONTENT.json','CONTENT_EVENTS.json','CONTENT_SPANS.json','CONTENT_FRONTIERS.json','native_jobs.jsonl','events.jsonl','consumer.jsonl','canonical_wal.jsonl','accepted_input_wal.jsonl','power.jsonl']
 for cell in plan['cells']:
  for name in common:pairs.append((cell['out']+'/'+name,cell['cell_id']+'/'+name,True))
  pairs.append((cell['out']+'/FULLSPEC_LEDGER.json',cell['cell_id']+'/FULLSPEC_LEDGER.json',cell['arm']=='two_full_spec_early'))
  pairs.append((cell['log'],cell['cell_id']+'/worker_stdout.log',True))
 for remote,rel,required in pairs:
  try:size=s.stat(remote).st_size
  except FileNotFoundError:
   assert not required,remote
   continue
  assert size<20_000_000,remote;local=dest/rel;local.parent.mkdir(exist_ok=True,parents=True);s.get(remote,str(local));data=local.read_bytes();assert len(data)==size
  with s.open(remote,'rb') as f:remote_data=f.read()
  assert remote_data==data;rows.append(dict(path=rel,remote=remote,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 s.close();manifest=dict(files=rows,all_bytes_equal=True,total_bytes=sum(x['bytes'] for x in rows),raw_packets='all candidate wire payloads and model/audio/env remain designated B disk; no packets downloaded',source_commit=plan['source_commit'],complete_scope=plan['scope'])
 (dest/'COLLECTION_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
 summary=json.loads((dest/'campaign/SUMMARY.json').read_text(encoding='utf8'));statuspath=T/'CURRENT_STATUS.json';status=json.loads(statuspath.read_text(encoding='utf8'));status.update(status='COMPLETE_SOURCE0_PILOT_AND_FOUR_OLD_SOURCE_CONFIRMATION_TASK_FIDELITY_PASS' if args.campaign=='confirmation' else 'COMPLETE_SOURCE0_THREE_ARM_PILOT_ALL_TASK_FIDELITY_PASS_DECISION_PENDING',actual_serving_cells=19 if args.campaign=='confirmation' else 3,remote_resources_released=True,service_summary_sha256=hashlib.sha256((dest/'campaign/SUMMARY.json').read_bytes()).hexdigest(),next_action='Analyze all frozen paired data and explicit content/EOS limits. Conditional encoder-readset component probe is separately planned; no new-source measurement yet.')
 statuspath.write_text(json.dumps(status,indent=2)+'\n',encoding='utf8');print(json.dumps(dict(files=len(rows),bytes=manifest['total_bytes'],status=summary['status'],comparisons=summary['development_opportunity_screen']),indent=2))
finally:c.close()
