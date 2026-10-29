"""Run only after the exact profile worker finishes; all raw data remains on B."""
import pathlib,json,sys,hashlib,shlex
T=pathlib.Path(__file__).resolve().parents[1];plan=json.loads((T/'PLAN_v1_FROZEN.json').read_text(encoding='utf-8'));P=str(pathlib.PurePosixPath(plan['source_root']).parent);O=str(pathlib.PurePosixPath(plan['raw_result_location']).parent)
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 code=r'''import pathlib,json,hashlib,subprocess,sys
O=pathlib.Path(O_VALUE);h=json.loads((O/'HANDLE_v1.json').read_text());proc=pathlib.Path('/proc')/str(h['pid']);assert not proc.exists(),'original controller still alive; do not duplicate'
assert json.loads((O/'campaign_v1/GATE.json').read_text())['status']=='PASS_BOUNDED_ORIGINAL_STAGE_PROFILE_AND_PACKET_CONTROLS'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
print('PASS_PROFILE_TERMINAL_AND_GPU_IDLE')
'''.replace('O_VALUE',repr(O))
 def execute(code,timeout=60):
  i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=timeout);i.write(code);i.flush();i.channel.shutdown_write();out=o.read().decode();err=e.read().decode();rc=o.channel.recv_exit_status();print(out);print(err,file=sys.stderr);assert rc==0;return out
 execute(code)
 s=c.open_sftp()
 for local,name in [(T/'packages/ANALYSIS_SOURCE_v1.bundle','ANALYSIS_SOURCE_v1.bundle'),(T/'packages/ANALYSIS_SOURCE_v1.json','ANALYSIS_SOURCE_v1.json')]:
  path=P+'/'+name;body=local.read_bytes()
  try:
   with s.open(path,'rb') as f:assert f.read()==body
  except FileNotFoundError:
   with s.open(path,'wb') as f:f.write(body)
 s.close()
 code=r'''import pathlib,json,hashlib,subprocess,os,sys
P=pathlib.Path(P_VALUE);O=pathlib.Path(O_VALUE);S=P/'analysis_source_v1';m=json.loads((P/'ANALYSIS_SOURCE_v1.json').read_text())
if not S.exists():
 subprocess.run(['git','clone','--no-checkout',str(P/'ANALYSIS_SOURCE_v1.bundle'),str(S)],check=True);subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True);subprocess.run(['git','-C',str(S),'checkout',m['source_commit']],check=True)
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==m['source_commit'];assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain','--untracked-files=all'],text=True).strip()
assert set(subprocess.check_output(['git','-C',str(S),'ls-files'],text=True).splitlines())=={r['path'] for r in m['files']}
for r in m['files']:
 data=(S/r['path']).read_bytes();assert len(data)==r['bytes'] and hashlib.sha256(data).hexdigest()==r['sha256']
out=O/'analysis_v1';log=O/'analysis_v1.log';assert not out.exists() and not log.exists()
cmd=[sys.executable,'-B',str(S/'summarize.py'),'--campaign',str(O/'campaign_v1'),'--out',str(out),'--prior-ready','/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_20261028/ready_opportunity_v1/SUMMARY.json']
with log.open('x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'))
assert r.returncode==0,'preserve analysis failure and log; never repeat same output'
print((out/'GATE.json').read_text());print(log.read_text())
'''.replace('P_VALUE',repr(P)).replace('O_VALUE',repr(O))
 execute(code)
 s=c.open_sftp();dest=T/'RESULTS_v1';dest.mkdir(exist_ok=False);rels=['campaign_v1/'+name for name in ['GATE.json','SUMMARY.json','RUN_RECORD.json','ENVIRONMENT.json','FROZEN_PLAN.json']]+['analysis_v1/'+name for name in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json']]
 for run in plan['runs']:
  rels+=['campaign_v1/'+run['run_id']+'/'+name for name in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','ACTUAL_PARAMETER_DTYPES.json','WARMUP.json']]
 receipts=[];total=0
 for rel in rels:
  remote=O+'/'+rel;st=s.stat(remote);assert st.st_size<5_000_000;total+=st.st_size;assert total<15_000_000
  local=dest/rel;local.parent.mkdir(parents=True,exist_ok=True);s.get(remote,str(local));body=local.read_bytes()
  with s.open(remote,'rb') as f:assert f.read()==body
  receipts.append(dict(path=rel,remote=remote,bytes=len(body),sha256=hashlib.sha256(body).hexdigest()))
 s.close();(dest/'COLLECTION_MANIFEST.json').write_text(json.dumps(dict(files=receipts,total_bytes=total,all_remote_bytes_matched=True,large_raw_tensors_and_audio_on_B_only=True),indent=2),encoding='utf-8');print(json.dumps(dict(files=len(receipts),total_bytes=total,collection=str(dest)),indent=2))
finally:c.close()
