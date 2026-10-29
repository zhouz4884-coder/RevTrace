"""Execute only in the root/SC-allocated short CPU/IO window, after NN release."""
import argparse,pathlib,json,hashlib,sys,shlex
T=pathlib.Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args();assert a.execute,'explicit orchestration invocation required after resource allocation'
localplan=T/'OLD_FIDELITY_PLAN_v1_FROZEN.json';plan=json.loads(localplan.read_bytes());RP=str(pathlib.PurePosixPath(plan['analysis_source_root']).parent)
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 s=c.open_sftp()
 for local,target in [(T/'packages/OLD_FIDELITY_SOURCE_v1.bundle',RP+'/OLD_FIDELITY_SOURCE_v1.bundle'),(T/'packages/OLD_FIDELITY_SOURCE_v1.json',plan['analysis_source_manifest']),(localplan,RP+'/OLD_FIDELITY_PLAN_v1_FROZEN.json'),(T/'ORIGINAL_FIXED_REFERENCES_v1.json',plan['original_fixed_references'])]:
  data=local.read_bytes()
  try:
   with s.open(target,'rb') as f:assert f.read()==data,'staged bytes differ; never replace'
  except FileNotFoundError:
   with s.open(target,'wb') as f:f.write(data)
 s.close()
 program="""import pathlib,json,subprocess,sys,os,hashlib,time
P=pathlib.Path(RP_VALUE);plan=json.loads((P/'OLD_FIDELITY_PLAN_v1_FROZEN.json').read_bytes());out=pathlib.Path(plan['raw_result_location']);source=pathlib.Path(plan['analysis_source_root'])
assert hashlib.sha256((P/'OLD_FIDELITY_PLAN_v1_FROZEN.json').read_bytes()).hexdigest()==PLAN_SHA_VALUE
assert hashlib.sha256(pathlib.Path(plan['analysis_source_manifest']).read_bytes()).hexdigest()==plan['analysis_source_manifest_sha256']
gate=json.loads((pathlib.Path(plan['new_neural_out'])/'GATE.json').read_bytes());assert gate['status']=='PASS_FOUR_SOURCE_PROTECTED_PACKET_ORIGINAL_C_U_EQUIVALENCE' and gate['full_steps']==69 and gate['source_commit']==plan['neural_source_commit']
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'NN still owns GPU: no CPU analysis overlap'
if not source.exists():
 subprocess.run(['git','clone','--no-checkout',str(P/'OLD_FIDELITY_SOURCE_v1.bundle'),str(source)],check=True);subprocess.run(['git','-C',str(source),'config','core.autocrlf','false'],check=True);subprocess.run(['git','-C',str(source),'checkout',plan['analysis_source_commit']],check=True)
assert not out.exists(),'never replace analysis output'
begin=time.perf_counter();r=subprocess.run([sys.executable,'-B',str(source/'old_fidelity.py'),'--plan',str(P/'OLD_FIDELITY_PLAN_v1_FROZEN.json'),'--manifest',plan['analysis_source_manifest'],'--out',str(out)],capture_output=True,text=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'))
(P/'OLD_FIDELITY_STDOUT_v1.txt').write_text(r.stdout);(P/'OLD_FIDELITY_STDERR_v1.txt').write_text(r.stderr)
print(json.dumps(dict(returncode=r.returncode,elapsed_seconds=time.perf_counter()-begin,out=str(out),gate_sha256=hashlib.sha256((out/'GATE.json').read_bytes()).hexdigest(),gate=json.loads((out/'GATE.json').read_bytes()))));assert r.returncode==0,r.stderr
""".replace('RP_VALUE',repr(RP)).replace('PLAN_SHA_VALUE',repr(sha(localplan)))
 i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=120);i.write(program);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(T/'OLD_FIDELITY_EXEC_STDOUT_v1.txt').write_bytes(stdout);(T/'OLD_FIDELITY_EXEC_STDERR_v1.txt').write_bytes(stderr);print(stdout.decode());print(stderr.decode(),file=sys.stderr)
 # Preserve and collect both a successful gate and a failed diagnostic.
 check="""import pathlib,json,hashlib
O=pathlib.Path(OUT_VALUE);P=pathlib.Path(RP_VALUE);rows=[]
for p in sorted(O.iterdir()):
 if p.is_file():rows.append(dict(path=p.name,remote=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
for name in ('OLD_FIDELITY_STDOUT_v1.txt','OLD_FIDELITY_STDERR_v1.txt'):
 p=P/name
 if p.exists():rows.append(dict(path=name,remote=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
print(json.dumps(rows))
""".replace('OUT_VALUE',repr(plan['raw_result_location'])).replace('RP_VALUE',repr(RP))
 i,o,e=c.exec_command('python3 -B -',timeout=20);i.write(check);i.flush();i.channel.shutdown_write();rows=json.loads(o.read());err=e.read();assert o.channel.recv_exit_status()==0,err.decode();dest=T/'old_native69_task_fidelity_RESULTS_v1';dest.mkdir(exist_ok=False);s=c.open_sftp()
 try:
  for r in rows:
   target=dest/r['path'];s.get(r['remote'],str(target));data=target.read_bytes();assert len(data)==r['bytes'] and hashlib.sha256(data).hexdigest()==r['sha256']
 finally:s.close()
 (dest/'COLLECTION_MANIFEST.json').write_bytes(json.dumps(dict(files=rows,total_bytes=sum(r['bytes'] for r in rows),all_remote_sha256_verified=True),indent=2).encode());assert rc==0,'analysis failed; error retained and collected'
finally:c.close()
