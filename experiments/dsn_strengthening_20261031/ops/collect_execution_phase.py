"""After physical quiescence, inventory all raw bytes and copy bounded evidence."""
import argparse,hashlib,json,pathlib,shlex,sys
E=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_20261031';O=B+'/results/revtrace/dsn_strengthening_20261031';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['paired32_v2','resident4_v2','buffer4_v1','interference_opportunity4_v1'],required=True);a=p.parse_args();phase=a.phase;local=E/(phase.upper()+'_RESULTS');assert not local.exists()
code=r'''import pathlib,json,hashlib,subprocess,sys
P=pathlib.Path(__PROJECT__);O=pathlib.Path(__OUTPUT__);root=O/__PHASE__;sys.path.insert(0,str(P/'paired_resident_source_v2'));from common import read,put,sha,canonical,need
need((root/'GATE.json').is_file(),'completed phase gate missing');need(not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=5).strip(),'no heavy collection during live GPU work')
inventory=[]
for path in sorted(root.rglob('*')):
 if path.is_file():inventory.append(dict(path=str(path.relative_to(root)),bytes=path.stat().st_size,sha256=sha(path)))
folder=O/'collections';folder.mkdir(exist_ok=True);manifest=folder/(__PHASE__+'_RAW_INDEX.json');put(manifest,dict(operation='complete raw-byte inventory after phase quiescence; not metric recomputation',raw_root=str(root),files=inventory,total_bytes=sum(r['bytes'] for r in inventory),file_count=len(inventory),phase_gate=read(root/'GATE.json')))
bounded=[p for p in root.iterdir() if p.is_file() and p.name in ('CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','GATE.json','SUMMARY.json','SMOKE8_DECISION.json','SMOKE2_DECISION.json')]
for cell in sorted((root/'cells').glob('*')):
 for name in ('SUMMARY.json','GATE.json','ENERGY.json','ORIGIN.json','SERVICE_END.json','RUN_RECORD.json','ENVIRONMENT.json','PRIMARY_METRICS.json','BUFFER_WITNESS_GATE.json','OWNER_CLEANUP.json'):
  q=cell/name
  if q.is_file():bounded.append(q)
 ready=[]
 if (cell/'READY.json').exists():ready=list(read(cell/'READY.json').values())
 else:
  for path in cell.glob('owner_e*/worker_results.jsonl'):
   with path.open('r',encoding='utf8') as stream:
    for line in stream:
     row=json.loads(line);event=row.get('event',{})
     if event.get('kind')=='ready':ready.append(event)
 compact=[]
 for row in ready:
  warm=row.get('neural_ready_warmup',{});compact.append(dict(worker=row.get('worker'),pid=row['pid'],gpu=row['gpu'],worker_incarnation=row.get('worker_incarnation'),mode=row.get('mode'),environment=row.get('environment'),ASR_parameter_dtypes=row.get('asr_parameter_dtypes'),corrector_parameter_dtypes=row.get('corrector_parameter_dtypes'),runtime_identity_sha256=hashlib.sha256(canonical(row.get('runtime_identity'))).hexdigest(),initial_cut_sha256={sid:hashlib.sha256(canonical(v)).hexdigest() for sid,v in row.get('initials',{}).items()},warmup={k:v for k,v in warm.items() if k!='original_record'},warmup_original_record_sha256=hashlib.sha256(canonical(warm.get('original_record'))).hexdigest()))
 q=folder/(__PHASE__+'_'+cell.name+'_READY_IDENTITY.json');put(q,dict(cell_id=cell.name,actual_ready_rows=compact,scope='Actual READY parameter/env/warmup identity summaries; raw source records remain inventoried on8TB'));bounded.append(q)
if (root/'watchdog').exists():
 for q in root.glob('watchdog/*/WATCHDOG_GATE.json'):bounded.append(q)
rows=[dict(remote=str(q),relative=str(q.relative_to(root)) if q.is_relative_to(root) else 'identity/'+q.name,bytes=q.stat().st_size,sha256=sha(q)) for q in bounded];rows.append(dict(remote=str(manifest),relative='RAW_INDEX.json',bytes=manifest.stat().st_size,sha256=sha(manifest)))
index=folder/(__PHASE__+'_BOUNDED_INDEX.json');put(index,dict(raw_manifest=str(manifest),raw_manifest_sha256=sha(manifest),bounded_files=rows,total_bounded_bytes=sum(r['bytes'] for r in rows),phase_gate=read(root/'GATE.json')));print(json.dumps(dict(index=str(index),files=len(rows),bytes=sum(r['bytes'] for r in rows),raw_files=len(inventory),raw_bytes=sum(r['bytes'] for r in inventory))))
'''.replace('__PROJECT__',repr(P)).replace('__OUTPUT__',repr(O)).replace('__PHASE__',repr(phase))
compile(code,'remote_phase_collection','exec')
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=120);i.write(code);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();rc=o.channel.recv_exit_status();assert rc==0,err.decode();result=json.loads(b);s=c.open_sftp()
 with s.open(result['index'],'rb') as stream:index_raw=stream.read()
 index=json.loads(index_raw);local.mkdir();(local/'BOUNDED_INDEX.json').write_bytes(index_raw)
 for row in index['bounded_files']:
  target=local/pathlib.PurePosixPath(row['relative']);target.parent.mkdir(parents=True,exist_ok=True)
  with s.open(row['remote'],'rb') as stream:data=stream.read()
  assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'];target.write_bytes(data)
 print(json.dumps(result))
finally:c.close()
