"""Read-only audit status; retrieve the completed ordinary JSON receipt once."""
import datetime
import hashlib
import json
import pathlib
import shlex
import sys

T=pathlib.Path(__file__).resolve().parents[1]
REMOTE=r'''
import hashlib,json,pathlib
A=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_20261028/assets_v1/independent_full_sha_v2')
r={}
for name in ('HANDLE.json','GATE.json','RECEIPT.json'):
 p=A/name
 if p.exists():r[name]=json.loads(p.read_text())
h=r.get('HANDLE.json')
if h:
 p=pathlib.Path('/proc')/str(h['pid']);r['verifier_proc_exists']=p.exists()
 if p.exists():
  f=(p/'stat').read_text().rsplit(')',1)[1].split();r['verifier_process']=dict(identity_matches=int(f[19])==h['start_ticks'],state=f[0],
   cmdline_sha256=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest())
p=A/'SAFE_LOG.jsonl'
if p.exists():
 with p.open('rb') as f:f.seek(max(0,p.stat().st_size-2000));r['safe_log_tail']=f.read().decode()
print(json.dumps(r))
'''
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
    _,stdout,stderr=c.exec_command('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revbatch-cu128/bin/python -B -c '+shlex.quote(REMOTE),timeout=40)
    data=stdout.read();err=stderr.read();rc=stdout.channel.recv_exit_status()
    if rc:raise RuntimeError('Audit status observation failed; this is not worker death')
    result=json.loads(data);result['observed_local_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt=result.get('RECEIPT.json');folder=T/'acquisition_monitor_v1'
    if receipt:
        path=folder/'FINAL_FULL_SHA_ASSET_RECEIPT.json';body=json.dumps(receipt,indent=2).encode()
        if path.exists():assert path.read_bytes()==body
        else:path.write_bytes(body)
        result['local_receipt']=str(path);result['local_receipt_sha256']=hashlib.sha256(body).hexdigest()
        result['receipt_summary']={k:v for k,v in receipt.items() if k not in ('checks','auxiliary_dependency_checks')}
        del result['RECEIPT.json']
    print(json.dumps(result,indent=2))
finally:c.close()
