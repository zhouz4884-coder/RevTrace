"""Frozen paired run/source analysis. No serving simulation or output concatenation."""
from pathlib import Path
from collections import defaultdict
import csv,json,sys
import numpy as np
B=Path(sys.argv[1]);O=B/'results/revtrace/elastic_20261022';A=O/'formal_audit'
rows=list(csv.DictReader((A/'SERVICE_CELLS.csv').open()));src=list(csv.DictReader((A/'SOURCE_QUALITY.csv').open()));pts=list(csv.DictReader((A/'COMMON_FRONTIER_POINTS.csv').open()));grid=list(csv.DictReader((A/'DUAL_DEADLINE_GRID.csv').open()))
assert len(rows)==24 and json.loads((A/'AUDIT_REPORT.json').read_text())['cells']==24
methods=['fixed1','fixed2','fixed3','backlog','deadline','joint'];speakers=sorted({r['source_id'] for r in src});assert len(speakers)==32
cells={};R=4;N=32;M=6;maxq=max(sum(p['cell']==r['cell'] and p['source_id']==s for p in pts) for r in rows for s in speakers)
good=np.zeros((M,R,N));we=np.zeros_like(good);wn=np.zeros_like(good);ce=np.zeros_like(good);cn=np.zeros_like(good);wall=np.zeros((M,R));energy=np.zeros((M,R));dp=np.zeros((M,R));cp=np.zeros((M,R));caps=np.zeros((M,R));cover=np.zeros((M,R));lat=np.full((M,R,N,maxq),np.nan);display_lat=lat.copy();manifest=[]
for row in rows:
 m=methods.index(row['granularity_kind']);r=int(row['cell'].rsplit('-r',1)[1]);cells[m,r]=row['cell'];quality={s['source_id']:s for s in src if s['cell']==row['cell']};qsp=[p for p in pts if p['cell']==row['cell']]
 total=sum(float(p['audio_seconds']) for p in qsp);wall[m,r]=total/float(row['xRT_to_final_consumer']);energy[m,r]=float(row['GPU_service_window_J_per_audio_s']);cover[m,r]=float(row['power_window_min_coverage']);dp[m,r]=float(row['display_P99_consumer']);cp[m,r]=float(row['commit_P99']);caps[m,r]=int(row['token_limit_events'])
 for j,s in enumerate(speakers):
  qs=[p for p in qsp if p['source_id']==s];good[m,r,j]=sum(float(p['audio_seconds']) for p in qs if p['display'] and p['commit'] and float(p['display'])<=2 and float(p['commit'])<=8)
  we[m,r,j]=float(quality[s]['WER_errors']);wn[m,r,j]=float(quality[s]['reference_words']);ce[m,r,j]=float(quality[s]['CER_errors']);cn[m,r,j]=float(quality[s]['reference_chars'])
  for k,p in enumerate(qs):lat[m,r,j,k]=float(p['commit']) if p['commit'] else np.inf;display_lat[m,r,j,k]=float(p['display']) if p['display'] else np.inf
 g=next(g for g in grid if g['cell']==row['cell'] and g['display_deadline']=='2' and g['commit_deadline']=='8');assert abs(good[m,r].sum()/wall[m,r]-float(g['delivered_goodput_audio_s_per_wall_s']))<1e-8
 assert abs(np.nanquantile(lat[m,r],.99)-cp[m,r])<1e-8
gp=good.sum(axis=2)/wall;WER=we.sum(axis=2)/wn.sum(axis=2);CER=ce.sum(axis=2)/cn.sum(axis=2);eligible=[]
for m in range(M):eligible.append(bool(WER[m].mean()<=WER[0].mean()+.005 and CER[m].mean()<=CER[0].mean()+.005 and caps[m].sum()==0))
fixed=[i for i in [0,1,2] if eligible[i]];simple=[i for i in [3,4] if eligible[i]];assert fixed
rng=np.random.default_rng(20261022);K=10000;ri=rng.integers(0,R,(K,R));si=rng.integers(0,N,(K,N));boot_gp=np.zeros((M,K));boot_we=np.zeros_like(boot_gp);boot_ce=np.zeros_like(boot_gp);boot_energy=np.zeros_like(boot_gp)
for m in range(M):
 sampled_good=good[m][ri[:,:,None],si[:,None,:]];sampled_we=we[m][ri[:,:,None],si[:,None,:]];sampled_wn=wn[m][ri[:,:,None],si[:,None,:]];sampled_ce=ce[m][ri[:,:,None],si[:,None,:]];sampled_cn=cn[m][ri[:,:,None],si[:,None,:]]
 boot_gp[m]=(sampled_good.sum(axis=2)/wall[m][ri]).mean(axis=1);boot_we[m]=sampled_we.sum(axis=(1,2))/sampled_wn.sum(axis=(1,2));boot_ce[m]=sampled_ce.sum(axis=(1,2))/sampled_cn.sum(axis=(1,2));boot_energy[m]=energy[m][ri].mean(axis=1)
