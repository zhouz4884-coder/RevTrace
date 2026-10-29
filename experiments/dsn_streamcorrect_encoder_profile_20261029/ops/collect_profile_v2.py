"""Collect bounded JSON only, verifying every byte; raw feature binaries stay B."""
import hashlib,json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';O=B+'/results/revtrace/dsn_streamcorrect_encoder_profile_20261029';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
script='''import hashlib,json,pathlib,subprocess
O=pathlib.Path(O_VALUE);out=O/'profile_v2';h=json.loads((O/'HANDLE_v2.json').read_text())
assert not (pathlib.Path('/proc')/str(h['pid'])).exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader'],text=True).strip()
gate=json.loads((out/'GATE.json').read_text());assert gate['calls']==13 and gate['all_workers_exited']
files=[]
for p in sorted(out.rglob('*.json')):
 b=p.read_bytes();assert len(b)<10*1024*1024;files.append(dict(relative=p.relative_to(out).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
assert sum(r['bytes'] for r in files)<12*1024*1024
print(json.dumps(dict(status='PASS_PROFILE13_TERMINAL_AND_GPU_RELEASE',gate=gate,gate_sha256=hashlib.sha256((out/'GATE.json').read_bytes()).hexdigest(),summary_sha256=hashlib.sha256((out/'SUMMARY.json').read_bytes()).hexdigest(),files=files,feature_binaries_retained_on_B=True)))
'''.replace('O_VALUE',repr(O))
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=45);i.write(script);i.flush();i.channel.shutdown_write();body=o.read().decode();err=e.read().decode();assert o.channel.recv_exit_status()==0,err
 manifest=json.loads(body);out=F/'RESULTS_v2';out.mkdir(exist_ok=False);s=c.open_sftp()
 try:
  for r in manifest['files']:
   p=out/r['relative'];p.parent.mkdir(parents=True,exist_ok=True);s.get(O+'/profile_v2/'+r['relative'],str(p));assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
 finally:s.close()
 (out/'COLLECTION_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
 (F/'RELEASE_RECEIPT_v2.json').write_text(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(status=manifest['status'],files=len(manifest['files']),bytes=sum(r['bytes'] for r in manifest['files']),gate_sha256=manifest['gate_sha256'],summary_sha256=manifest['summary_sha256'])))
finally:c.close()
