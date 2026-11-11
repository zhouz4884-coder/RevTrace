"""Freeze and launch one small independent exact24 endpoint CPU diagnostic."""
import ast,hashlib,json,pathlib,shlex,subprocess,sys
E=pathlib.Path(__file__).resolve().parents[1];R=E.parents[1];S=E/'eos_source_v1';P=E/'eos_packages_v1';B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python';PROJECT=B+'/projects/revtrace_dsn_strengthening_v16_20261111/eos_v1';OUT=B+'/results/revtrace/dsn_strengthening_v16_20261111/eos_v1'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def git(p,*a):return subprocess.check_output(['git','-C',str(p),*a],text=True).strip()
def main():
 P.mkdir(exist_ok=False)
 for p in S.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
 subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--output',str(P/'DEFAULT_PREFLIGHT_BEFORE.json')],check=True,cwd=R)
 subprocess.run(['git','init','--initial-branch=codex/eos-diagnostic-v1'],cwd=S,check=True,capture_output=True)
 for k,v in [('core.autocrlf','false'),('user.name','RevTrace Research'),('user.email','source@revtrace.local')]:git(S,'config',k,v)
 git(S,'add','-A');git(S,'commit','-m','analysis: exact24 EOS and nonEOS endpoint diagnostic with frozen counterfactuals');commit=git(S,'rev-parse','HEAD')
 files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in git(S,'ls-files').splitlines()];put(P/'SOURCE.json',dict(code_commit=commit,source_commit=commit,files=files));git(S,'bundle','create',str(P/'SOURCE.bundle'),'HEAD');git(R,'fetch',str(P/'SOURCE.bundle'),'HEAD:refs/research/eos-diagnostic-v1')
 uploads={};cells=[];pilot=json.loads((E/'gpu_results/PILOT24_V2/CONFIG.json').read_bytes())
 for c in pilot['cells']:
  cid=c['cell_id'];local=E/'gpu_results/PILOT24_V2/cells'/cid;p=json.loads((local/'SUMMARY.json').read_bytes())['primary'];specs={}
  for key,name in [('config','CONFIG.json'),('origin','ORIGIN.json'),('summary','SUMMARY.json')]:
   src=local/name;dest=PROJECT+'/inputs/'+cid+'.'+name;uploads[dest]=src
   specs[key]=dict(path=dest,sha256=sha(src))
   if key in ('config','origin'):assert specs[key]['sha256']==p['raw_inputs'][key+'_sha256']
  src=E/'opportunity_ops/RESULTS_V1/cells'/cid/'ACTUAL_PAID_WORK.json';dest=PROJECT+'/inputs/'+cid+'.WORK.json';uploads[dest]=src;specs['work']=dict(path=dest,sha256=sha(src))
  specs['consumer']=dict(path=c['out']+'/consumer.jsonl',sha256=p['raw_inputs']['consumer_sha256'],jsonl=True)
  cells.append(dict(cell_id=cid,files=specs))
 src=E/'gpu_results/REFERENCE_FULL4_V2/CONFIG.json';dest=PROJECT+'/inputs/REFERENCE_CONFIG.json';uploads[dest]=src;ref=dict(path=dest,sha256=sha(src))
 cfg=dict(experiment_id='REVTRACE_EXACT24_EOS_DIAGNOSTIC_20261111_V1',source_commit=commit,source_manifest_sha256=sha(P/'SOURCE.json'),cells=cells,reference_config=ref,
  original_pilot_summary_sha256=sha(E/'gpu_results/PILOT24_V2/SUMMARY.json'),scope='Offline targeted existing24 Consumer endpoint diagnostic only; EOS-only arithmetic hypotheses, no deployed repair or original G/deadline/model/input change')
 put(P/'CONFIG.json',cfg)
 sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
 client=ssh_client()
 def remote(code):
  i,o,e=client.exec_command(shlex.quote(PY)+' -B -',timeout=90);i.write(code);i.flush();i.channel.shutdown_write();raw,err=o.read(),e.read();rc=o.channel.recv_exit_status();assert rc==0,err.decode('utf8',errors='replace');return json.loads(raw)
 try:
  env=remote("import json,platform,sys;print(json.dumps(dict(python=sys.version,executable=sys.executable,platform=platform.platform(),CUDA_VISIBLE_DEVICES='',model_calls=0,GPU_calls=0)))");put(P/'FROZEN_ENVIRONMENT.json',env)
  record=dict(experiment_id=cfg['experiment_id'],code_commit=commit,frozen_config=str(P/'CONFIG.json'),frozen_config_sha256=sha(P/'CONFIG.json'),environment_record=str(P/'FROZEN_ENVIRONMENT.json'),environment_record_sha256=sha(P/'FROZEN_ENVIRONMENT.json'),raw_result_location=OUT,aggregate_summary_location=OUT+'/SUMMARY.json',gate_decision_location=OUT+'/GATE.json');put(P/'PRELAUNCH_RECORD.json',record)
  subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--source',str(S),'--manifest',str(P/'SOURCE.json'),'--run-record',str(P/'PRELAUNCH_RECORD.json'),'--output',str(P/'EXPLICIT_PREFLIGHT.json')],check=True,cwd=R)
  remote('import pathlib,json\np=pathlib.Path('+repr(PROJECT)+');p.mkdir(parents=True,exist_ok=False);(p/"inputs").mkdir();pathlib.Path('+repr(OUT)+').parent.mkdir(parents=True,exist_ok=True);print(json.dumps(dict(staging=True)))')
  for name in ('SOURCE.json','SOURCE.bundle','CONFIG.json','FROZEN_ENVIRONMENT.json'):uploads[PROJECT+'/'+name]=P/name
  s=client.open_sftp()
  try:
   for dest,src in uploads.items():
    with s.open(dest,'wb') as f:f.write(src.read_bytes())
  finally:s.close()
  params=dict(project=PROJECT,out=OUT,commit=commit,hashes={n:sha(P/n) for n in ('SOURCE.json','SOURCE.bundle','CONFIG.json','FROZEN_ENVIRONMENT.json')})
  result=remote('PARAMS='+repr(params)+'\n'+r'''import datetime,hashlib,json,os,pathlib,platform,subprocess,sys
P=pathlib.Path(PARAMS['project']);O=pathlib.Path(PARAMS['out']);S=P/'source';C=PARAMS['commit']
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
for n,h in PARAMS['hashes'].items():assert sha(P/n)==h
compute=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=10).strip();assert not compute,'CPUwindownotidle'
subprocess.run(['git','clone','--no-checkout',str(P/'SOURCE.bundle'),str(S)],check=True,capture_output=True);subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True);subprocess.run(['git','-C',str(S),'checkout',C],check=True,capture_output=True)
m=json.loads((P/'SOURCE.json').read_bytes());cfg=json.loads((P/'CONFIG.json').read_bytes());env=json.loads((P/'FROZEN_ENVIRONMENT.json').read_bytes())
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==C==m['code_commit']==cfg['source_commit']
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain','--untracked-files=all'],text=True).strip()
assert set(subprocess.check_output(['git','-C',str(S),'ls-files'],text=True).splitlines())=={r['path'] for r in m['files']}
for r in m['files']:assert (S/r['path']).stat().st_size==r['bytes'] and sha(S/r['path'])==r['sha256']
for k,v in dict(python=sys.version,executable=sys.executable,platform=platform.platform()).items():assert env[k]==v
rec=dict(experiment_id=cfg['experiment_id'],code_commit=C,frozen_config=str(P/'CONFIG.json'),frozen_config_sha256=sha(P/'CONFIG.json'),environment_record=str(P/'FROZEN_ENVIRONMENT.json'),environment_record_sha256=sha(P/'FROZEN_ENVIRONMENT.json'),raw_result_location=str(O),aggregate_summary_location=str(O/'SUMMARY.json'),gate_decision_location=str(O/'GATE.json'),GPU_compute_processes=compute,utc=datetime.datetime.now(datetime.timezone.utc).isoformat());(P/'REMOTE_PRELAUNCH.json').write_text(json.dumps(rec,indent=2)+'\n')
cmd=[sys.executable,'-B',str(S/'run.py'),'--config',str(P/'CONFIG.json'),'--manifest',str(P/'SOURCE.json'),'--out',str(O)]
with (P/'controller.log').open('x') as f:child=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1'))
proc=pathlib.Path('/proc')/str(child.pid);tail=(proc/'stat').read_text().rsplit(')',1)[1].split();h=dict(pid=child.pid,start_ticks=int(tail[19]),cmdline_sha256=sha(proc/'cmdline'),source_commit=C,source_manifest_sha256=sha(P/'SOURCE.json'),config_sha256=sha(P/'CONFIG.json'),remote_prelaunch_sha256=sha(P/'REMOTE_PRELAUNCH.json'),out=str(O),project=str(P),GPU_calls=0);(P/'HANDLE.json').write_text(json.dumps(h,indent=2)+'\n');print(json.dumps(h))
''');put(P/'HANDLE.json',result);print(json.dumps(result,indent=2))
 finally:client.close()
if __name__=='__main__':main()
