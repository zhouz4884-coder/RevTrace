"""Pure config helpers. Never changes source/CURRENT, starts IO or runs a model."""
import copy,datetime,hashlib,json,pathlib,re,subprocess
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];H=F.parent/'dsn_streamcorrect_stage_handoff_20261029';I=F.parent/'dsn_streamcorrect_independent_20261029'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_resilience_20261030';O=B+'/results/revtrace/dsn_native_resilience_20261030';BDFA='bdfa3b1307d267a5a4caf6484e1ad465c39a592e'
def read(path):return json.loads(pathlib.Path(path).read_bytes())
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def put(path,value):
 path=pathlib.Path(path)
 if path.exists():raise ValueError('refuse to overwrite frozen plan/config: '+str(path))
 path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
def add_environment_arguments(parser):
 parser.add_argument('--environment-record',type=pathlib.Path)
 parser.add_argument('--environment-record-remote')
 parser.add_argument('--runtime-allocator')
def environment_override(local,remote,allocator,record=None):
 supplied=(local is not None,remote is not None,allocator is not None)
 if not any(supplied):return None
 if not all(supplied):raise ValueError('--environment-record, --environment-record-remote and --runtime-allocator must be supplied together')
 if allocator!='expandable_segments:True':raise ValueError('only the fixed evidenced expandable_segments:True control is supported')
 if not str(remote).startswith(B+'/'):raise ValueError('frozen environment remote path must stay on designated8TB')
 data=read(local) if record is None else copy.deepcopy(record);expected={'PYTORCH_CUDA_ALLOC_CONF':allocator}
 if data.get('runtime_environment')!=expected:raise ValueError('environment record and requested runtime allocator disagree')
 packages=data.get('packages')
 if not isinstance(packages,dict) or not packages or any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in packages.items()):raise ValueError('frozen actual package versions required in environment record')
 return dict(local=str(local),remote=str(remote),sha256=sha(local) if record is None else 'synthetic-self-test',runtime_environment=expected,packages=copy.deepcopy(packages),record=data)
def read_environment_override(args):return environment_override(args.environment_record,args.environment_record_remote,args.runtime_allocator)
def validate_environment_binding(environment,m,manifest,pilot):
 if environment is None:return
 data=environment['record']
 if data.get('native_source_commit')!=m['source_commit'] or data.get('source_manifest_sha256')!=sha(manifest):raise ValueError('frozen environment does not bind this final runtime source/manifest')
 if data.get('executable')!=pilot['environment_python'] or data.get('base_environment_record_sha256')!=pilot['environment_sha256']:raise ValueError('new environment changed the original executable or unbound base environment')
 base=R/'experiments/dsn_streamcorrect_adaptation_20261028/final_native_v8_evidence/FROZEN_ENVIRONMENT_v8.json'
 if sha(base)!=pilot['environment_sha256'] or read(base)['packages']!=environment['packages']:raise ValueError('new frozen environment package versions differ from original task')
def apply_environment(value,environment):
 if environment is not None:value.update(environment_record=environment['remote'],environment_sha256=environment['sha256'],runtime_environment=copy.deepcopy(environment['runtime_environment']),frozen_environment_packages=copy.deepcopy(environment['packages']))
 return value
