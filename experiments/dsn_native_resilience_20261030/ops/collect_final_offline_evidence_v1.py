"""Whole bounded offline outputs, byte-audited; no point or outcome selection."""
import argparse,hashlib,json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';p=argparse.ArgumentParser();p.add_argument('--kind',choices=['trace','native','export'],required=True);a=p.parse_args();specs=dict(trace=(B+'/results/revtrace/dsn_native_refinement_20261030/formal_actual36_v1','PASS_ALL_FORMAL36_ACTUAL_ORIGINAL_FULLCALL_REFINEMENT',F/'FORMAL_ACTUAL36_TRACE_RESULTS_v1'),native=(B+'/results/revtrace/dsn_native_resilience_20261030/native_work_recount_v1','PASS_COMPLETE_LITERAL_NATIVE_RECORD_COUNTS_AND_STRICT_CLOCK_AUDIT',F/'NATIVE_WORK_RECOUNT_RESULTS_v1'),export=(B+'/results/revtrace/dsn_native_resilience_20261030/bounded_formal36_v3','PASS_ALL36_BOUNDED_SERIES_AND_ORIGINAL_ENDPOINT_RECOUNTS',F/'BOUNDED_FORMAL36_RESULTS_v3'));remote,status,dest=specs[a.kind]
script=r'''import pathlib,json,hashlib,subprocess
root=pathlib.Path(ROOT);kind=KIND
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
gate_path=root/('results/GATE.json' if kind=='native' else 'GATE.json');gate=json.loads(gate_path.read_bytes());assert gate['status']==STATUS
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
rows=[]
for p in sorted(root.rglob('*')):
 if not p.is_file():continue
 assert not p.is_symlink();relative=p.relative_to(root).as_posix()
 if relative.startswith('tmp/') or '/tmp/' in relative:continue
 assert p.stat().st_size<20_000_000,'Bounded output too large; do not silently truncate or select points: '+relative
 rows.append(dict(path=relative,remote=str(p),bytes=p.stat().st_size,sha256=sha(p)))
assert sum(r['bytes'] for r in rows)<256_000_000,'bounded group too large; preserve on8TB and explicitly change export packaging'
print(json.dumps(dict(status='PASS_WHOLE_BOUNDED_OFFLINE_OUTPUT_COLLECTION',kind=kind,source_gate=str(gate_path),source_gate_sha256=sha(gate_path),files=rows,new_model_calls=0,all_observed_rows_preserved=True,large_original_raw_remains_on8TB=True)))
'''.replace('ROOT',repr(remote)).replace('KIND',repr(a.kind)).replace('STATUS',repr(status))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(B+'/envs/revtrace-streamcorrect-20261028/bin/python')+' -B -',timeout=60);i.write(script);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();assert o.channel.recv_exit_status()==0,err.decode();r=json.loads(b);dest.mkdir();s=c.open_sftp()
 for row in r['files']:
  target=dest/row['path'];target.parent.mkdir(parents=True,exist_ok=True);s.get(row['remote'],str(target));assert target.stat().st_size==row['bytes'] and hashlib.sha256(target.read_bytes()).hexdigest()==row['sha256']
 s.close();r['all_remote_local_SHA_equal']=True;(dest/'COLLECTION_MANIFEST.json').write_bytes((json.dumps(r,indent=2)+'\n').encode());print(json.dumps(dict(status=r['status'],kind=a.kind,files=len(r['files']),bytes=sum(x['bytes'] for x in r['files']),all_SHA_equal=True,gate_sha256=r['source_gate_sha256'])))
finally:c.close()
