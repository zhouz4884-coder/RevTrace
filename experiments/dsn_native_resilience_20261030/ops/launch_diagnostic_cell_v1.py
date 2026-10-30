"""Launch one frozen diagnostic cell after the prior physical GPU owner exits."""
import argparse,hashlib,json,pathlib,shlex,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--label',choices=['default_r1','expanded_r0','same_input_r0','release_g_expanded_r0'],required=True);a=p.parse_args();F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1]
read=lambda p:json.loads(pathlib.Path(p).read_bytes());plan=read(F/('LONG_MEMORY_DIAGNOSTIC_v3_FROZEN.json' if a.label=='release_g_expanded_r0' else 'LONG_MEMORY_DIAGNOSTIC_v1_FROZEN.json'));cell=read(F/'LONG_MEMORY_EXPANDED_RELEASE_CELL_v3_FROZEN.json') if a.label=='release_g_expanded_r0' else read(F/'LONG_MEMORY_SAME_INPUT_CELL_v1_FROZEN.json') if a.label=='same_input_r0' else next(c for c in plan['cells'] if c['label']==a.label)
assert read(R/'experiments/repository_identity_20261027/CURRENT.json')['source_commit']==plan['source_commit'];pre=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);target=F/('DIAGNOSTIC_ROOT_NOARG_'+a.label+'.json');assert not target.exists();target.write_bytes(pre.stdout)
code=r'''import pathlib,json,hashlib,subprocess,os,sys,datetime
plan=PLAN;cell=CELL
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
sys.path.insert(0,plan['source_root']);from diagnose_long_memory import own_identity;assert own_identity(plan['source_manifest'])==plan['source_commit'];assert sha(cell['config'])==cell['config_sha256']
assert not pathlib.Path(cell['out']).exists() and not pathlib.Path(cell['log']).exists();command=[sys.executable,'-B',str(pathlib.Path(plan['source_root'])/'diagnose_long_memory.py'),'--config',cell['config'],'--manifest',plan['source_manifest'],'--out',cell['out']];env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1');env.pop('CUDA_VISIBLE_DEVICES',None)
with open(cell['log'],'x') as f:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=env)
proc=pathlib.Path('/proc')/str(child.pid);h=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=command,diagnostic_source_commit=plan['source_commit'],imported_neural_source_commit=plan['imported_neural_source_commit'],out=cell['out'],log=cell['log'],config_sha256=cell['config_sha256'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reference_only=True,actual_serving_cells=0);(pathlib.Path(plan['raw_result_location'])/('HANDLE_'+cell['label']+'.json')).write_bytes((json.dumps(h,indent=2)+'\n').encode());print(json.dumps(h))
'''.replace('PLAN',repr(plan)).replace('CELL',repr(cell))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=20);i.write(code);i.flush();i.channel.shutdown_write();b=o.read();err=e.read();assert o.channel.recv_exit_status()==0,err.decode();target=F/('LONG_MEMORY_DIAGNOSTIC_HANDLE_'+a.label+'.json');assert not target.exists();target.write_bytes(b);print(b.decode())
finally:c.close()
