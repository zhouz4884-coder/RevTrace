"""Tiny exact-handle poll, or bounded collect only after controller exit+gate."""
import argparse,pathlib,json,hashlib,sys,shlex
H=pathlib.Path(__file__).resolve().parents[1];I=H.parent/'dsn_streamcorrect_independent_20261029'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';O=B+'/results/revtrace/dsn_streamcorrect_independent_20261029'
p=argparse.ArgumentParser();p.add_argument('--collect',action='store_true');a=p.parse_args()
script="""import pathlib,json,hashlib,subprocess
O=pathlib.Path(O_VALUE);h=json.loads((O/'REFERENCE_HANDLE_v1.json').read_bytes());proc=pathlib.Path('/proc')/str(h['pid']);alive=False;state=None
if proc.exists():
 try:
  stat=(proc/'stat').read_text().rsplit(')',1)[1].split();state=stat[0];alive=int(stat[19])==h['start_ticks'] and hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()==h['cmdline_sha256'] and state!='Z'
 except FileNotFoundError:pass
out=pathlib.Path(h['out']);r=dict(exact_controller_alive=alive,process_state=state,pid=h['pid'],out=str(out),reference_only=True)
for name in ('PROGRESS.json','GATE.json','SUMMARY.json'):
 q=out/name
 if q.exists():r[name]=dict(sha256=hashlib.sha256(q.read_bytes()).hexdigest(),value=json.loads(q.read_bytes()))
if COLLECT_VALUE:
 assert not alive and (out/'GATE.json').exists(),'wait for exact controller exit and terminal gate; do not collect during NN'
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'actual model process still owns GPU'
 rows=[];inventory=[]
 for base,prefix in [(out,''),(O/'reference_cpu_v1','CPU/')]:
  for q in sorted(base.iterdir()):
   if not q.is_file():continue
   item=dict(path=prefix+q.name,remote=str(q),bytes=q.stat().st_size,sha256=hashlib.sha256(q.read_bytes()).hexdigest());inventory.append(item)
   if q.name!='RAW_STEPS.jsonl':rows.append(item)
 assert sum(x['bytes'] for x in rows)<=20*1024*1024,'bounded output budget exceeded; preserve raw and review explicit files'
 r['collection_files']=rows;r['remote_raw_inventory']=inventory
 log=O/'reference_v1.log'
 if log.exists():
  with log.open('rb') as f:f.seek(max(0,log.stat().st_size-8000));r['log_tail']=f.read().decode('utf8',errors='replace')
print(json.dumps(r))
""".replace('O_VALUE',repr(O)).replace('COLLECT_VALUE',repr(a.collect))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command('python3 -B -',timeout=30);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();assert rc==0,stderr.decode();r=json.loads(stdout)
 if a.collect:
  target=I/'REFERENCE_RESULTS_v1';target.mkdir(exist_ok=False);s=c.open_sftp()
  try:
   for row in r['collection_files']:
    dest=target/row['path'];dest.parent.mkdir(parents=True,exist_ok=True);s.get(row['remote'],str(dest));raw=dest.read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
  finally:s.close()
  (target/'COLLECTION_MANIFEST.json').write_bytes(json.dumps(dict(files=r['collection_files'],remote_raw_inventory=r['remote_raw_inventory'],all_remote_SHA256_verified=True,total_bytes=sum(x['bytes'] for x in r['collection_files']),RAW_STEPS_remains_on_8TB=True),indent=2).encode())
  (target/'reference_log_tail.txt').write_text(r.get('log_tail',''),encoding='utf8')
  print(json.dumps(dict(status=r.get('GATE.json'),files=len(r['collection_files']),bytes=sum(x['bytes'] for x in r['collection_files']),output=str(target)),indent=2))
 else:
  compact={k:v for k,v in r.items() if k not in ('SUMMARY.json',)};print(json.dumps(compact,indent=2))
finally:c.close()
