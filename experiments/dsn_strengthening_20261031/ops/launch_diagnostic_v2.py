"""Launch the frozen complete36 CPU scan from a real file; zero model calls."""
import hashlib,json,pathlib,shlex,subprocess,sys
E=pathlib.Path(__file__).resolve().parents[1];R=E.parents[1];d=json.loads((E/'DIAG_STAGED_v2.json').read_bytes())
r=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--run-record',str(E/'diagnostic_v2_control_mirror/RUN_RECORD_ROOT_CHECK.json')],cwd=R,capture_output=True,check=True);gate=json.loads(r.stdout);assert gate['code_commit']=='ff95f04465d006f76a0e729d3fd5457c32769c1e' and gate['run_record_prelaunch_checked'] is True
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 script='C='+repr(d)+'\n'+r'''
import datetime,hashlib,json,os,pathlib,subprocess,sys
sys.path.insert(0,C['source']);from evidence_io import identity,sha
identity(C['source'],C['manifest']);assert not pathlib.Path(C['results']).exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=20).strip(),'GPU owned; no concurrent heavy audit'
pre=pathlib.Path(C['project'])/'DIAG_COMPLETE_PRELAUNCH_ROOT_GATE_v2.json';assert sha(pre)==C['root_prelaunch_sha256'];assert json.loads(pre.read_bytes())['run_record_prelaunch_checked'] is True
command=[C['python'],'-B',C['source']+'/run_diagnostics.py','--config',C['control']+'/CONFIG_FROZEN.json','--manifest',C['manifest'],'--out',C['results']]
log=pathlib.Path(C['output'])/'diagnostic_v2_run.log';assert not log.exists();env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',TMPDIR=C['output']+'/bootstrap_tmp_v2')
with log.open('x') as out:p=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True,env=env)
proc=pathlib.Path('/proc')/str(p.pid);record=dict(pid=p.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=command,source_commit='ff95f04465d006f76a0e729d3fd5457c32769c1e',raw_result_location=C['results'],log=str(log),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_model_calls=0)
handle=pathlib.Path(C['output'])/'DIAG_HANDLE_v2.json';assert not handle.exists();handle.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
'''
 i,o,e=c.exec_command(shlex.quote(d['python'])+' -B -',timeout=60);i.write(script);i.flush();i.channel.shutdown_write();raw=o.read();err=e.read();rc=o.channel.recv_exit_status();assert rc==0,err.decode('utf8',errors='replace');p=E/'DIAG_HANDLE_v2.json';assert not p.exists();p.write_bytes(raw);print(raw.decode())
finally:c.close()
