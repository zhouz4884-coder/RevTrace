"""Collect all-case bounded metadata after a whole formal group and GPU drain."""
import argparse,hashlib,json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('--label',choices=['short28_v1','sustained8_v1'],required=True);a=p.parse_args();h=json.loads((F/('FORMAL_HANDLE_'+a.label+'.json')).read_bytes());dest=F/('FORMAL_'+a.label.upper()+'_RESULTS_v1')
script=r'''import pathlib,json,hashlib,subprocess
h=HANDLE;root=pathlib.Path(h['out']);p=pathlib.Path('/proc')/str(h['pid'])
if p.exists():
 state=(p/'stat').read_text().rsplit(')',1)[1].split();assert int(state[19])==h['start_ticks'] and state[0]=='Z','same campaign still executing'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
gate=json.loads((root/'GATE.json').read_bytes());plan=json.loads((root/'CONFIG.json').read_bytes());assert gate['status']=='PASS_ALL_FROZEN_FORMAL_TRIALS_AND_COMPLETE_TASK_REFERENCE' and gate['completed_cells']==gate['planned_cells']==h['expected_cells']==len(plan['cells']);assert hashlib.sha256(pathlib.Path(h['command'][h['command'].index('--plan')+1]).read_bytes()).hexdigest()==h['frozen_plan_sha256']
assert {q.name for q in (root/'cells').iterdir()}=={c['cell_id'] for c in plan['cells']};paths=[root/n for n in ('CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','PROGRESS.json','SUMMARY.json','GATE.json')]
for cell in plan['cells']:
 out=pathlib.Path(cell['out']);assert out==root/'cells'/cell['cell_id'];paths.extend(out/n for n in ('CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','METRICS_GATE.json','ORIGIN.json','SERVICE_END.json'))
rows=[]
for q in paths:
 assert q.is_file() and not q.is_symlink() and q.stat().st_size<20_000_000;rows.append(dict(path=q.relative_to(root).as_posix(),remote=str(q),bytes=q.stat().st_size,sha256=hashlib.sha256(q.read_bytes()).hexdigest()))
assert sum(x['bytes'] for x in rows)<64_000_000
print(json.dumps(dict(status='PASS_ALL_FROZEN_FORMAL_GROUP_METADATA_COLLECTION',source_commit=h['neural_source_commit'],operator_source_commit=h['operator_source_commit'],completed_cells=h['expected_cells'],frozen_plan_sha256=h['frozen_plan_sha256'],files=rows,GPU_released=True,raw_large_logs_preserved_on8TB=True,scope='All planned completed cells, no performance/outcome selection. Independent trace and bounded-series export still separate.')))
'''.replace('HANDLE',repr(h))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(h['command'][0])+' -B -',timeout=25);i.write(script);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();assert o.channel.recv_exit_status()==0,err.decode();r=json.loads(b);dest.mkdir();s=c.open_sftp()
 for row in r['files']:
  target=dest/row['path'];target.parent.mkdir(parents=True,exist_ok=True);s.get(row['remote'],str(target));assert target.stat().st_size==row['bytes'] and hashlib.sha256(target.read_bytes()).hexdigest()==row['sha256']
 s.close();r['all_remote_local_SHA_equal']=True;(dest/'COLLECTION_MANIFEST.json').write_bytes((json.dumps(r,indent=2)+'\n').encode());print(json.dumps(dict(status=r['status'],completed_cells=r['completed_cells'],files=len(r['files']),bytes=sum(x['bytes'] for x in r['files']),all_SHA_equal=True)))
finally:c.close()
