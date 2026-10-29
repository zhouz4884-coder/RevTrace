"""Upload bounded frozen plan/source, actual CPU gate, detached no-NN download."""
import hashlib,json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_streamcorrect_independent_20261029';O=B+'/results/revtrace/dsn_streamcorrect_independent_20261029';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
c=ssh_client();s=c.open_sftp()
try:
 def mkdir(p):
  if p==B:return
  assert p.startswith(B+'/')
  try:s.stat(p)
  except FileNotFoundError:mkdir(str(pathlib.PurePosixPath(p).parent));s.mkdir(p)
 mkdir(P);mkdir(O)
 files=[(F/'packages/SOURCE_v1.bundle',P+'/SOURCE_v1.bundle'),(F/'packages/SOURCE_v1.json',P+'/SOURCE_v1.json')]
 files += [(F/name,P+'/'+name) for name in ('ACQUISITION_v1_FROZEN.json','METADATA_SELECTION_v1_FROZEN.json','SELECTION_RULE_v1_FROZEN.json','ROOT_SELECTION_PREFLIGHT_v1.json')]
 for local,remote in files:
  try:s.stat(remote)
  except FileNotFoundError:s.put(str(local),remote)
  else:
   with s.open(remote,'rb') as f:assert hashlib.sha256(f.read()).hexdigest()==sha(local)
 script='''import datetime,hashlib,json,os,pathlib,platform,subprocess,sys,time
P=pathlib.Path(P_VALUE);O=pathlib.Path(O_VALUE);cfg=json.loads((P/'ACQUISITION_v1_FROZEN.json').read_text());src=P/'source_v1'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(P/'ACQUISITION_v1_FROZEN.json')==CONFIG_SHA
assert sha(P/'METADATA_SELECTION_v1_FROZEN.json')==cfg['selection_sha256']
gate=json.loads((P/'ROOT_SELECTION_PREFLIGHT_v1.json').read_text());assert gate['gate']=='SOURCE_IDENTITY_PASS' and gate['code_commit']==cfg['source_commit'] and gate['files_verified']==6
if not src.exists():
 subprocess.run(['git','init',str(src)],check=True,stdout=subprocess.DEVNULL)
 subprocess.run(['git','fetch',str(P/'SOURCE_v1.bundle'),'HEAD'],cwd=src,check=True,stdout=subprocess.DEVNULL)
 subprocess.run(['git','checkout','--detach',cfg['source_commit']],cwd=src,check=True,stdout=subprocess.DEVNULL)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()==cfg['source_commit']
assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
for f in cfg['source_files']:assert sha(src/f['path'])==f['sha256']
assert not (O/'HANDLE_v1.json').exists() and not pathlib.Path(cfg['out']).exists()
cpu=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(src),'-p','test_*.py','-v'],capture_output=True,text=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'))
(O/'CPU_CONTROLS_v1.stdout.log').write_text(cpu.stdout);(O/'CPU_CONTROLS_v1.stderr.log').write_text(cpu.stderr)
assert cpu.returncode==0 and 'Ran 13 tests' in cpu.stderr and 'skipped' not in cpu.stderr
pr=dict(status='PASS_13_CPU_CONTROLS_AND_COMPLETE_SOURCE_BEFORE_DATA',tests=13,skips=0,source_commit=cfg['source_commit'],selection_sha256=cfg['selection_sha256'],python=sys.version,executable=sys.executable,platform=platform.platform(),model_calls=0,gpu_calls=0)
(O/'CPU_GATE_v1.json').write_text(json.dumps(pr,indent=2)+'\\n')
with (O/'acquisition_v1.log').open('xb') as log:
 p=subprocess.Popen([sys.executable,'-B',str(src/'acquire_selected.py'),'--config',str(P/'ACQUISITION_v1_FROZEN.json')],cwd=P,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'))
time.sleep(.1);proc=pathlib.Path('/proc')/str(p.pid);st=(proc/'stat').read_text().rsplit(') ',1)[1].split();cmd=(proc/'cmdline').read_bytes()
h=dict(status='LAUNCHED_FOUR_PRESELECTED_PUBLIC_MEMBER_ACQUISITION_NO_NEURAL',pid=p.pid,start_ticks=st[19],command_sha256=hashlib.sha256(cmd).hexdigest(),source_commit=cfg['source_commit'],selection_sha256=cfg['selection_sha256'],config_sha256=sha(P/'ACQUISITION_v1_FROZEN.json'),CPU_gate_sha256=sha(O/'CPU_GATE_v1.json'),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),out=cfg['out'],model_calls=0,gpu_calls=0)
(O/'HANDLE_v1.json').write_text(json.dumps(h,indent=2)+'\\n');print(json.dumps(h),flush=True)
'''.replace('P_VALUE',repr(P)).replace('O_VALUE',repr(O)).replace('CONFIG_SHA',repr(sha(F/'ACQUISITION_v1_FROZEN.json')))
 i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=60);i.write(script);i.flush();i.channel.shutdown_write();body=o.read().decode();err=e.read().decode();code=o.channel.recv_exit_status()
 (F/'STAGE_CPU_LAUNCH_v1.stdout.log').write_text(body,encoding='utf-8');(F/'STAGE_CPU_LAUNCH_v1.stderr.log').write_text(err,encoding='utf-8');print(body);print(err,file=sys.stderr);assert code==0
 h=json.loads(body.splitlines()[-1]);(F/'HANDLE_v1.json').write_text(json.dumps(h,indent=2)+'\n',encoding='utf-8')
 for name in ('CPU_GATE_v1.json','CPU_CONTROLS_v1.stdout.log','CPU_CONTROLS_v1.stderr.log'):
  s.get(O+'/'+name,str(F/name))
finally:s.close();c.close()
