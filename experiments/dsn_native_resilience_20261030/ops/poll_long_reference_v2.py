"""Read exact process identity and bounded oracle progress; never restart."""
import json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];h=json.loads((F/'LONG_REFERENCE_HANDLE_v2.json').read_bytes())
script=r'''import pathlib,json,hashlib,subprocess
h=HANDLE;p=pathlib.Path('/proc')/str(h['pid']);r=dict(pid=h['pid'],exists=p.exists())
if p.exists():
 s=(p/'stat').read_text().rsplit(')',1)[1].split();r.update(state=s[0],exact_start=int(s[19])==h['start_ticks'],exact_command=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==h['cmdline_sha256'])
out=pathlib.Path(h['out'])
for name in ('MODEL_READY.json','PROGRESS.json','GATE.json'):
 q=out/name
 if q.exists():
  try:
   x=json.loads(q.read_bytes());r[name]=x if name!='MODEL_READY.json' else dict(model_ready=True,actual_parameter_dtypes=x.get('actual_parameter_dtypes'),PYTORCH_CUDA_ALLOC_CONF=x.get('PYTORCH_CUDA_ALLOC_CONF'),PYTORCH_ALLOC_CONF=x.get('PYTORCH_ALLOC_CONF'))
  except json.JSONDecodeError:r[name]='temporarily partial; observation only'
r['completed_source_comparisons']={}
for q in sorted(out.glob('sources/*/RESTORE_COMPARISONS.json')):
 try:
  rows=json.loads(q.read_bytes());r['completed_source_comparisons'][q.parent.name]=dict(original_continuous_steps=len(rows),restored_steps=len(rows),mismatches=sum(not row['all_equal'] for row in rows))
 except json.JSONDecodeError:pass
log=pathlib.Path(h['log'])
if log.exists() and ('GATE.json' in r or not p.exists()):
 with log.open('rb') as stream:stream.seek(max(0,log.stat().st_size-2500));r['log_tail']=stream.read().decode(errors='replace')
r['GPU_processes']=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader'],text=True).strip()
print(json.dumps(r))
'''.replace('HANDLE',repr(h))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(h['command'][0])+' -B -',timeout=20);i.write(script);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();assert o.channel.recv_exit_status()==0,err.decode();print(b.decode())
finally:c.close()
