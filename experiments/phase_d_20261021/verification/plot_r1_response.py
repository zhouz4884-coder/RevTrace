from pathlib import Path
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
W=Path(__file__).resolve().parent;rows=list(csv.DictReader((W/'collected_early/R1_CELLS.csv').open()))
plt.rcParams.update({'font.family':['Arial','DejaVu Sans'],'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','pdf.fonttype':42})
fig,axs=plt.subplots(1,2,figsize=(10,3.6));colors={1:'#0F4D92',3:'#B64342'}
for rho in [1,3]:
 for rep in range(3):
  rs=sorted([r for r in rows if int(r['rho'])==rho and int(r['repeat'])==rep],key=lambda r:float(r['hold']))
  for ax,key in zip(axs,['rollback_per_commit','withdrawn_audio_wall_area']):ax.plot([float(r['hold']) for r in rs],[float(r[key])*(100 if key=='rollback_per_commit' else 1) for r in rs],marker='o',lw=1.5,color=colors[rho],alpha=.8,label=('Fine' if rho==1 else 'Coarse') if rep==0 else None)
for ax in axs:ax.set_xlabel('Artificial authority delivery hold (s)');ax.set_xticks([0,.75,1.5]);ax.grid(axis='y',alpha=.16)
axs[0].set_ylabel('Audio retractions / canonical publications (%)');axs[0].legend(frameon=False);axs[1].set_ylabel('Withdrawn audio-time area (s²)')
fig.suptitle('Controlled timing intervention; canonical content histories unchanged',fontsize=11);fig.tight_layout();out=W/'figures';out.mkdir(exist_ok=True)
for ext in ['svg','pdf','png']:fig.savefig(out/('R1_CONTROLLED_DELIVERY_RESPONSE.'+ext),dpi=220,facecolor='white')
