"""Formal short24 failure coverage plus four fixed regressions, no NN launch."""
import argparse,pathlib,random,re
from formal_plan_common import F,H,I,P,O,BDFA,read,sha,put,runtime,base_settings,cell_config,common_plan,add_environment_arguments,read_environment_override,validate_environment_binding,environment_self_test
CONDITIONS=('none','duplicate_late','worker_after_asr','worker_partial_frame','owner_before_durable','owner_after_durable')
def design(seed=2026103031):
 rng=random.Random(seed);arms=['conservative','fullcall'];initial={condition:rng.randrange(2) for condition in CONDITIONS};normal=[];fault=[]
 for condition in CONDITIONS:
  for repeat in (0,1):
   order=arms[initial[condition]:]+arms[:initial[condition]]
   if repeat:order=list(reversed(order))
   block=dict(source_id='BAC009S0908W0369',condition=condition,repeat=repeat,primary_gpu=repeat,arms=order,tier='formal_failure_coverage')
   (normal if condition=='none' else fault).append(block)
 for gpu,sid in enumerate(('BAC009S0764W0209','BAC009S0905W0246')):
  order=list(arms);rng.shuffle(order);normal.append(dict(source_id=sid,condition='none',repeat=0,primary_gpu=gpu,arms=order,tier='fixed_prior_source_regression'))
 rng.shuffle(normal);rng.shuffle(fault);return normal+fault
def self_test():
 environment_self_test()
 blocks=design();assert len(blocks)==14 and sum(len(b['arms']) for b in blocks)==28;main=[b for b in blocks if b['tier']=='formal_failure_coverage'];assert len(main)==12
 for condition in CONDITIONS:
  r0=next(b for b in main if b['condition']==condition and b['repeat']==0);r1=next(b for b in main if b['condition']==condition and b['repeat']==1);assert r1['arms']==r0['arms'][::-1] and (r0['primary_gpu'],r1['primary_gpu'])==(0,1)
 assert all(b['condition']=='none' for b in blocks[:4]);assert design()==design();print('PASS short28 pure plan-shape controls; no freeze/IO/NN')
def main():
 p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--self-test',action='store_true');p.add_argument('--version',default='v1');p.add_argument('--runtime-manifest',type=pathlib.Path);p.add_argument('--runtime-source',type=pathlib.Path);p.add_argument('--reference-gate',type=pathlib.Path,default=F/'SHORT_REFERENCE_EXPORT_RESULTS_v1/GATE.json');p.add_argument('--reference-details',type=pathlib.Path,default=F/'SHORT_REFERENCE_EXPORT_RESULTS_v1/DETAILS.json');p.add_argument('--reference-gate-remote',default=P+'/SHORT85_REFERENCE_GATE_v1.json');p.add_argument('--reference-details-remote',default=P+'/SHORT85_REFERENCE_DETAILS_v1.json');add_environment_arguments(p);a=p.parse_args()
 assert re.fullmatch(r'v[1-9]\d*',a.version)
 if a.self_test:self_test();return
 environment=read_environment_override(a)
 if not a.freeze:print(dict(status='DRY_RUN_NO_MUTATION',campaign_kind='formal_short28',cells=28,main_cells=24,regression_cells=4,seed=2026103031,blocks=design(),environment_override={k:v for k,v in environment.items() if k!='record'} if environment else None));return
 assert a.runtime_manifest and a.runtime_source
 m=runtime(a.runtime_manifest,a.runtime_source);gate=read(a.reference_gate);assert gate['status']=='PASS_PRIOR_ACTUAL_BDFA_SHORT85_REFERENCE_EXPORT' and gate['measured_native_source_commit']==BDFA and gate['combined_calls']==85
 assert sha(a.reference_details)==gate['reference_details_sha256'];references=read(a.reference_details)
 ref=dict(kind='short_bdfa_static_source_mapping',details_remote=a.reference_details_remote,details_sha256=sha(a.reference_details),gate_remote=a.reference_gate_remote,gate_sha256=sha(a.reference_gate))
 pilot,base,warm=base_settings(m['source_commit']);validate_environment_binding(environment,m,a.runtime_manifest,pilot);new=read(I/'SOURCE_RECEIPT_v1.json');sources={s['source_id']:s for s in new['sources']};sources[warm['source_id']]=warm
 for sid in ('BAC009S0908W0369','BAC009S0764W0209','BAC009S0905W0246'):
  source=sources[sid];rows=[r for r in references if r['source_id']==sid];assert [r['end'] for r in rows]==list(range(8000,source['frames'],8000))+[source['frames']]
  for row in rows:assert row['original_full_start_cut']['contract']['stage_execution']['source_commit']==row['original_full_cut']['contract']['stage_execution']['source_commit']==BDFA
 folder=F/('formal_short28_'+a.version+'_configs');folder.mkdir();cells=[];blocks=design()
 for block_index,block in enumerate(blocks):
  for arm in block['arms']:
   sid=block['source_id'];cid=f'SC_FORMAL_SHORT28_{a.version}_{sid}_{block["condition"]}_{arm}_r{block["repeat"]}';cfg=cell_config(cid,arm,sources[sid],base,warm,block['repeat'],block['primary_gpu'],len(cells),block_index,block['condition'],block['tier'],ref,240,environment=environment);path=folder/(cid+'.json');put(path,cfg);cells.append(dict(cell_id=cid,source_id=sid,repeat=block['repeat'],primary_gpu=block['primary_gpu'],pair_block=block_index,tier=block['tier'],arm=arm,fault_kind=block['condition'],config=P+'/formal_short28_'+a.version+'_configs/'+path.name,config_sha256=sha(path),out=O+'/formal_short28_'+a.version+'/cells/'+cid,log=O+'/formal_short28_'+a.version+'/logs/'+cid+'.log'))
 plan=common_plan('formal_short28',m['source_commit'],a.runtime_manifest,a.version,pilot,ref,cells,2026103031,'formal_short28_'+a.version,a.runtime_source,environment=environment);plan.update(main_failure_coverage_cells=24,fixed_regression_cells=4,conditions=list(CONDITIONS),fault_target_samples=32000,normal_and_regression_blocks_first=True,paired_blocks=blocks,repeat_arm_order_reversed=True,primary_gpu_equals_repeat_for_main=True,expected_canonical_transitions=476,scope='Formal same-source controlled failure coverage,24main+4prior-source normal regressions. Repeated timing/fault observations are not independent acoustic samples or natural failure prevalence; reference uses prior actual protected calls and no output replay in service.')
 target=F/('FORMAL_SHORT28_'+a.version+'_FROZEN.json');put(target,plan);print(dict(status='FROZEN_FORMAL_SHORT28_NO_NN',plan=str(target),sha256=sha(target),source_commit=m['source_commit'],cells=28))
if __name__=='__main__':main()
