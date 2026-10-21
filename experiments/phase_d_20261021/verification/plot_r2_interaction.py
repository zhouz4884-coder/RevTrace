from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
W=Path(__file__).resolve().parent;groups=json.loads((W/'R2_MATCHED_SUMMARY.json').read_text())['groups'];order=[(False,'snapshot'),(False,'two_lane'),(True,'snapshot'),(True,'two_lane')];labels=['Neither','View only','Chain only','Both'];colors=['#767676','#3775BA','#B64342','#42949E']
plt.rcParams.update({'font.family':['Arial','DejaVu Sans'],'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','pdf.fonttype':42})
fig,axs=plt.subplots(2,2,figsize=(10,6.3))
for row,rho in enumerate([1,3]):
 for i,((keep,view),label,color) in enumerate(zip(order,labels,colors)):
  r=next(g for g in groups if g['rho']==rho and g['retention']==keep and g['consumer']==view);runs=r['rollback_runs']
  axs[row,0].bar(i,sorted(runs)[1],color=color,alpha=.72,edgecolor='#272727',linewidth=.8)
  axs[row,0].scatter([i-.1,i,i+.1],runs,c='#272727',s=18,zorder=4)
  value=r['display_P99_consumer_median'];axs[row,1].bar(i,value,color=color,alpha=.72,edgecolor='#272727',linewidth=.8);axs[row,1].text(i,value+.15,f'{value:.2f}',ha='center',fontsize=9)
 for ax in axs[row]:ax.set_xticks(range(4),labels);ax.set_ylim(bottom=0);ax.grid(axis='y',alpha=.12)
 axs[row,0].set_ylabel(('Fine' if rho==1 else 'Coarse')+' audio retractions / run')
 axs[row,1].set_ylabel('Actual view-application P99 (s)')
axs[0,0].set_title('Three repeats, independently audited; same canonical content')
axs[0,1].set_title('Latency includes actual local FIFO consumer')
fig.tight_layout(pad=1.5);out=W/'figures';out.mkdir(exist_ok=True)
for ext in ['svg','pdf','png']:fig.savefig(out/('R2_CHAIN_VIEW_INTERACTION.'+ext),dpi=220,facecolor='white')
