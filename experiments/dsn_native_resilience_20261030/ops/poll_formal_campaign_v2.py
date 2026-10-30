"""Read exact formal operator identity/counts only; no performance prefixes."""
import argparse,json,pathlib,shlex,sys
p=argparse.ArgumentParser();p.add_argument('--label',choices=['short28_v1','sustained8_v1'],required=True);a=p.parse_args();F=pathlib.Path(__file__).resolve().parents[1];h=json.loads((F/('FORMAL_HANDLE_'+a.label+'.json')).read_bytes())
script=r'''import pathlib,json,hashlib,subprocess
h=HANDLE;p=pathlib.Path('/proc')/str(h['pid']);r=dict(pid=h['pid'],exists=p.exists())
if p.exists():
 s=(p/'stat').read_text().rsplit(')',1)[1].split();r.update(state=s[0],exact_start=int(s[19])==h['start_ticks'],exact_command=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==h['cmdline_sha256'])
out=pathlib.Path(h['out'])
for name in ('PROGRESS.json','GATE.json'):
 q=out/name
 if q.exists():
  try:
   value=json.loads(q.read_bytes());r[name]=value if name=='PROGRESS.json' else {k:v for k,v in value.items() if k not in ('cells',)}
  except json.JSONDecodeError:r[name]='temporarily partial; observation only'
if 'GATE.json' in r:
 log=pathlib.Path(h['log'])
 with log.open('rb') as f:f.seek(max(0,log.stat().st_size-4000));r['log_tail']=f.read().decode(errors='replace')
r['GPU_processes']=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader'],text=True).strip();print(json.dumps(r))
'''.replace('HANDLE',repr(h))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(h['command'][0])+' -B -',timeout=20);i.write(script);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();assert o.channel.recv_exit_status()==0,err.decode();print(b.decode())
finally:c.close()
