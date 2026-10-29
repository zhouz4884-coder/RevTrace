"""Tiny authoritative process/JSON observation; never restarts workers."""
import argparse,json,pathlib,shlex,sys
ap=argparse.ArgumentParser();ap.add_argument('--campaign',choices=['pilot','confirmation'],default='pilot');args=ap.parse_args()
T=pathlib.Path(__file__).resolve().parents[1];h=json.loads((T/('SERVICE_HANDLE_v1.json' if args.campaign=='pilot' else 'CONFIRMATION_HANDLE_v1.json')).read_text(encoding='utf8'));plan=json.loads((T/('SERVICE_PILOT_v1_FROZEN.json' if args.campaign=='pilot' else 'SERVICE_CONFIRMATION_v1_FROZEN.json')).read_text(encoding='utf8'))
code=r'''import pathlib,json,hashlib,time
h=HANDLE;out=pathlib.Path(h['campaign_output']);p=pathlib.Path('/proc')/str(h['pid']);r={}
if p.exists():
 raw=(p/'stat').read_text().rsplit(')',1)[1].split();r['process']=dict(pid=h['pid'],state=raw[0],same_start_ticks=int(raw[19])==h['start_ticks'],same_cmdline=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==h['cmdline_sha256'])
else:r['process']=dict(pid=h['pid'],exists=False)
for name in ['PROGRESS.json','GATE.json']:
 f=out/name
 if f.exists():r[name]=json.loads(f.read_text())
current=r.get('PROGRESS.json',{}).get('current')
if current:
 cell=pathlib.Path(h['raw_result_location'])/'cells'/current
 r['current_cell_files']={name:dict(bytes=(cell/name).stat().st_size,mtime=(cell/name).stat().st_mtime) for name in ['READY.json','ORIGIN.json','GATE.json','native_jobs.jsonl','consumer.jsonl'] if (cell/name).exists()}
 if (cell/'ORIGIN.json').exists():r['current_service_elapsed_seconds']=time.perf_counter()-json.loads((cell/'ORIGIN.json').read_text())['origin_perf']
 log=pathlib.Path(h['raw_result_location'])/'logs'/(current+'.log')
 if log.exists():
  with log.open('rb') as f:f.seek(max(0,log.stat().st_size-1000));r['current_log_tail']=f.read().decode(errors='replace')
f=out/'PARTIAL_RESULTS.json'
if f.exists():r['completed_cells_recent']=[dict(arm=x['arm'],source=x['sources'],repeat=x['repeat'],credit=x['primary']['dual_deadline_audio_credit_seconds'],D99=x['primary']['primary_linear_all_offered_D99'],C99=x['primary']['primary_linear_all_offered_C99'],C50=x['latency_medians']['all_offered_C50'],whole_pass=x['primary']['complete_coverage_and_original_quantile_pass'],J=x['service_board_joules'],hits=x['actual_ready_hits'],promotions=x['fullspec_inflight_promotions'],matching_inflight_fallbacks=x['matching_inflight_fallbacks'],fidelity=x['fidelity']['status']) for x in json.loads(f.read_text())[-4:]]
if (out/'GATE.json').exists() or not p.exists():
 log=pathlib.Path(h['log'])
 if log.exists():
  with log.open('rb') as f:f.seek(max(0,log.stat().st_size-1800));r['controller_log_tail']=f.read().decode(errors='replace')
print(json.dumps(r,indent=2))
'''.replace('HANDLE',repr(h))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=30);i.write(code);i.flush();i.channel.shutdown_write();s=o.read().decode();error=e.read().decode();rc=o.channel.recv_exit_status();assert rc==0,error;print(s)
finally:c.close()
