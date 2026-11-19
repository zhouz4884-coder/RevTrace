"""Reviewer-facing sourcewise comparison from the current five-policy study."""
from pathlib import Path
import argparse,csv,hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

def render(data,out):
 plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','Helvetica','DejaVu Sans'],
  'font.size':7.6,'axes.labelsize':7.6,'axes.titlesize':8.5,'axes.linewidth':.65,
  'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':7.1,
  'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,
  'axes.spines.right':False,'savefig.dpi':450})
 fig,axes=plt.subplots(1,2,figsize=(7.05,2.52),sharey=True,gridspec_kw={'width_ratios':[1.04,1]})
 fig.subplots_adjust(left=.085,right=.972,top=.84,bottom=.225,wspace=.10)
 policies=[('conservative_s1','Serial','#737C89','^',-.14),
           ('r0s1','Ready-only','#D58A26','s',0.),
           ('r1s1','RevTrace','#245FA5','o',.14)]
 labels=[str(i+1)for i in range(len(data['sources']))]
 for panel,ax in enumerate(axes):
  for i,source in enumerate(data['sources']):
   if i%2==0:ax.axhspan(i-.48,i+.48,color='#F3F5F8',zorder=0)
   vals=[]
   for key,label,color,marker,offset in policies:
    p=source['policies'][key]
    val=100*p['credit_audio_s']/p['offered_audio_s']if panel==0 else p['both_board_J']/p['offered_audio_s']
    vals.append(val)
    reps=[100*r['credit_audio_s']/r['offered_audio_s']if panel==0 else r['both_board_J']/r['offered_audio_s']for r in p['repeats']]
    ax.plot([min(reps),max(reps)],[i+offset,i+offset],color=color,lw=.8,alpha=.65,zorder=2)
    for j,v in enumerate(reps):ax.scatter(v,i+offset+(-.027 if j==0 else .027),s=12,marker=marker,facecolors='white',edgecolors=color,lw=.65,zorder=4)
    ax.scatter(val,i+offset,s=31 if key=='r1s1'else 25,marker=marker,facecolors=color,edgecolors='white',lw=.45,zorder=5)
   ax.plot([min(vals),max(vals)],[i,i],color='#C8CFDA',lw=.9,zorder=1)
  ax.set_ylim(len(labels)-.52,-.55);ax.set_yticks(range(len(labels)),labels);ax.tick_params(axis='y',length=0,pad=4)
  ax.grid(axis='x',color='#DCE1E8',lw=.5,zorder=0)
  ax.set_title('(a) Timely progress'if panel==0 else'(b) Service energy',loc='left',fontweight='bold',pad=8)
 axes[0].set_xlim(-2,103);axes[0].set_xticks([0,25,50,75,100]);axes[0].set_xlabel('Dual-deadline audio coverage (%)');axes[0].set_ylabel('Speaker',labelpad=7)
 allJ=[r['both_board_J']/r['offered_audio_s']for s in data['sources']for p in s['policies'].values()for r in p['repeats']]
 lo=np.floor((min(allJ)-15)/50)*50;hi=np.ceil((max(allJ)+15)/50)*50
 axes[1].set_xlim(lo,hi);axes[1].set_xticks(np.arange(lo,hi+1,100));axes[1].set_xlabel('Two-board energy (J / offered audio-s)')
 handles=[Line2D([],[],color=c,marker=m,linestyle='none',markerfacecolor=c,markeredgecolor='white',markersize=5.4,label=l)for k,l,c,m,o in policies]
 fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.54,.015),ncol=3,frameon=False,handletextpad=.5,columnspacing=2.1)
 out.mkdir(parents=True,exist_ok=True)
 for ext in('pdf','svg','png'):fig.savefig(out/('native_comparison.'+ext),bbox_inches=None,pad_inches=.02,metadata={'Creator':'RevTrace figure renderer'}if ext=='pdf'else None)
 plt.close(fig)

def main():
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();data=json.loads(a.data.read_bytes())
 assert data['study']=='native.factorial'and data['trials']==80 and len(data['sources'])==8
 for policy,target in [('conservative_s1',55.5),('r0s1',58.5),('r1s1',129.96)]:
  assert abs(sum(s['policies'][policy]['credit_audio_s']for s in data['sources'])-target)<1e-8
  assert abs(sum(s['policies'][policy]['offered_audio_s']for s in data['sources'])-137.864125)<1e-8
  assert all(len(s['policies'][policy]['repeats'])==2 for s in data['sources'])
 render(data,a.out)
 print(json.dumps({'figure':'native_comparison','sources':8,'policies':3,'data_sha256':hashlib.sha256(a.data.read_bytes()).hexdigest()}))
if __name__=='__main__':main()
