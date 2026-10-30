"""Collect bounded fixed-memory controls after all physical NN owners exit."""
import hashlib,json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';O=B+'/results/revtrace/dsn_native_resilience_20261030';dest=F/'LONG_MEMORY_DIAGNOSTIC_RESULTS_v1'
script=r'''import pathlib,json,hashlib,subprocess,datetime
O=pathlib.Path(OUTPUT)
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
bad=O/'long_memory_diagnostic_v2/release_g_r0';gate=bad/'GATE.json'
if not gate.exists():
 log=(O/'long_memory_diagnostic_v2/release_g_r0.log').read_text(errors='replace');assert 'Cannot access storage of SparseTensorImpl' in log
 x=dict(status='FAIL_DIAGNOSTIC_OBSERVER_SPARSE_STORAGE_COMPATIBILITY_PRESERVED',diagnostic_source_commit='a2144058bdbb496eee965c62720f79e6776da584',imported_neural_source_commit='9492d3f9cb35e2b2849ec020817750a221248f0e',producer='Root operator terminal classification after observed process exit; original driver crashed before producing its gate',logged_exception_type='NotImplementedError',completed_streamed_rows=0,raw_log_sha256=hashlib.sha256((O/'long_memory_diagnostic_v2/release_g_r0.log').read_bytes()).hexdigest(),reference_only=True,actual_serving_cells=0,recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());gate.write_bytes((json.dumps(x,indent=2)+'\n').encode())
rows=[]
for version in ('v1','v2','v3'):
 root=O/('long_memory_diagnostic_'+version)
 for p in sorted(root.rglob('*')):
  if not p.is_file():continue
  assert not p.is_symlink();rows.append(dict(path=version+'/'+p.relative_to(root).as_posix(),remote=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),download=p.stat().st_size<20_000_000))
assert sum(x['bytes'] for x in rows if x['download'])<128_000_000
final=json.loads((O/'long_memory_diagnostic_v3/release_g_expanded_r0/GATE.json').read_bytes());assert final['status']=='PASS_RELEASE_G96_AND_ALL_FIXED_ACTUAL_PREFIX_AND_INPUT_CONTROLS' and final['all_fixed_actual_complete_state_C_IDs_equal'] and final['complete_rows']==96
print(json.dumps(dict(status='PASS_BOUNDED_FIXED_MEMORY_CONTROL_COLLECTION',files=rows,final_gate=final,GPU_released=True,original_failed_C_U_not_relabelled=True)))
'''.replace('OUTPUT',repr(O))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(B+'/envs/revtrace-streamcorrect-20261028/bin/python')+' -B -',timeout=30);i.write(script);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();assert o.channel.recv_exit_status()==0,err.decode();r=json.loads(b);dest.mkdir();s=c.open_sftp()
 for row in r['files']:
  if not row['download']:continue
  p=dest/row['path'];p.parent.mkdir(parents=True,exist_ok=True);s.get(row['remote'],str(p));assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
 s.close();r['all_downloaded_remote_local_SHA_equal']=True;(dest/'COLLECTION_MANIFEST.json').write_bytes((json.dumps(r,indent=2)+'\n').encode());print(json.dumps(dict(status=r['status'],files=len(r['files']),downloaded_files=sum(x['download'] for x in r['files']),downloaded_bytes=sum(x['bytes'] for x in r['files'] if x['download']),all_SHA_equal=True,final_gate=r['final_gate']['status'])))
finally:c.close()
