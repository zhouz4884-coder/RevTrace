import csv,gzip,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
W=Path(__file__).resolve().parent;rows=list(csv.DictReader((W/'collected_final/R0/FRONTIER_TRAJECTORIES.csv').open()));cases=list(csv.DictReader(gzip.open(W/'collected_final/R0/ROLLBACK_EVENT_CASES.csv.gz','rt',encoding='utf8')));timing=json.loads((W/'tables/TIMELINE_COMPONENTS.json').read_text())['records']
plt.rcParams.update({'font.family':['Arial','DejaVu Sans'],'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','pdf.fonttype':42})
fig,axs=plt.subplots(3,1,figsize=(11,10),sharex=True,sharey=True)
names=['fine_certified-decoupled-obs1-r0','coarse-decoupled-obs1-r0','coarse-segment-obs1-r0'];styles=[('released','#767676','--'),('committed','#0F4D92','-'),('visible','#B64342','-'),('ever','#42949E',':')]
for ax,name in zip(axs,names):
 rs=sorted([r for r in rows if r['cell']==name and r['session_id']=='0'],key=lambda r:float(r['time']));cs=[r for r in cases if r['cell']==name and r['session_id']=='0']
 for col,color,line in styles:
  if col=='released':
   duration=max(float(r['released']) for r in rs);end=max(float(r['time']) for r in rs);ax.plot([0,duration,end],[0,duration,duration],label=col,color=color,ls=line,lw=1.7)
  else:ax.step([0]+[float(r['time']) for r in rs],[0]+[float(r[col]) for r in rs],where='post',label=col,color=color,ls=line,lw=1.7)
 for r in cs:
  if float(r['rollback_audio_seconds'])>0:ax.annotate('',xy=(float(r['time']),float(r['new_committed_frontier'])),xytext=(float(r['time']),float(r['pre_visible_frontier'])),arrowprops={'arrowstyle':'->','color':'#B64342','lw':.8})
 for t in [r for r in timing if r['cell']==name]:
  for y,left,right,color in [(-1.8,t['enqueue'],t['model_start'],'#999999'),(-3.4,t['model_start'],t['model_end'],'#7A5195'),(-5,t['model_end'],t['received'],'#E89A3C'),(-6.6,t['wal_owner_start'],t['wal_owner_end'],'#2A8C64')]:
   ax.plot([left,right],[y,y],color=color,lw=3,solid_capstyle='butt')
 ax.axhline(0,color='#CCCCCC',lw=.6)
 ax.set_title(name.replace('-obs1-r0','')+' | source chinese-00, repeat 0',loc='left');ax.set_ylabel('Audio frontier (s)');ax.set_ylim(-8,37);ax.set_yticks([0,10,20,30])
axs[0].legend(ncol=4,loc='lower right',bbox_to_anchor=(1,.2),fontsize=9);axs[-1].set_xlabel('Wall-clock since arrival release (s)')
from matplotlib.lines import Line2D
fig.legend(handles=[Line2D([0],[0],color=c,lw=3,label=n) for n,c in [('enqueue to model (queue + preprocessing)','#999999'),('GPU model-call interval','#7A5195'),('model completion to owner receipt','#E89A3C'),('WAL-owner call (includes sync)','#2A8C64')]],loc='lower center',ncol=2,fontsize=9)
fig.tight_layout(pad=1.5,rect=(0,.055,1,1));O=W/'figures';O.mkdir(exist_ok=True)
for ext in ['svg','pdf','png']:fig.savefig(O/('R1_FOUR_FRONTIERS.'+ext),dpi=180 if ext=='png' else 300,facecolor='white')
print('plotted read-only GPU event trajectories; arrows are measured full-snapshot audio retractions, not text-error labels')
