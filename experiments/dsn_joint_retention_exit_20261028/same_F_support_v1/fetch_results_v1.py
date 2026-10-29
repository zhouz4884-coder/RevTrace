"""Dry-run by default; bounded verified download only after the CPU audit PASS."""
from pathlib import Path
import argparse,datetime,hashlib,json,sys
HERE=Path(__file__).resolve().parent
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
O=B+'/results/revtrace/physical_retirement_20261028/dsn_joint_same_F_support_v1'
P=B+'/projects/revtrace_physical_retirement_20261028/dsn_joint_same_F_support_v1'

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');parser.add_argument('--output',type=Path,default=HERE/'RESULTS_v1');args=parser.parse_args()
 if not args.execute:
  print(json.dumps(dict(status='LOCAL_DRY_RUN_ONLY_NO_SSH',remote=O,local=str(args.output),condition='After full CPU same-F gate PASS and before midpoint GPU; actual raw logs remain on 8TB')));return
 sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
 from contractkv_ssh_credential import ssh_client
 client=ssh_client()
 try:
  script=r'''
from pathlib import Path
import datetime,hashlib,json,subprocess
O=Path(OUTPUT);P=Path(PROJECT)
assert json.loads((O/'GATE.json').read_text())['gate']=='PASS_ALL24_SAME_F_SUPPORT_RECOUNT'
assert not (O/'STOP.json').exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
roots={'':O,'primary':O/'primary','primary/usefulness':O/'primary/usefulness'}
rows=[]
for relative,root in roots.items():
 for path in sorted(root.iterdir()):
  if path.is_file() and path.suffix in ['.json','.csv','.log']:
   rel=(relative+'/' if relative else '')+path.name;rows.append(dict(relative=rel,path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
for name in ['HANDLE_v1.json','CPU_WINDOW_RECORD_v1.json']:
 path=P/name;rows.append(dict(relative='launch/'+name,path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
assert max(r['bytes'] for r in rows)<15_000_000 and sum(r['bytes'] for r in rows)<65_000_000
print(json.dumps(dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=rows)))
'''.replace('OUTPUT',repr(O)).replace('PROJECT',repr(P))
  i,o,e=client.exec_command('python3 -B -',timeout=45);i.write(script);i.flush();i.channel.shutdown_write();raw=o.read();error=e.read();assert o.channel.recv_exit_status()==0,error.decode();manifest=json.loads(raw)
  args.output.mkdir(parents=True,exist_ok=False);sftp=client.open_sftp()
  try:
   for row in manifest['files']:
    local=args.output/row['relative'];local.parent.mkdir(parents=True,exist_ok=True);sftp.get(row['path'],str(local));assert local.stat().st_size==row['bytes'] and hashlib.sha256(local.read_bytes()).hexdigest()==row['sha256']
  finally:sftp.close()
  receipt=dict(experiment_id='REVTRACE-DSN-RXK-SAMEF-SUPPORT-20261029-v1-BOUNDED-DELIVERY',fetched_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),all_remote_sha256_matched=True,acquisition_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),**manifest)
  with (args.output/'DOWNLOAD_VERIFICATION.json').open('x',encoding='utf8') as stream:json.dump(receipt,stream,indent=2);stream.write('\n')
  print(json.dumps(dict(output=str(args.output),files=len(manifest['files']),bytes=sum(r['bytes'] for r in manifest['files']),all_remote_sha256_matched=True)))
 finally:client.close()

if __name__=='__main__':main()
