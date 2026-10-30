"""Read-only remote identity/resource and pinned author-state source preflight."""
import base64,hashlib,json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1]
H=R/'experiments/dsn_streamcorrect_stage_handoff_20261029'
cfg=json.loads(next((H/'service_pilot_v1_configs').glob('*.json')).read_bytes())['settings']
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
script=r"""import base64,hashlib,json,pathlib,subprocess,shutil,platform
A=pathlib.Path(AUTHOR);B=pathlib.Path(BASE)
def git(*a):return subprocess.check_output(['git','-C',str(A),*a],text=True).strip()
assert git('rev-parse','HEAD')==COMMIT
names=[p for p in git('ls-tree','-r','--name-only','HEAD').splitlines() if p.endswith('.py') and ('token_buffer' in p or p=='simul_whisper/config.py')]
files=[]
for name in names:
 raw=(A/name).read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();assert git('rev-parse','HEAD:'+name)==blob
 files.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),blob=blob,base64=base64.b64encode(raw).decode()))
print(json.dumps(dict(host=platform.node(),python=platform.python_version(),author_commit=git('rev-parse','HEAD'),author_clean=not bool(git('status','--porcelain','--untracked-files=all')),gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.used,utilization.gpu','--format=csv,noheader'],text=True),compute_processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True),disk=shutil.disk_usage(B)._asdict(),memory=[x for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith(('MemTotal','MemAvailable'))],files=files)))
""".replace('AUTHOR',repr(cfg['backend']['author_root'])).replace('BASE',repr(B)).replace('COMMIT',repr(cfg['backend']['contract']['native_author_commit']))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(cfg['backend'].get('environment_python',B+'/envs/revtrace-streamcorrect-20261028/bin/python'))+' -B -',timeout=30)
 i.write(script);i.flush();i.channel.shutdown_write();raw=o.read();err=e.read();rc=o.channel.recv_exit_status();assert rc==0,err.decode()
 d=json.loads(raw);p=F/'author_reference';p.mkdir(exist_ok=True)
 for f in d['files']:
  v=base64.b64decode(f.pop('base64'));assert hashlib.sha256(v).hexdigest()==f['sha256'];target=p/f['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(v)
 (F/'REMOTE_READONLY_ENVIRONMENT_v1.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf8')
 print(json.dumps(d,indent=2))
finally:c.close()

