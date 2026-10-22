"""Operational predeclared gate; timing-only optimistic screen, no neural splicing."""
from pathlib import Path
from collections import defaultdict
import csv,json,math,sys
B=Path(sys.argv[1]);O=B/'results/revtrace/elastic_20261022';A=O/'fixed_scout_audit'
rows=list(csv.DictReader((A/'SERVICE_CELLS.csv').open()));points=list(csv.DictReader((A/'COMMON_FRONTIER_POINTS.csv').open()));grid=list(csv.DictReader((A/'DUAL_DEADLINE_GRID.csv').open()));demand=list(csv.DictReader((A/'AUTHORITY_DEMAND.csv').open()))
assert len(rows)==9 and json.loads((A/'AUDIT_REPORT.json').read_text())['cells']==9
def q99(v):
 if any(x is None for x in v):return math.inf
 v=sorted(v);x=(len(v)-1)*.99;i=int(x);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(x-i)
lookup={(r['arrival'],int(r['rho'])):r for r in rows};info=[]
for r in rows:
 rr=dict(r);base=lookup[r['arrival'],1];quality_ok=float(r['WER'])<=float(base['WER'])+.005 and float(r['CER'])<=float(base['CER'])+.005
 g=next(g for g in grid if g['cell']==r['cell'] and g['display_deadline']=='2' and g['commit_deadline']=='8');rs=[p for p in points if p['cell']==r['cell']]
 phases={}
 for phase in ['low_initial','high','low_final']:
  ps=[p for p in rs if p['phase_by_release']==phase]
  if ps:phases[phase]={'frontiers':len(ps),'commit_p99':q99([float(p['commit']) if p['commit'] else None for p in ps]),'display_p99':q99([float(p['display']) if p['display'] else None for p in ps]),'good_audio_seconds_2_8':sum(float(p['audio_seconds']) for p in ps if p['display'] and p['commit'] and float(p['display'])<=2 and float(p['commit'])<=8)}
 rr.update(quality_eligible=quality_ok and int(r['token_limit_events'])==0,Goodput_2_8=float(g['delivered_goodput_audio_s_per_wall_s']),phases=phases)
 info.append(rr)
 ldir=O/'fixed_scout'/r['cell'];es=[json.loads(l) for l in (ldir/'events.jsonl').read_text().splitlines()];spans=set((e['gpu_model_started'],e['gpu_model_completed']) for e in es if e['kind']=='executor-complete' and e['role']=='authority')
 rr['authority_model_fraction_high_window']=sum(max(0,min(b,42)-max(a,10)) for a,b in spans)/32
 jobs=[e for e in es if e['kind']=='enqueue' and e['role']=='authority'];rr['max_authority_ready_to_enqueue']=max(e['enqueue_perf']-e['audio_ready_perf'] for e in jobs)
lhl=[r for r in info if r['arrival']=='low-high-low'];valid=[r for r in lhl if r['quality_eligible']];assert valid
bestgp=max(valid,key=lambda r:r['Goodput_2_8']);d=next(d for d in demand if d['cell']==bestgp['cell']);ps=[p for p in points if p['cell']==bestgp['cell']];total=sum(float(p['audio_seconds']) for p in ps);last_release=float(d['arrival_horizon']);ub=total/last_release;headroom=ub/bestgp['Goodput_2_8']-1
pressure=any(r['authority_model_fraction_high_window']>=.8 or r['max_authority_ready_to_enqueue']>=1 for r in lhl)
primary=headroom>=.05 and pressure
byrho={int(r['rho']):r for r in lhl};fine,coarse=byrho[1],byrho[3]
low_benefit=coarse['phases']['low_initial']['commit_p99']-fine['phases']['low_initial']['commit_p99']
high_benefit=fine['phases']['high']['commit_p99']-coarse['phases']['high']['commit_p99']
timings=defaultdict(list)
for p in points:
 if p['cell'] in {r['cell'] for r in lhl}:timings[p['source_id'],p['frontier_audio_seconds']].append(float(p['commit']) if p['commit'] else math.inf)
optimistic=q99([min(v) for v in timings.values()]);bestcommit=min(float(r['commit_P99']) for r in valid);commit_space=low_benefit>=1 and high_benefit>=1 and optimistic<=.9*bestcommit
cheap=min(lhl,key=lambda r:float(r['GPU_J_per_audio_s']));cheapestvalid=min(valid,key=lambda r:float(r['GPU_J_per_audio_s']));energy_space=not cheap['quality_eligible'] and float(cheapestvalid['GPU_J_per_audio_s'])>=1.1*float(cheap['GPU_J_per_audio_s'])
gate=primary or commit_space or energy_space
out={'decision':'GO_MINIMAL_ELASTIC_PROTOTYPE' if gate else 'NO_GO_ELASTIC_UPGRADE_ON_FROZEN_SPACE_GATE','fixed_scouts':info,'nonstationary':{'independent_sources':16,'total_audio_seconds':total,'last_required_audio_release':last_release,'absolute_goodput_upper_bound':ub,'best_quality_eligible_fixed_rho':int(bestgp['rho']),'best_fixed_goodput':bestgp['Goodput_2_8'],'absolute_primary_headroom_fraction':headroom,'actual_authority_pressure':pressure,'primary_space_trigger':primary,'low_phase_fine_commit_advantage_seconds':low_benefit,'high_phase_coarse_commit_advantage_seconds':high_benefit,'timing_only_optimistic_commit_p99':optimistic,'best_quality_eligible_fixed_commit_p99':bestcommit,'commit_space_trigger':commit_space,'energy_quality_space_trigger':energy_space},'timing_screen_is_not_a_legal_dynamic_oracle':True,'canonical_outputs_not_combined':True,'no_neural_or_GPU_dynamic_results_claimed':True,'rule_file':'SPACE_GATE_OPERATIONAL.md','scout_n_per_configuration':1,'not_a_universal_impossibility_or_statistical_acceptance_claim':True}
(O/'SPACE_GATE.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
print(json.dumps({'decision':out['decision'],'nonstationary':out['nonstationary'],'cells':[{k:r[k] for k in ['cell','rho','Goodput_2_8','display_P99_consumer','commit_P99','GPU_J_per_audio_s','WER','CER','quality_eligible']} for r in info]}))
