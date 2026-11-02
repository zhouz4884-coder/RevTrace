"""Read-only availability precheck of the immutable historical trace indexes."""
from pathlib import Path
import hashlib,json,shlex,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1]
names=['S0_N5_SCAN_v2.json','S0_CK5_SCAN_v2.json'];entries={};indexes=[]
for name in names:
    p=R/'experiments/legal_progress_20261026'/name;b=p.read_bytes();j=json.loads(b)
    indexes.append(dict(path=p.relative_to(R).as_posix(),sha256=hashlib.sha256(b).hexdigest(),attempts=len(j['attempts'])))
    for a in j['attempts']:
        for row in a.get('trace_identity',[]):
            if row['path'] in entries:assert entries[row['path']]==row
            entries[row['path']]=row
env=json.loads((E/'REMOTE_PRELAUNCH_ENVIRONMENT_v1.json').read_bytes())
script='ROWS='+repr(list(entries.values()))+'\n'+r'''
import datetime,json,pathlib
bad=[];total=0
for row in ROWS:
 p=pathlib.Path(row['path']);assert p.is_relative_to(pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'))
 if not p.is_file():bad.append(dict(path=str(p),reason='missing'))
 elif p.stat().st_size!=row['bytes']:bad.append(dict(path=str(p),reason='size_mismatch',observed=p.stat().st_size,expected=row['bytes']))
 else:total+=p.stat().st_size
print(json.dumps(dict(scope='Availability/size precheck, not input SHA validation or analysis result',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=len(ROWS),matching_files=len(ROWS)-len(bad),matching_bytes=total,problems=bad)))
'''
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(env['executable'])+' -B -',timeout=120)
 i.write(script);i.flush();i.channel.shutdown_write();raw=o.read();err=e.read();rc=o.channel.recv_exit_status()
 assert rc==0,err.decode(errors='replace')[-1500:]
 result=json.loads(raw);result['input_indexes']=indexes
 result['local_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 target=E/'history/RAW_AVAILABILITY_PRECHECK.json';target.parent.mkdir(exist_ok=True)
 assert not target.exists();target.write_bytes((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({k:v for k,v in result.items() if k!='problems'}));print(json.dumps(dict(problems=result['problems'][:8])))
finally:c.close()
