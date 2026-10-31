"""Small identity-bound observation; never restarts or kills a model process."""
import argparse,hashlib,json,pathlib,shlex,sys,time
E=pathlib.Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('--kind',choices=['paired','resident','buffer','interference'],required=True);a=p.parse_args();h=json.loads((E/('BUFFER4_HANDLE_v1.json' if a.kind=='buffer' else 'INTERFERENCE_HANDLE_v1.json' if a.kind=='interference' else a.kind.upper()+'_HANDLE_v2.json')).read_bytes())
script=r'''import pathlib,json,hashlib
h=HANDLE;p=pathlib.Path('/proc')/str(h['pid']);out=pathlib.Path(h['out']);r=dict(pid=h['pid'],process_exists=p.exists(),observation_scope='bounded status only; no NN/source/raw-log processing')
if p.exists():
 stat=(p/'stat').read_text().rsplit(')',1)[1].split();r.update(process_state=stat[0],start_ticks_match=int(stat[19])==h['start_ticks'],cmdline_match=hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==h['cmdline_sha256'])
for name in ['PROGRESS.json','GATE.json','SMOKE8_DECISION.json','SMOKE2_DECISION.json']:
 path=out/name
 if path.exists():
  try:r[name]=json.loads(path.read_bytes())
  except json.JSONDecodeError:r[name]='CURRENT_WRITE_IN_PROGRESS'
partial=out/'PARTIAL_RESULTS.json'
if partial.exists():
 try:
  rows=json.loads(partial.read_bytes());r['completed_cells']=len(rows);r['completed_rows']=[dict(cell_id=x['cell_id'],version=x.get('version'),strategy=x.get('strategy',x.get('arm')),repeat=x['repeat'],all_three_gates_and_exit_pass=x.get('all_three_gates_and_exit_pass'),gates={k:v.get('status') for k,v in x.get('gates',{}).items()},primary={k:v for k,v in x.get('primary',x.get('summary',{}).get('primary',{})).items() if k!='frontiers'},semantic=x.get('semantic',x.get('summary',{}).get('integrity',{}).get('original_reference',{}))) for x in rows]
 except json.JSONDecodeError:r['partial_currently_writing']=True
if isinstance(r.get('GATE.json'),dict) and str(r['GATE.json'].get('status','')).startswith('FAIL'):
 log=pathlib.Path(h['log']);r['log_tail']=log.read_text()[-14000:] if log.exists() else ''
print(json.dumps(r))
'''.replace('HANDLE',repr(h))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(h['command'][0])+' -B -',timeout=20);i.write(script);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();rc=o.channel.recv_exit_status();assert rc==0,err.decode();value=json.loads(b);target=E/(a.kind.upper()+'_POLL_v2_'+str(time.time_ns())+'.json');target.write_bytes(b);print(json.dumps({k:v for k,v in value.items() if k!='completed_rows'}));print(json.dumps(dict(last_completed=value.get('completed_rows',[])[-4:]),ensure_ascii=False))
finally:c.close()
