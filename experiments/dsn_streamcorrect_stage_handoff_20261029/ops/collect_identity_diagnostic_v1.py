import pathlib,sys,json,hashlib,shlex
T=pathlib.Path(__file__).resolve().parents[1];target=T/'identity_diagnostic_results_v1';target.mkdir(exist_ok=False)
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
program="""import pathlib,json,hashlib
R=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_stage_handoff_20261029');rows=[]
for version in (1,2,3):
 for name in ('CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','DETAILS.json','SUMMARY.json','GATE.json','failure.txt'):
  p=R/('identity_diagnostic_v'+str(version))/name
  if p.exists():rows.append(dict(relative=str(p.relative_to(R)),remote=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
print(json.dumps(rows))
"""
c=ssh_client()
try:
 i,o,e=c.exec_command('python3 -B -',timeout=20);i.write(program);i.flush();i.channel.shutdown_write();raw=o.read();err=e.read();assert o.channel.recv_exit_status()==0,err.decode();rows=json.loads(raw);s=c.open_sftp()
 try:
  for r in rows:
   p=target/r['relative'];p.parent.mkdir(parents=True,exist_ok=True);s.get(r['remote'],str(p));data=p.read_bytes();assert len(data)==r['bytes'] and hashlib.sha256(data).hexdigest()==r['sha256']
 finally:s.close()
 (target/'COLLECTION_MANIFEST.json').write_bytes(json.dumps(dict(files=rows,total_bytes=sum(r['bytes'] for r in rows)),indent=2).encode());print(json.dumps(dict(files=len(rows),bytes=sum(r['bytes'] for r in rows),all_remote_sha256_verified=True)))
finally:c.close()
