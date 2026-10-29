"""Stage and run the frozen CPU-only actual-trace extract, then SHA fetch."""
from pathlib import Path
import hashlib,json,shlex,sys
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
H=Path(__file__).resolve().parent/'trace_illustration_v1';B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_service_stability_20261028';O=B+'/results/revtrace/physical_retirement_20261028/dsn_service_stability_trace_v1'
c=ssh_client()
try:
    s=c.open_sftp()
    try:
        for name in ('TRACE_SOURCE_v1.bundle','TRACE_SOURCE_v1.json','CONFIG_v1.json'):
            target=P+'/ILLUSTRATION_'+name
            try:s.stat(target)
            except FileNotFoundError:s.put(str(H/name),target)
            else:
                with s.open(target,'rb') as f:assert f.read()==(H/name).read_bytes()
    finally:s.close()
    program=r'''
from pathlib import Path
import hashlib,json,os,subprocess,sys
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_service_stability_20261028';O=B/'results/revtrace/physical_retirement_20261028/dsn_service_stability_trace_v1';S=P/'illustration_source_v1'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'no heavy IO during timed GPU cells'
if not S.exists():subprocess.run(['git','clone','--quiet',str(P/'ILLUSTRATION_TRACE_SOURCE_v1.bundle'),str(S)],check=True)
subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True)
cfg=P/'ILLUSTRATION_CONFIG_v1.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(cfg)=='bb0b4157b892155dfee352f92969009ceee59817e0ac76d40fbd738dfdfed18a'
if not O.exists():
 subprocess.run([str(B/'envs/revbatch-cu128/bin/python'),'-B',str(S/'trace_extract.py'),'--config',str(cfg),'--config-sha256',sha(cfg),'--source-manifest',str(P/'ILLUSTRATION_TRACE_SOURCE_v1.json'),'--output',str(O)],cwd=S,check=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
assert json.loads((O/'GATE.json').read_text())['gate']=='PASS_SAME_SELECTED_HISTORY_AND_SHARED_COMPATIBLE_ROOT'
print('FETCH_MANIFEST '+json.dumps([dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in O.rglob('*.json')]))
'''
    i,o,e=c.exec_command(shlex.quote(B+'/envs/revbatch-cu128/bin/python')+' -B -',timeout=60);i.write(program);i.flush();i.channel.shutdown_write()
    raw=o.read().decode();err=e.read().decode();rc=o.channel.recv_exit_status();print(raw);print(err) if err else None;assert rc==0
    line=next(x for x in raw.splitlines() if x.startswith('FETCH_MANIFEST '));manifest=json.loads(line[len('FETCH_MANIFEST '):]);assert sum(r['bytes'] for r in manifest)<5_000_000
    D=H/'RESULTS_v1';D.mkdir(exist_ok=False);s=c.open_sftp()
    try:
        for r in manifest:
            rel=r['path'][len(O)+1:];p=D/rel;p.parent.mkdir(parents=True,exist_ok=True);s.get(r['path'],str(p))
            assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
    finally:s.close()
    with (D/'DOWNLOAD_VERIFICATION.json').open('x') as f:json.dump(manifest,f,indent=2);f.write('\n')
    print(json.dumps(dict(local=str(D),files=len(manifest),bytes=sum(r['bytes'] for r in manifest),all_SHA256_matched=True)))
finally:c.close()
