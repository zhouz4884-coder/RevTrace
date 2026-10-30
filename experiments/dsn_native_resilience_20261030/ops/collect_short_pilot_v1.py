"""Collect bounded same-source pilot receipts only after the real six-cell terminal gate."""
import hashlib,json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];h=json.loads((F/'OPERATOR_PILOT_HANDLE_v2.json').read_bytes())
script=r"""import pathlib,json,hashlib,subprocess
h=HANDLE;out=pathlib.Path(h['out']);gate=json.loads((out/'GATE.json').read_bytes())
assert gate['status']=='PASS_ALL_FROZEN_SIX_DEVELOPMENT_TRIALS_AND_COMPLETE_TASK_REFERENCE' and gate['completed_cells']==gate['planned_cells']==6
p=pathlib.Path('/proc')/str(h['pid'])
if p.exists():
 s=(p/'stat').read_text().rsplit(')',1)[1].split();assert int(s[19])==h['start_ticks'] and s[0]=='Z','same operator still executing; do not collect'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'NN owns host; do not collect'
rows=[]
for p in sorted(out.rglob('*')):
 if not p.is_file():continue
 assert not p.is_symlink() and p.stat().st_size<20_000_000,p
 rows.append(dict(path=p.relative_to(out).as_posix(),remote=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
assert sum(r['bytes'] for r in rows)<128_000_000
print(json.dumps(dict(source_commit=h['neural_source_commit'],operator_source_commit=h['operator_source_commit'],completed_cells=6,controller_exited=True,GPU_released=True,files=rows)))
""".replace('HANDLE',repr(h))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(h['command'][0])+' -B -',timeout=30);i.write(script);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();assert o.channel.recv_exit_status()==0,err.decode();receipt=json.loads(b)
 dest=F/'SHORT_PILOT_RESULTS_v1';assert not dest.exists();dest.mkdir();s=c.open_sftp()
 for row in receipt['files']:
  target=dest/row['path'];target.parent.mkdir(parents=True,exist_ok=True);s.get(row['remote'],str(target));assert target.stat().st_size==row['bytes'] and hashlib.sha256(target.read_bytes()).hexdigest()==row['sha256'],row['path']
 s.close();receipt['all_bytes_equal']=True;(dest/'COLLECTION_MANIFEST.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
 print(json.dumps(dict(status='PASS_BOUNDED_PILOT6_COLLECTION',files=len(receipt['files']),bytes=sum(r['bytes'] for r in receipt['files']),all_bytes_equal=True,controller_exited=True,GPU_released=True)))
finally:c.close()

