"""Bounded full875+875 receipts; large complete native arrays stay on8TB."""
import hashlib,json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];h=json.loads((F/'LONG_REFERENCE_HANDLE_v2.json').read_bytes());dest=F/'LONG_REFERENCE_RESULTS_v2'
script=r'''import pathlib,json,hashlib,subprocess
h=HANDLE;root=pathlib.Path(h['out']);p=pathlib.Path('/proc')/str(h['pid'])
if p.exists():
 state=(p/'stat').read_text().rsplit(')',1)[1].split();assert int(state[19])==h['start_ticks'] and state[0]=='Z','same reference still executing'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'NN owns host'
def sha(path):
 value=hashlib.sha256()
 with pathlib.Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(4*1024*1024),b''):value.update(block)
 return value.hexdigest()
gate=json.loads((root/'GATE.json').read_bytes());assert gate['status']=='PASS_CONTINUOUS_ORIGINAL_AND_ALL_RESTORED_NATIVE_EDGES' and gate['source_commit']==h['source_commit'];assert gate['reference_full_calls']==gate['restored_full_calls']==875 and gate['all_original_full_state_C_IDs_equal'];assert sha(root/'DETAILS.json')==gate['reference_details_sha256']
comparisons=json.loads((root/'RESTORE_COMPARISONS.json').read_bytes());assert len(comparisons)==875 and all(row['all_equal'] for row in comparisons)
keep={'CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','MODEL_READY.json','PROGRESS.json','SUMMARY.json','GATE.json','DETAILS_INDEX.json','INPUT_MANIFEST.json','RESTORE_COMPARISONS.json','STATE_BOUNDARIES.jsonl','LAST_ORIGINAL_INPUT.json'};rows=[]
for q in sorted(root.rglob('*')):
 if not q.is_file():continue
 assert not q.is_symlink();rows.append(dict(path=q.relative_to(root).as_posix(),remote=str(q),bytes=q.stat().st_size,sha256=sha(q),download=q.name in keep and q.stat().st_size<20_000_000))
assert sum(x['bytes'] for x in rows if x['download'])<96_000_000
print(json.dumps(dict(status='PASS_BOUNDED_COMPLETE_ORIGINAL875_RESTORED875_COLLECTION',source_commit=h['source_commit'],files=rows,original_full_calls=875,restored_full_calls=875,all_original_complete_state_C_IDs_equal=True,GPU_released=True,large_raw_arrays_preserved_on8TB=True,reference_only=True,actual_serving_cells=0)))
'''.replace('HANDLE',repr(h))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(h['command'][0])+' -B -',timeout=30);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();assert o.channel.recv_exit_status()==0,stderr.decode();r=json.loads(stdout);dest.mkdir();s=c.open_sftp()
 for row in r['files']:
  if not row['download']:continue
  target=dest/row['path'];target.parent.mkdir(parents=True,exist_ok=True);s.get(row['remote'],str(target));assert target.stat().st_size==row['bytes'] and hashlib.sha256(target.read_bytes()).hexdigest()==row['sha256']
 s.close();r['all_downloaded_remote_local_SHA_equal']=True;(dest/'COLLECTION_MANIFEST.json').write_bytes((json.dumps(r,indent=2)+'\n').encode());print(json.dumps(dict(status=r['status'],files=len(r['files']),downloaded_files=sum(x['download'] for x in r['files']),downloaded_bytes=sum(x['bytes'] for x in r['files'] if x['download']),all_SHA_equal=True,source_commit=h['source_commit'],original_full_calls=875,restored_full_calls=875)))
finally:c.close()