def interval(v):return [float(x) for x in np.quantile(v,[.025,.975])]
quality={'WER_delta_point_pp':float((WER[5].mean()-WER[0].mean())*100),'CER_delta_point_pp':float((CER[5].mean()-CER[0].mean())*100),'WER_delta_CI_pp':[x*100 for x in interval(boot_we[5]-boot_we[0])],'CER_delta_CI_pp':[x*100 for x in interval(boot_ce[5]-boot_ce[0])],'caps_joint':int(caps[5].sum())}
quality_ok=eligible[5] and quality['WER_delta_CI_pp'][1]<=.5 and quality['CER_delta_CI_pp'][1]<=.5
comparisons={};primary=bool(quality_ok and simple)
for name,idx in [('best_fixed',fixed),('best_simple',simple)]:
 if not idx:comparisons[name]={'status':'NO_QUALITY_ELIGIBLE_COMPARATOR; success not credited'};primary=False;continue
 best=max(idx,key=lambda i:gp[i].mean());ratio=float(gp[5].mean()/gp[best].mean()-1);ci=interval(boot_gp[5]/boot_gp[idx].max(axis=0)-1);paired=(gp[5]-gp[best]).tolist();pass_=ratio>=.05 and ci[0]>0 and all(x>0 for x in paired)
 comparisons[name]={'point_comparator':methods[best],'mean_goodput_gain':ratio,'bootstrap_reselect_best_CI':ci,'paired_repeat_differences':paired,'primary_pass':pass_};primary=primary and pass_
# Commit P99 uncertainty over paired source blocks, not a spliced neural path.
boot_cp=np.zeros((M,K))
for m in range(M):
 for z in range(K):boot_cp[m,z]=np.mean([np.nanquantile(lat[m,ri[z,k],si[z],:],.99) for k in range(R)])
commit_pass=bool(quality_ok and simple);energy_pass=bool(quality_ok and simple and np.min(cover[5])>=.995);secondary={}
for name,idx in [('fixed',fixed),('simple',simple)]:
 if not idx:commit_pass=energy_pass=False;continue
 cb=min(idx,key=lambda i:cp[i].mean());cp_gain=float(1-cp[5].mean()/cp[cb].mean());cp_ci=interval(1-boot_cp[5]/boot_cp[idx].min(axis=0));gp_noninfer=interval(boot_gp[5]/boot_gp[idx].max(axis=0)-1)
 cpass=cp_gain>=.1 and cp_ci[0]>0 and gp_noninfer[0]>=-.02;commit_pass=commit_pass and cpass
 eb=min(idx,key=lambda i:energy[i].mean());egain=float(1-energy[5].mean()/energy[eb].mean());eci=interval(1-boot_energy[5]/boot_energy[idx].min(axis=0));time_ok=bool(dp[5].mean()<=1.02*dp[eb].mean() and cp[5].mean()<=1.02*cp[eb].mean());epass=egain>=.1 and eci[0]>0 and gp_noninfer[0]>=-.02 and time_ok and np.min(cover[eb])>=.995;energy_pass=energy_pass and epass
 secondary[name]={'commit_comparator':methods[cb],'commit_gain':cp_gain,'commit_bootstrap_reselect_CI':cp_ci,'Goodput_noninferiority_CI':gp_noninfer,'commit_pass':cpass,'energy_comparator':methods[eb],'energy_gain':egain,'energy_run_bootstrap_reselect_CI':eci,'display_and_commit_noninferior_2pct':time_ok,'energy_pass':epass}
summary=[]
for m,name in enumerate(methods):
 summary.append({'method':name,'n_runs':4,'n_unique_sources':32,'point_quality_eligible':eligible[m],'Goodput_mean':float(gp[m].mean()),'Goodput_each_run':gp[m].tolist(),'Display_P99_mean':float(dp[m].mean()),'Commit_P99_mean':float(cp[m].mean()),'Commit_P99_each_run':cp[m].tolist(),'GPU_window_J_audio_s_mean':float(energy[m].mean()),'GPU_window_J_audio_s_each_run':energy[m].tolist(),'WER_mean':float(WER[m].mean()),'CER_mean':float(CER[m].mean()),'caps':int(caps[m].sum()),'power_min_coverage':float(cover[m].min())})
out={'decision':'GO_C2_ELASTIC_UPGRADE_IN_BOUNDED_EVIDENCE' if primary or commit_pass or energy_pass else 'NO_GO_C2_ELASTIC_ALGORITHM_UPGRADE','primary_pass':bool(primary),'secondary_commit_pass':bool(commit_pass),'secondary_energy_pass':bool(energy_pass),'quality_pass':bool(quality_ok),'quality':quality,'primary_comparisons':comparisons,'secondary_comparisons':secondary,'summary':summary,'bootstrap':{'iterations':K,'seed':20261022,'paired_run_clusters':4,'paired_source_clusters':32,'performance_source_bootstrap_is_conditional_on_observed_queues':True,'energy_only_run_bootstrap':True},'no_output_splicing_or_reference_guided_online_selection':True,'C1_C3_original_contributions_retained':True,'scouts_not_counted_as_formal_repeats':True}
(O/'FORMAL_DECISION.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
with (O/'FORMAL_COMPARISON.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
print(json.dumps(out))
