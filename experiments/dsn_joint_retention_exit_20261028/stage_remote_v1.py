"""Stage the frozen R/K plan and independent analysis; no GPU execution."""
import hashlib,json,shlex,sys
from pathlib import Path
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
T=Path(__file__).resolve().parent
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_physical_retirement_20261028'
mapping={'PLAN_v1.json':'DSN_JOINT_PLAN_v1_FROZEN.json','ANALYSIS_SOURCE_v1.json':'DSN_JOINT_ANALYSIS_SOURCE_v1.json','ANALYSIS_SOURCE_v1.bundle':'DSN_JOINT_ANALYSIS_SOURCE_v1.bundle'}
program=r"""
import hashlib,json,subprocess
from pathlib import Path
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_physical_retirement_20261028';A=P/'dsn_joint_analysis_source_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P/'DSN_JOINT_PLAN_v1_FROZEN.json')=='d5da167c84b185dc38c2f5db345b7ba9bd0b501b087fcb06216e8f449a7a7f8e'
M=P/'DSN_JOINT_ANALYSIS_SOURCE_v1.json';assert sha(M)=='b7f31431d15c30534c342aca5bbae6315bd4e58ac0e8ac1d9069c63ee0c92c8a'
m=json.loads(M.read_text())
if not A.exists():subprocess.run(['git','clone','--quiet',str(P/'DSN_JOINT_ANALYSIS_SOURCE_v1.bundle'),str(A)],check=True)
def git(*args):return subprocess.check_output(['git','-C',str(A),*args],text=True).strip()
assert git('rev-parse','HEAD')==m['code_commit'] and not git('status','--porcelain','--untracked-files=all')
assert set(git('ls-files').splitlines())=={r['path'] for r in m['files']}
for r in m['files']:assert (A/r['path']).stat().st_size==r['bytes'] and sha(A/r['path'])==r['sha256']
print(json.dumps(dict(gate='STAGED_FULL_SOURCE_AND_PLAN_IDENTITY',analysis_commit=m['code_commit'],new_model_calls=0,plan=str(P/'DSN_JOINT_PLAN_v1_FROZEN.json'))))
"""
c=ssh_client()
try:
 s=c.open_sftp()
 try:
  for local,name in mapping.items():
   dest=P+'/'+name
   try:
    with s.open(dest,'rb') as f:old=f.read()
    assert old==(T/local).read_bytes(),'never replace frozen input'
   except FileNotFoundError:s.put(str(T/local),dest)
 finally:s.close()
 i,o,e=c.exec_command(shlex.quote(B+'/envs/revbatch-cu128/bin/python')+' -B -',timeout=45);i.write(program);i.flush();i.channel.shutdown_write()
 print(o.read().decode());err=e.read().decode();print(err) if err else None;assert o.channel.recv_exit_status()==0
finally:c.close()