def environment_self_test():
 fixture=dict(packages={'torch':'fixed'},runtime_environment={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'})
 assert environment_override(None,None,None) is None
 for mask in range(1,7):
  values=('local.json' if mask&1 else None,B+'/fixture.json' if mask&2 else None,'expandable_segments:True' if mask&4 else None)
  try:environment_override(*values,record=fixture)
  except ValueError:pass
  else:raise AssertionError('partial environment arguments accepted')
 valid=environment_override('local.json',B+'/fixture.json','expandable_segments:True',record=fixture);a=apply_environment({},valid);b=apply_environment({},valid);assert a['runtime_environment']==b['runtime_environment']==fixture['runtime_environment'];a['runtime_environment']['PYTORCH_CUDA_ALLOC_CONF']='changed';assert b['runtime_environment']==fixture['runtime_environment']
 bad=copy.deepcopy(fixture);bad['runtime_environment']={}
 try:environment_override('local.json',B+'/fixture.json','expandable_segments:True',record=bad)
 except ValueError:pass
 else:raise AssertionError('frozen allocator disagreement accepted')
 bad=copy.deepcopy(fixture);bad['packages']={}
 try:environment_override('local.json',B+'/fixture.json','expandable_segments:True',record=bad)
 except ValueError:pass
 else:raise AssertionError('missing package record accepted')
def runtime(manifest,source):
 manifest=pathlib.Path(manifest);source=pathlib.Path(source);m=read(manifest)
 if not re.fullmatch('[0-9a-f]{40}',m['source_commit']):raise ValueError('full actual runtime commit required')
 if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=m['source_commit']:raise ValueError('actual source commit differs')
 if subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'],text=True).strip():raise ValueError('runtime source dirty')
 tracked=set(subprocess.check_output(['git','-C',str(source),'ls-files'],text=True).splitlines())
 if tracked!={row['path'] for row in m['files']}:raise ValueError('runtime manifest incomplete')
 for row in m['files']:
  if (source/row['path']).stat().st_size!=row['bytes'] or sha(source/row['path'])!=row['sha256']:raise ValueError('runtime bytes differ')
 return m
def base_settings(commit):
 pilot=read(H/'SERVICE_PILOT_v1_FROZEN.json');cell=next(c for c in pilot['cells'] if c['arm']=='two_full_spec_early');cfg=read(H/'service_pilot_v1_configs'/pathlib.PurePosixPath(cell['config']).name);settings=copy.deepcopy(cfg['settings'])
 settings.update(source_commit=commit,max_ahead_frames=32000,record_state_telemetry=True)
 warm=next(s for s in settings['model_sources'] if s['source_id']==settings['warmup']['source_id'])
 return pilot,settings,warm
def settings_for(base,warm,source,gpu):
 value=copy.deepcopy(base);model_sources={s['source_id']:copy.deepcopy(s) for s in (warm,source)};value.update(sources=[copy.deepcopy(source)],model_sources=list(model_sources.values()),primary_gpu=gpu);return value
def cell_config(cid,arm,source,base,warm,repeat,gpu,position,block,fault,stage,reference,maximum_service,environment=None):
 return apply_environment(dict(cell_id=cid,experiment_id=cid,source_commit=base['source_commit'],arm=arm,stage=stage,cohort=source['source_id'],repeat=repeat,position=position,pair_block=block,maximum_service_seconds=maximum_service,maximum_owner_restarts=2,settings=settings_for(base,warm,source,gpu),fault=dict(kind=fault,source_id=source['source_id'],target=32000),require_reference=True,expected_owner_error_types=[],reference_details=reference['details_remote'],reference_details_sha256=reference['details_sha256'],reference_gate=reference['gate_remote'],reference_gate_sha256=reference['gate_sha256'],reference_kind=reference['kind'],scope='Same protected original FP32 ASR/C/U, two physical GPUs, fixed original neural warmup, same early whole-view Consumer, durable/recovery/lifecycle support. Original2/8 and alloffered including EOS remain; cold-fault deadline misses remain outcomes.'),environment)
def common_plan(kind,commit,manifest,version,pilot,reference,cells,seed,raw_name,runtime_source,environment=None):
 return apply_environment(dict(experiment_id='SC_NATIVE_RESILIENCE_'+kind.upper()+'_'+version.upper(),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),campaign_kind=kind,source_commit=commit,source_root=P+'/'+pathlib.Path(runtime_source).name,source_manifest=P+'/'+pathlib.Path(manifest).name,source_manifest_sha256=sha(manifest),environment_python=pilot['environment_python'],environment_record=pilot['environment_record'],environment_sha256=pilot['environment_sha256'],reference_details=reference['details_remote'],reference_details_sha256=reference['details_sha256'],reference_gate=reference['gate_remote'],reference_gate_sha256=reference['gate_sha256'],reference_kind=reference['kind'],expected_cells=len(cells),seed=seed,cells=cells,original_D2_seconds=2.,original_C8_seconds=8.,all_offered_including_EOS=True,raw_result_location=O+'/'+raw_name,aggregate_summary_location=O+'/'+raw_name+'/SUMMARY.json',gate_decision_location=O+'/'+raw_name+'/GATE.json',resource_rule='Root-owned exclusive NN queue; no simultaneous heavy remote IO/setup. Fresh trial processes; source/assets/environment/formalCPU/ref/source noarg gates precede launch.',fixed_group_rule='Complete the frozen group and preserve every failure/negative/EOS. No result-dependent source, arm order, deadline, target, maximum-service or quality normalizer changes.'),environment)
