"""Hard-bind formal CPU/OS/asset receipts, then dispatch the frozen NN queue."""
import argparse,hashlib,json,pathlib,shlex,subprocess,sys
E=pathlib.Path(__file__).resolve().parents[1];R=E.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_20261031';O=B+'/results/revtrace/dsn_strengthening_20261031';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--kind',choices=['paired','resident'],required=True);a=p.parse_args();kind=a.kind;planname='PAIRED32_v2_FROZEN.json' if kind=='paired' else 'RESIDENT4_v2_FROZEN.json';localplan=E/'paired_resident_inputs_v2'/planname;pre=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);rootgate=E/(kind.upper()+'_LAUNCH_ROOT_NOARG_v2.json');assert not rootgate.exists();rootgate.write_bytes(pre.stdout);g=json.loads(pre.stdout);assert g['code_commit']=='a13fa0a335529dc188f7e738877a3acd027ce4a7' and g['manifest_sha256']=='8cadffbfe9ffcc1eb3efdf5e2702e7afbc2ec932158c12dd197d6f0bdc334934'
script=r'''import json,pathlib,subprocess,sys,os,hashlib,time
P=pathlib.Path(PROJECT);O=pathlib.Path(OUTPUT);S=P/'paired_resident_source_v2';M=P/'PAIRED_RESIDENT_SOURCE_v2.json';sys.path.insert(0,str(S))
from common import read,sha,verify_checkout,need,put
from run_paired_campaign import validate_plan
planpath=P/PLANNAME;need(sha(planpath)==PLANSHA,'frozen plan bytes differ');plan=read(planpath);prepath=P/'PRELAUNCH_v2.json';pre=read(prepath);identity=verify_checkout(S,M,plan['controller_source_commit'])
for key,status in [('formal_Linux_CPU_gate','PASS_FORMAL_LINUX_HARNESS28_ZERO_SKIP'),('real_orphan_OS_gate','PASS_REAL_LINUX_DEAD_LEADER_ORPHAN_GROUP_CONTROL')]:
 receipt=pre[key];need(sha(receipt['path'])==receipt['sha256'],'formal prerequisite bytes changed');gate=read(receipt['path']);need(gate['status']==status and gate['controller_source_commit']==identity['source_commit'] and gate['controller_manifest_sha256']==identity['source_manifest_sha256'] and gate['shared_environment_sha256']==plan['environment_sha256'],'formal prerequisite source/env/status differs')
 if key=='formal_Linux_CPU_gate':need(gate['tests']==28 and gate['skipped']==gate['failures']==gate['errors']==gate['trained_model_calls']==0,'formal CPU count/scope failed')
 else:need(gate['GPU_or_NVML_checked'] is False and gate['CUDA_owner_query_was_synthetic'] is True and gate['confirmed_no_executing_members'] is True,'OS control scope misrepresented')
asset=read(pre['asset_byte_gate']['path']);need(asset['model_contract_files']==26 and asset['all_asset_bytes_verified'],'full model26 byte gate missing')
validate_plan(plan,M,pre,paired=(KIND=='paired'))
if KIND=='resident':need(read(O/'paired32_v2/GATE.json')['status']=='COMPLETE_PAIRED32_ACTUAL_SERVICE_AND_REFERENCE_AUDIT','resident cannot bypass paired completion gate')
need(not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=10).strip(),'GPU occupied before neural launch')
out=pathlib.Path(plan['raw_result_location']);log=O/(KIND+'_campaign_v2.log');need(not out.exists() and not log.exists(),'never overwrite neural attempt')
command=[sys.executable,'-B',str(S/('run_paired_campaign.py' if KIND=='paired' else 'run_resident_campaign.py')),'--plan',str(planpath),'--manifest',str(M),'--prelaunch',str(prepath),'--out',str(out)]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1');env.pop('PYTORCH_ALLOC_CONF',None);env.pop('CUDA_VISIBLE_DEVICES',None);env.update(plan['runtime_environment'])
record=dict(experiment_id=plan['experiment_id']+'_ROOT_LAUNCH',code_commit=identity['source_commit'],frozen_config=str(planpath),frozen_config_sha256=sha(planpath),environment_record=plan['environment_record'],environment_record_sha256=plan['environment_sha256'],raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),formal_prelaunch_sha256=sha(prepath),root_noarg_preflight_sha256=ROOTSHA,wrapper_sha256=WRAPPERSHA,formal_CPU_gate=pre['formal_Linux_CPU_gate'],real_OS_gate=pre['real_orphan_OS_gate'],asset_byte_gate=pre['asset_byte_gate']);put(O/(KIND+'_ROOT_PRELAUNCH_v2.json'),record)
with log.open('x') as stream:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=env)
proc=pathlib.Path('/proc')/str(child.pid);handle=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=command,out=str(out),log=str(log),expected_cells=plan['expected_cells'],plan_sha256=sha(planpath),prelaunch_sha256=sha(prepath));put(O/(KIND.upper()+'_HANDLE_v2.json'),handle);print(json.dumps(handle))
'''.replace('PROJECT',repr(P)).replace('OUTPUT',repr(O)).replace('PLANNAME',repr(planname)).replace('PLANSHA',repr(sha(localplan))).replace('KIND',repr(kind)).replace('ROOTSHA',repr(sha(rootgate))).replace('WRAPPERSHA',repr(sha(__file__)))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=120);i.write(script);i.flush();i.channel.shutdown_write();out=o.read();err=e.read();rc=o.channel.recv_exit_status();(E/(kind.upper()+'_LAUNCH_STDOUT_v2.txt')).write_bytes(out);(E/(kind.upper()+'_LAUNCH_STDERR_v2.txt')).write_bytes(err);assert rc==0,err.decode();(E/(kind.upper()+'_HANDLE_v2.json')).write_bytes(out);print(out.decode())
finally:c.close()
