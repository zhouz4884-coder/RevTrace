"""Root-allocated old14 CPU analysis only; no model calls or runtime edits."""
from pathlib import Path
import hashlib,json,shlex,sys
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
H=Path(__file__).resolve().parent;B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_content_20261029';O=B+'/results/revtrace/dsn_native_content_20261029/analysis_v1'
assert json.loads((H/'CPU_CONTROLS_v2/GATE.json').read_text(encoding='utf8'))['gate']=='PASS_EIGHT_CPU_CONTENT_CONTROLS'
c=ssh_client()
try:
 s=c.open_sftp()
 try:
  try:s.stat(P)
  except FileNotFoundError:s.mkdir(P)
  for name in ('SOURCE_v1.bundle','SOURCE_v1.json','CONFIG_v1.json'):
   target=P+'/'+name
   try:s.stat(target)
   except FileNotFoundError:s.put(str(H/name),target)
   else:
    with s.open(target,'rb') as f:assert f.read()==(H/name).read_bytes()
 finally:s.close()
 program=r'''
from pathlib import Path
import hashlib,json,os,subprocess,sys
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_native_content_20261029';O=B/'results/revtrace/dsn_native_content_20261029/analysis_v1';S=P/'source_v1'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'no IO during timed models'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P/'SOURCE_v1.json')=='c610cdf68440d6e905e88b0350e0d081a232f044018efa51a4973a8f33d60092'
assert sha(P/'CONFIG_v1.json')=='f773b46d6a24cbf6ea6c43fb7984d6345266733cf95260d85adecf1557d3c140'
if not S.exists():subprocess.run(['git','clone','-c','core.autocrlf=false','--quiet',str(P/'SOURCE_v1.bundle'),str(S)],check=True)
sys.path.insert(0,str(S));from analyze_content import source_gate
source_gate(json.loads((P/'SOURCE_v1.json').read_text()))
O.parent.mkdir(parents=True,exist_ok=True)
assert not O.exists()
cmd=[str(B/'envs/revbatch-cu128/bin/python'),'-B',str(S/'analyze_content.py'),'--config',str(P/'CONFIG_v1.json'),'--source-manifest',str(P/'SOURCE_v1.json'),'--out',str(O)]
with (O.parent/'PROCESS_v1.log').open('x') as log:r=subprocess.run(cmd,cwd=S,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES=''),stdout=log,stderr=subprocess.STDOUT)
if r.returncode:
 print((O.parent/'PROCESS_v1.log').read_text()[-4000:]);raise RuntimeError('preserved content recount failure')
assert json.loads((O/'GATE.json').read_text())['gate']=='PASS_ALL14_ORIGINAL_CREDIT_AND_TEXT_ENDPOINTS'
print('FETCH_MANIFEST '+json.dumps([dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(O.glob('*.json'))]))
'''
 i,o,e=c.exec_command(shlex.quote(B+'/envs/revbatch-cu128/bin/python')+' -B -',timeout=60);i.write(program);i.flush();i.channel.shutdown_write();raw=o.read().decode();err=e.read().decode();rc=o.channel.recv_exit_status();print(raw);print(err) if err else None;assert rc==0
 manifest=json.loads(next(x[len('FETCH_MANIFEST '):] for x in raw.splitlines() if x.startswith('FETCH_MANIFEST ')))
 assert sum(r['bytes'] for r in manifest)<=32000000
 D=H/'RESULTS_v1';D.mkdir(exist_ok=False);s=c.open_sftp()
 try:
  for r in manifest:
   p=D/r['path'].rsplit('/',1)[-1];s.get(r['path'],str(p));assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
 finally:s.close()
 with (D/'DOWNLOAD_VERIFICATION.json').open('x',encoding='utf8') as f:json.dump(manifest,f,indent=2);f.write('\n')
 print(json.dumps(dict(local=str(D),files=len(manifest),bytes=sum(r['bytes'] for r in manifest),all_SHA256_matched=True)))
finally:c.close()
