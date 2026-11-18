"""Freeze the protocol/order before new neural outcomes and prepare strict references."""
from pathlib import Path
import copy,hashlib,importlib.util,json,random,subprocess,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_joint_retention_20261118';O=B+'/results/revtrace/dsn_native_joint_retention_20261118'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def identity(label,folder,reference=False):
 mf=E/'packages'/(label+'.json');m=json.loads(mf.read_bytes());x=dict(source_commit=m['source_commit'],source_root=P+'/'+folder+'/source',source_manifest=P+'/'+folder+'/SOURCE.json',source_manifest_sha256=sha(mf),complete_files=len(m['files']),clean=True)
 if reference:x['manifest_sha256']=sha(mf)
 return x
nn=identity('RUNTIME_SOURCE_V1','runtime_v1',True);driver=identity('CAMPAIGN_SOURCE_V1','campaign_v1',True)
selection=json.loads((E/'baseline/ORIGINAL_SELECTION_BANK.json').read_bytes());sources=sorted(selection['sources'],key=lambda s:(s['speaker_id'],s['source_id']));assert len(sources)==8
rng=random.Random(20261118);conditions=['r0s0','r0s1','r1s0','r1s1','conservative_s1'];orders={}
for s in sources:
 v=conditions.copy();rng.shuffle(v);orders[s['source_id']]=v
matrix=[]
for stage,group in [('PILOT20_V1',sources[:2]),('CONFIRM60_V1',sources[2:])]:
 blocks=[(s,rep)for rep in (0,1)for s in group];rng.shuffle(blocks)
 for s,rep in blocks:
  for cond in orders[s['source_id']][::(-1 if rep else 1)]:matrix.append(dict(stage=stage,source_id=s['source_id'],speaker_id=s['speaker_id'],repeat=rep,primary_gpu=rep,condition=cond))
