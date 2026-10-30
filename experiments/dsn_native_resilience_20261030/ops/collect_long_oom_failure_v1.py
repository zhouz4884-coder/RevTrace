"""Bounded original OOM evidence; never invents lost in-memory complete cuts."""
import hashlib,json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];h=json.loads((F/'LONG_REFERENCE_HANDLE_v1.json').read_bytes());dest=F/'LONG_REFERENCE_OOM_RESULTS_v1'
script=r'''import pathlib,json,hashlib
h=HANDLE;out=pathlib.Path(h['out']);p=pathlib.Path('/proc')/str(h['pid']);assert not p.exists(),'original failed process still exists'
gate=json.loads((out/'GATE.json').read_bytes());assert gate['status']=='FAIL_CONTINUOUS_ORACLE_SETUP_OR_EXECUTION_PRESERVED';rows=[]
for q in sorted(out.rglob('*')):
 if q.is_file():
  assert not q.is_symlink() and q.stat().st_size<20_000_000
  rows.append(dict(path=q.relative_to(out).as_posix(),remote=str(q),bytes=q.stat().st_size,sha256=hashlib.sha256(q.read_bytes()).hexdigest()))
assert sum(x['bytes'] for x in rows)<64_000_000
print(json.dumps(dict(status='ORIGINAL_CONTINUOUS_WRAPPER_OOM_PRESERVED',source_commit=h['source_commit'],files=rows,complete_continuous_details_persisted=(out/'DETAILS.json').exists() or bool(list(out.glob('sources/*/CONTINUOUS_DETAILS.json'))),no_recovered_RAM_cut_claim=True)))
'''.replace('HANDLE',repr(h))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(h['command'][0])+' -B -',timeout=20);i.write(script);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();assert o.channel.recv_exit_status()==0,err.decode();r=json.loads(b);dest.mkdir();s=c.open_sftp()
 for row in r['files']:
  p=dest/row['path'];p.parent.mkdir(parents=True,exist_ok=True);s.get(row['remote'],str(p));assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
 s.close();r['all_remote_local_SHA_equal']=True;(dest/'COLLECTION_MANIFEST.json').write_bytes((json.dumps(r,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in r.items() if k!='files'},indent=2))
finally:c.close()
