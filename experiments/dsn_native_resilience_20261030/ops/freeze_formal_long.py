"""Formal synthetic state-boundary8, bound only to a real matching oracle gate."""
import argparse,pathlib,random,re
from formal_plan_common import F,P,O,read,sha,put,runtime,base_settings,cell_config,common_plan,add_environment_arguments,read_environment_override,validate_environment_binding,environment_self_test
D=F.parent/'dsn_native_sustained_20261030'
def design(ids,seed=2026103041):
 rng=random.Random(seed);arms=['conservative','fullcall'];initial={sid:rng.randrange(2) for sid in ids};blocks=[]
 for sid in ids:
  for repeat in (0,1):
   order=arms[initial[sid]:]+arms[:initial[sid]]
   if repeat:order=list(reversed(order))
   blocks.append(dict(source_id=sid,repeat=repeat,primary_gpu=repeat,arms=order))
 rng.shuffle(blocks);return blocks
def self_test():
 environment_self_test()
 blocks=design(['sourceA','sourceB']);assert len(blocks)==4 and sum(len(b['arms']) for b in blocks)==8
 for sid in ('sourceA','sourceB'):
  a=next(b for b in blocks if b['source_id']==sid and b['repeat']==0);b=next(b for b in blocks if b['source_id']==sid and b['repeat']==1);assert b['arms']==a['arms'][::-1] and (a['primary_gpu'],b['primary_gpu'])==(0,1)
 print('PASS sustained8 pure plan-shape controls; no freeze/IO/NN')
def main():
 p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--self-test',action='store_true');p.add_argument('--version',default='v1');p.add_argument('--runtime-manifest',type=pathlib.Path);p.add_argument('--runtime-source',type=pathlib.Path);p.add_argument('--reference-gate',type=pathlib.Path,default=F/'LONG_REFERENCE_RESULTS_v1/GATE.json');p.add_argument('--reference-details',type=pathlib.Path);p.add_argument('--reference-gate-remote',default=O+'/long_reference_v1/GATE.json');p.add_argument('--reference-details-remote',default=O+'/long_reference_v1/DETAILS.json');add_environment_arguments(p);a=p.parse_args()
 assert re.fullmatch(r'v[1-9]\d*',a.version)
 if a.self_test:self_test();return
 environment=read_environment_override(a)
 if not a.freeze:print(dict(status='DRY_RUN_NO_MUTATION',campaign_kind='formal_sustained8',cells=8,seed=2026103041,source_receipt=str(D/'SOURCE_RECEIPT_v1.json'),strict_reference_gate_required=True,max_service_seconds=1200,environment_override={k:v for k,v in environment.items() if k!='record'} if environment else None));return
 assert a.runtime_manifest and a.runtime_source
 m=runtime(a.runtime_manifest,a.runtime_source);gate=read(a.reference_gate);assert gate['status']=='PASS_CONTINUOUS_ORIGINAL_AND_ALL_RESTORED_NATIVE_EDGES' and gate['source_commit']==m['source_commit'] and gate['all_original_full_state_C_IDs_equal']
 receipt=read(D/'SOURCE_RECEIPT_v1.json');assert sha(D/'SOURCE_RECEIPT_v1.json')=='b8bb687eee1f9edd1fb32367c438cc1de9b1ae19b770afd98b7cd4fb68f19cb5';sources=receipt['sources'];assert len(sources)==2 and all(s['synthetic_concatenated_utterances'] and len(s['parts'])==24 for s in sources)
 steps=sum((s['frames']+7999)//8000 for s in sources);assert steps==875 and gate['reference_full_calls']==gate['restored_full_calls']==steps
 details_sha=gate['reference_details_sha256']
 if a.reference_details:assert sha(a.reference_details)==details_sha
 ref=dict(kind='continuous_original',details_remote=a.reference_details_remote,details_sha256=details_sha,gate_remote=a.reference_gate_remote,gate_sha256=sha(a.reference_gate));pilot,base,warm=base_settings(m['source_commit']);validate_environment_binding(environment,m,a.runtime_manifest,pilot);byid={s['source_id']:s for s in sources};blocks=design(list(byid));folder=F/('formal_sustained8_'+a.version+'_configs');folder.mkdir();cells=[]
 for bi,block in enumerate(blocks):
  for arm in block['arms']:
   sid=block['source_id'];cid=f'SC_FORMAL_SUSTAINED8_{a.version}_{sid}_{arm}_r{block["repeat"]}';cfg=cell_config(cid,arm,byid[sid],base,warm,block['repeat'],block['primary_gpu'],len(cells),bi,'none','formal_synthetic_sustained_state_boundary',ref,1200,environment=environment);cfg.update(synthetic_concatenated_utterances=True,source_recipe_sha256=sha(D/'METADATA_SELECTION_v1_FROZEN.json'),reset_at_part_boundaries=False);path=folder/(cid+'.json');put(path,cfg);cells.append(dict(cell_id=cid,source_id=sid,repeat=block['repeat'],primary_gpu=block['primary_gpu'],pair_block=bi,arm=arm,fault_kind='none',config=P+'/formal_sustained8_'+a.version+'_configs/'+path.name,config_sha256=sha(path),out=O+'/formal_sustained8_'+a.version+'/cells/'+cid,log=O+'/formal_sustained8_'+a.version+'/logs/'+cid+'.log'))
 plan=common_plan('formal_sustained8',m['source_commit'],a.runtime_manifest,a.version,pilot,ref,cells,2026103041,'formal_sustained8_'+a.version,a.runtime_source,environment=environment);plan.update(acoustic_speakers=2,synthetic_streams=2,utterances_per_stream=24,source_receipt_sha256=sha(D/'SOURCE_RECEIPT_v1.json'),total_unique_audio_seconds=sum(s['frames']/16000 for s in sources),offered_audio_seconds_per_arm=2*sum(s['frames']/16000 for s in sources),offered_frontiers_per_arm=2*steps,expected_canonical_transitions=4*steps,paired_blocks=blocks,repeat_arm_order_reversed=True,primary_gpu_equals_repeat=True,maximum_service_seconds=1200,scope='Two metadata-first synthetic concatenated streams from unused speakers,208/228seconds,2armsx2fresh=8. Not natural continuous recordings, not a pure time-length/concurrency capacity curve, not eight acoustic samples. Exact matching continuous-original oracle; no state field ignored.')
 target=F/('FORMAL_SUSTAINED8_'+a.version+'_FROZEN.json');put(target,plan);print(dict(status='FROZEN_FORMAL_SUSTAINED8_NO_NN',plan=str(target),sha256=sha(target),source_commit=m['source_commit'],cells=8,offered_frontiers_per_arm=plan['offered_frontiers_per_arm']))
if __name__=='__main__':main()
