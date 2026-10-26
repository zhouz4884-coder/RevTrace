from pathlib import Path
import csv,hashlib,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
W=Path(__file__).resolve().parents[1];O=Path(__file__).resolve().parent
p=W/'N5_NORMAL_AGGREGATION_v1.json';data=json.loads(p.read_text());groups=data['groups'];assert len(groups)==35
methods=['fine_fair','dgft_original','standard_fair','queue_expiry','cde_age','cde_full','standard_cde']
names=['Fine (rho1)','DGFT (rho3)','Standard (rho3)','Queue / expiry','Age-only','Full CDE','Standard + CDE']
loads=['nonsaturated','near_probe','burst','finite_overload','return_low'];labels=['c4 sync','c8 stagger','c16 burst','c32 stagger','low-high-low']
metrics=['GPU_J_per_offered_audio_second','all_offered_audio_goodput_2_8']
plt.rcParams.update({'font.family':'Times New Roman','font.size':8,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','mathtext.fontset':'stix'})
fig,axes=plt.subplots(1,2,figsize=(7.2,3.05));fig.subplots_adjust(left=.19,right=.98,top=.84,bottom=.25,wspace=.22)
rows=[]
for i,(ax,metric,cmap,title) in enumerate(zip(axes,metrics,['Blues','YlGn'],['(a) GPU J / offered audio-s','(b) Legal audio goodput (2s / 8s)'])):
 a=np.zeros((7,5))
 for y,method in enumerate(methods):
  for x,load in enumerate(loads):
   g=next(g for g in groups if g['method']==method and g['workload']==load)
   a[y,x]=g[metric+'_median'];assert g['runs']==3
   if i==0:
    rows.append({k:g[k] for k in ['method','workload','runs',metric+'_median',metric+'_each',metrics[1]+'_median',metrics[1]+'_each','display_P99_median','commit_view_P99_median','all_offered_WER_percent_median','whole_run_dual_P99_passes']})
 im=ax.pcolormesh(np.arange(6)-.5,np.arange(8)-.5,a,cmap=cmap,vmin=0,vmax=105 if i==0 else 12,rasterized=False)
 ax.set_xlim(-.5,4.5);ax.set_ylim(6.5,-.5)
 ax.set_xticks(range(5),labels=labels,rotation=25,ha='right',fontsize=7)
 ax.set_yticks(range(7),labels=names if i==0 else ['']*7,fontsize=8)
 ax.tick_params(length=0);ax.set_title(title,loc='left',fontsize=8.7,pad=17)
 for y in range(7):
  for x in range(5):
   ax.text(x,y,f'{a[y,x]:.1f}' if i==0 else f'{a[y,x]:.2f}',ha='center',va='center',fontsize=7,
    color='white' if a[y,x]>(72 if i==0 else 8) else '#18232D')
 for x in range(5):ax.text(x,-.8,'3/3' if x<2 else '0/3',ha='center',va='center',fontsize=7)
 for spine in ax.spines.values():spine.set_visible(False)
fig.text(.19,.955,'Whole-run dual-P99 passes above each column; all methods retain all offered frontiers.',fontsize=7.1)
fig.text(.19,.025,'Medians of 3 fresh runs. Rho changes quality: WER and full ranges in source table/caption.',fontsize=7.1)
fig.canvas.draw();renderer=fig.canvas.get_renderer();clipped=[]
for t in fig.findobj(matplotlib.text.Text):
 if t.get_visible() and t.get_text():
  b=t.get_window_extent(renderer)
  if b.x0<fig.bbox.x0-1 or b.y0<fig.bbox.y0-1 or b.x1>fig.bbox.x1+1 or b.y1>fig.bbox.y1+1:clipped.append(t.get_text())
assert not clipped,clipped
for ext in ['pdf','svg','png']:fig.savefig(O/('normal_cost_v2.'+ext),dpi=300)
plt.close(fig)
with (O/'NORMAL_COST_SOURCE_v2.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
caption='All35independent normal-study groups:7safe methods x5finite workloads,3fresh runs per group. Numbers are medians; full repeat values are in sourceCSV/JSON, not confidence intervals. GPUenergy is per offered audio-second, with actual WAL/Consumer costs included; goodput credits only actual legal Display<=2s AND certified view<=8s and divides by original arrival+drain time. Above-column3/3 or0/3 is whole-run dual-P99 pass for every method, not the fraction of individual windows. Fine/coarse WER(%), in load order:2.010/2.010,1.741/2.239,2.551/2.806,2.229/2.349,2.375/2.539. No equal-quality dominance or extra CDE advantage is established. All groups have final certified audio frontier coverage1; this is not transcript completeness. Finite c32 workload, not infinite sustained input or measured capacity limit.'
(O/'normal_cost_v2.caption.txt').write_text(caption+'\n')
(O/'NORMAL_COST_QA_v2.json').write_text(json.dumps(dict(status='NUMERIC_SOURCE_AND_BOUNDS_PASS_VISUAL_QA_PENDING',
 input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),groups=35,runs=105,all_methods_included=True,clipped_text=clipped,
 all_low_near_pass=all(g['whole_run_dual_P99_passes']==3 for g in groups if g['workload'] in loads[:2]),
 all_pressure_fail=all(g['whole_run_dual_P99_passes']==0 for g in groups if g['workload'] in loads[2:]),
 no_new_GPU=True),indent=2)+'\n')
print('35 groups /105 runs; no pooled ratios; vector and PNG exported')