assert len(matrix)==80
protocol=dict(experiment_id='REVTRACE_NATIVE_RS_20261118',actual_NN_source_commit=nn['source_commit'],campaign_source_commit=driver['source_commit'],source_bank='Same prespecified eight AISHELL speakers; not new acoustic units',sources=sources,condition_mapping={'r0s0':['ready_only',False],'r0s1':['ready_only',True],'r1s0':['fullcall',False],'r1s1':['fullcall',True],'conservative_s1':['conservative',True]},cells=matrix,order_seed=20261118,per_source_repeat_order_reversed=True,source_unit='speaker',timing_repeats=2,input_cadence_seconds=.5,D_seconds=2.,C_seconds=8.,all_offered_and_EOS_retained=True,primary='paired actual A2,8 audio duration credit and actual policy-aware compatible-view preservation',secondary=['all highwater rollback area includes necessary revisions','same-root support-classified loss area with boundary censoring','actual occupied-worker time','both-board service-origin to verified physical drain energy','full original state/C/returned-ID reference and actual-view path audit'],continuation='Technical identity/semantic/physical/audit failures preserve and stop. SLO misses, zero opportunities, ties, negative effects and resource variation are outcomes; no favorable retry or source replacement.',pilot_gate='Complete20 technical results with exact-original task and complete policy-aware audit; no effect-size or positive-difference gate',intended_final_cells=80,raw_result_root=O,new_manuscript_edits=False)
put(E/'plans/SCIENTIFIC_PROTOCOL.json',protocol)
template=json.loads((E/'baseline/ORIGINAL_TEMPLATE.json').read_bytes());template.update(source_commit=nn['source_commit']);template['settings']['source_commit']=nn['source_commit'];put(E/'plans/TEMPLATE.json',template)
env=json.loads((E/'plans/ENVIRONMENT.json').read_bytes());env['runtime']={k:v for k,v in nn.items()if k!='manifest_sha256'};env.pop('metadata_preparer_commit',None);env['metadata_preparer_operator_sha256']=sha(__file__);put(E/'plans/ENVIRONMENT.json',env)
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
with m.Remote()as c:
 for local,remote in [(E/'plans/TEMPLATE.json',P+'/TEMPLATE.json'),(E/'plans/ENVIRONMENT.json',P+'/ENVIRONMENT_v1_FROZEN.json'),(E/'baseline/ORIGINAL_SELECTION_BANK.json',P+'/SELECTION.json'),(E/'plans/SCIENTIFIC_PROTOCOL.json',P+'/SCIENTIFIC_PROTOCOL.json')]:c.put(local,remote)
 warmid=template['settings']['warmup']['source_id'];warm=next(s for s in template['settings']['model_sources']if s['source_id']==warmid)
 inputs={}
 for local,remote in [(E/'packages/CAMPAIGN_SOURCE_V1.json',driver['source_manifest']),(E/'packages/RUNTIME_SOURCE_V1.json',nn['source_manifest']),(E/'plans/TEMPLATE.json',P+'/TEMPLATE.json'),(E/'plans/ENVIRONMENT.json',P+'/ENVIRONMENT_v1_FROZEN.json'),(E/'baseline/ORIGINAL_SELECTION_BANK.json',P+'/SELECTION.json'),(E/'baseline/CPU_READINESS_V1/SUMMARY.json',O+'/CPU_READINESS_V1/SUMMARY.json')]:inputs[remote]=dict(bytes=local.stat().st_size,sha256=sha(local))
 plan=dict(experiment_id='REVTRACE_NATIVE_RS_REFERENCE8_V1_20261118',generator=driver,actual_NN=nn,base_source=nn['source_root'],base_manifest=nn['source_manifest'],actual_NN_source_commit=nn['source_commit'],selection_receipt=P+'/SELECTION.json',selection_receipt_sha256=sha(E/'baseline/ORIGINAL_SELECTION_BANK.json'),environment_record=P+'/ENVIRONMENT_v1_FROZEN.json',environment_sha256=sha(E/'plans/ENVIRONMENT.json'),environment_python=env['executable'],asset_byte_gate=O+'/CPU_READINESS_V1/SUMMARY.json',asset_byte_gate_sha256=sha(E/'baseline/CPU_READINESS_V1/SUMMARY.json'),inputs=inputs,sources=sources,expected_sources=8,expected_original_steps=sum((s['frames']+7999)//8000 for s in sources),backend=copy.deepcopy(template['settings']['backend']),warmup=copy.deepcopy(template['settings']['warmup']),warmup_source=warm,gpu=0,gpu_uuid='GPU-ef01d441-985f-50b3-6e64-5d4c3e2def3a',cache_root=B+'/cache/revtrace_native_rs_20261118',raw_result_location=O+'/REFERENCE8_V1',runtime_environment={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'},original_seed=1701,original_FP32=True,original_TF32=False,continuous_no_between_step_restore=True,restored_repeats_per_edge=2,first_failure_controls=dict(same_input_adapter_repeats=2,original_continuous_prefix_repeats=1,first_failed_boundary_per_source=True),source_replacement_after_reference_forbidden=True,reference_only=True,actual_serving_runs=0)
 put(E/'plans/REFERENCE_PLAN.json',plan);c.put(E/'plans/REFERENCE_PLAN.json',P+'/REFERENCE_PLAN.json')
 rec=dict(experiment_id=plan['experiment_id'],code_commit=driver['source_commit'],actual_NN_source_commit=nn['source_commit'],frozen_config=str((E/'plans/REFERENCE_PLAN.json').resolve()),frozen_config_sha256=sha(E/'plans/REFERENCE_PLAN.json'),environment_record=str((E/'plans/ENVIRONMENT.json').resolve()),environment_record_sha256=sha(E/'plans/ENVIRONMENT.json'),raw_result_location=plan['raw_result_location'],aggregate_summary_location=plan['raw_result_location']+'/SUMMARY.json',gate_decision_location=plan['raw_result_location']+'/GATE.json',reference_only=True,serving_runs=0)
 put(E/'launch_ops/REFERENCE8_V1/RUN_RECORD_PRELAUNCH.json',rec)
 gate=E/'launch_ops/REFERENCE8_V1/DRIVER_EXPLICIT.json';subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--source',str((E/'campaign_source').resolve()),'--manifest',str((E/'packages/CAMPAIGN_SOURCE_V1.json').resolve()),'--run-record',str((E/'launch_ops/REFERENCE8_V1/RUN_RECORD_PRELAUNCH.json').resolve()),'--output',str(gate.resolve())],cwd=R,check=True,capture_output=True)
 c.python('from pathlib import Path\nPath('+repr(P+'/root_gates')+').mkdir(parents=True,exist_ok=True)\n')
 for local in [E/'baseline/ROOT_NOARG_RUNTIME.json',gate]:c.put(local,P+'/root_gates/'+local.name)
 pre=dict(plan_sha256=sha(E/'plans/REFERENCE_PLAN.json'),root_noarg_preflight=P+'/root_gates/ROOT_NOARG_RUNTIME.json',root_noarg_preflight_sha256=sha(E/'baseline/ROOT_NOARG_RUNTIME.json'),driver_explicit_preflight=P+'/root_gates/DRIVER_EXPLICIT.json',driver_explicit_preflight_sha256=sha(gate),exclusive_GPU_window_authorized_by_root=True)
 put(E/'plans/REFERENCE_PRELAUNCH.json',pre);c.put(E/'plans/REFERENCE_PRELAUNCH.json',P+'/REFERENCE_PRELAUNCH.json')
 command=[env['executable'],'-B',driver['source_root']+'/run_reference.py','--plan',P+'/REFERENCE_PLAN.json','--manifest',driver['source_manifest'],'--prelaunch',P+'/REFERENCE_PRELAUNCH.json']
 C=dict(command=command,source=driver['source_root'],out=plan['raw_result_location'],log=O+'/REFERENCE8_V1.process.log',handle=O+'/REFERENCE8_V1.HANDLE.json',tmp=B+'/cache/revtrace_native_rs_20261118/launch_tmp')
 raw=c.python('C='+repr(C)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,subprocess
assert not Path(C['out']).exists()and not Path(C['log']).exists()and not Path(C['handle']).exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
Path(C['tmp']).mkdir(parents=True,exist_ok=True);env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',TMPDIR=C['tmp']);env.pop('CUDA_VISIBLE_DEVICES',None);env.pop('PYTORCH_ALLOC_CONF',None)
with Path(C['log']).open('xb')as f:p=subprocess.Popen(C['command'],cwd=C['source'],env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
q=Path('/proc')/str(p.pid);h=dict(pid=p.pid,start_ticks=int((q/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((q/'cmdline').read_bytes()).hexdigest(),command=C['command'],out=C['out'],log=C['log'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reference_only=True)
Path(C['handle']).write_text(json.dumps(h,indent=2)+'\n');print(json.dumps(h))
''',timeout=30)
 (E/'launch_ops/REFERENCE8_V1/HANDLE.json').write_bytes(raw+b'\n');print(raw.decode())
