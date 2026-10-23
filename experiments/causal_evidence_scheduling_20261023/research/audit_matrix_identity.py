"""Whole formal matrix identity/fairness; no performance selection or GPU calls."""
from pathlib import Path
import hashlib,json,sys
B=Path(sys.argv[1]);O=B/'results/revtrace/ces_20261023';P=B/'projects/revtrace_ces_20261023';D=O/'matrix_identity_v1';D.mkdir(exist_ok=False)
def read(p):return json.loads(p.read_text())
def dig(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
freeze=read(O/'FORMAL_FREEZE.json');assert len(freeze['plan'])==180
source=read(P/'runtime_v4/SOURCE_MANIFEST.json');expected_source={r['path']:r['sha256'] for r in source['files']}
names=['-'.join([i['pool'],i['arrival'],i['traffic'],i['method'],'r'+str(i['repeat'])]) for i in freeze['plan']]
actual={p.name for p in (O/'formal_v1').iterdir() if p.is_dir() and (p/'result.json').exists()}
assert actual==set(names) and len(actual)==180
hardware=set();software=set();auth=set();prop_by_traffic={};session_groups={};fault_groups={};checks=[];previous_end=None
for i,name in zip(freeze['plan'],names):
 C=O/'formal_v1'/name;cfg=read(C/'config.json');pro=read(C/'provenance.json');cmd=read(O/'formal_v1'/(name+'.COMMAND.json'))
 assert cmd['frozen_item']==i and cmd['source_commit']==source['code_commit']==pro['code_commit']
 assert cfg['ces_study']['method']==i['method'] and cfg['ces_study']['traffic']==i['traffic']
 assert cfg['fine_seconds']==2 and cfg['rho']==1 and cfg['microbatch']==16 and cfg['replicas']=={'proposal':[0],'authority':[1]}
 assert cfg['result_delivery']=='row' and cfg['journal_mode']=='durable' and cfg['journal_sync_mode']=='group_ready'
 assert cfg['consumer_policy']=='two_lane' and cfg['trusted_text_binding'] and cfg['capture_worker_records']
 assert cfg['async_implementation']==('standard' if i['method']=='standard' else 'revtrace')
 assert cfg['manifest_sha256']==freeze['sources'][i['pool']]['sha256']
 assert cfg['ces_study']['calibration_sha256']==freeze['calibration_sha256']
 for path,sha in pro['source_sha256'].items():assert expected_source[path]==sha,(name,path)
 assert not cfg['authority_runtime']['online_oracle_diagnostic']
 auth.add(dig(cfg['authority_runtime']));hardware.add(pro['gpus']);software.add(dig(pro['software']))
 prop=dig(cfg['proposal_runtime']);key=i['traffic']
 assert prop_by_traffic.setdefault(key,prop)==prop
 ss=read(C/'sessions.json');key=(i['pool'],i['arrival']);sd=dig(ss)
 assert session_groups.setdefault(key,sd)==sd
 fd=dig(cfg['ces_study']['fault_plan']);key=(i['pool'],i['traffic'])
 assert fault_groups.setdefault(key,fd)==fd
 initial=read(C/'initial_states.json');assert all(v['state']['checkpoint_id']==0 for v in initial)
 with (C/'events.jsonl').open() as f:first=json.loads(f.readline())
 assert first['kind']=='run-start';start=first['t0_perf']
 if previous_end is not None:assert start>=previous_end,'actual execution order/overlap differs from frozen sequence'
 previous_end=start+read(C/'result.json')['wall_seconds_including_arrival_and_drain']
 checks.append({'cell':name,'source_config_input_order_fault_plan_fairness':'PASS'})
assert len(hardware)==len(software)==len(auth)==1
out={'status':'PASS_ALL180_FROZEN_SOURCE_HARDWARE_SOFTWARE_INPUT_AND_FAIRNESS_IDENTITIES',
 'cells':180,'actual_order_matches_frozen_plan':True,'same_FP32_authority_profile_all_methods_traffic':True,
 'same_input_audio_offsets_per_pool_arrival':True,'same_exogenous_fault_plan_per_pool_traffic':True,
 'fresh_zero_ledger_every_cell':True,'checks':checks,'source_commit':source['code_commit'],
 'new_GPU_calls':0,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(D/'SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='checks'}))
