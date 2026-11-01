"""Standard interaction contrasts and a separate single-column content plot."""
from pathlib import Path
import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import base_renderer as b
from numeric_reuse import core_rows,native_rows
HERE=Path(__file__).resolve().parent
PREVIEW_MODE=True
P=json.loads((HERE/'COLOUR_SCENE.json').read_bytes())['palette']
SCENE=json.loads((HERE/'SCENE.json').read_bytes())

def core(out,j):
 rows=core_rows(j);native=native_rows(j);assert dict(core=rows,native=native)==j['original_numeric_values']
 data={r['arm']:r for r in rows};fig,axes=plt.subplots(1,2,figsize=tuple(SCENE['core']['size']))
 fig.subplots_adjust(**SCENE['core']['margins'])
 series=[('View retention off',('R0_S0','R1_S0'),P['compute'],'o'),('View retention on',('R0_S1','R1_S1'),P['view'],'s')]
 for panel,ax in enumerate(axes):
  for label,arms,color,marker in series:
   ys=[data[a]['withdrawals'] if panel==0 else 100*data[a]['credit']/data[a]['offered'] for a in arms]
   ax.plot([0,1],ys,color=color,lw=1.15,marker=marker,markersize=4.3,markeredgewidth=.8,label=label,zorder=3)
   for xx,yy in zip([0,1],ys):
    joint=xx==1 and label.endswith('on')
    offset=7 if panel==0 or (xx==0 and label.endswith('off')) or joint else -8
    value=str(int(yy)) if panel==0 else f'{yy:.1f}'
    if joint:value+=' · RevTrace'
    ax.annotate(value,(xx,yy),xytext=(0,offset),textcoords='offset points',ha='right' if joint else 'center',va='bottom' if offset>0 else 'top',fontsize=8.5,color=P['selected'] if joint else color)
  ax.set(xlim=(-.16,1.16),xticks=[0,1],xticklabels=['Off','On'],xlabel='Computation retention')
  ax.grid(axis='y',color='#DEE2E8',lw=.45,zorder=0)
  if panel==0:
   ax.set(ylim=(-.8,20),yticks=[0,5,10,15,20],ylabel='Frontier withdrawals (total)')
   ax.axhline(0,color='#B8BFC7',lw=.55,zorder=1)
   ax.set_title('(a) Withdrawals',loc='left',fontsize=9,fontweight='bold')
  else:
   ax.set(ylim=(85,100),yticks=[85,90,95,100],ylabel='Timely audio (%)')
   ax.set_title('(b) Audio meeting both deadlines',loc='left',fontsize=9,fontweight='bold')
 fig.text(.08,.98,'Core Qwen · 24 speakers\n714.110 s per arm · 3 cohorts',fontsize=8.5,color=P['neutral'],ha='left',va='top')
 fig.legend(*axes[0].get_legend_handles_labels(),loc='upper right',bbox_to_anchor=(.98,1.015),ncol=2,fontsize=8.5,columnspacing=1.4,handlelength=1.7)
 details=dict(preview_only=PREVIEW_MODE,numeric_values_equal_v7=True,total_cohorts=3,total_speakers=24,offered_audio_s_per_arm=714.110,confidence_intervals=False,lines='factor contrasts, not workload interpolation',coverage_axis_min=85,new_model_calls=0,actual_reader_calls=0)
 return b.export(fig,out,'core_interaction','The four pooled core totals are shown as factorial contrasts. Computation retention Off/On is categorical; each line holds view retention fixed. Withdrawal counts are totals over three cohorts, while timely audio divides the same credit by714.110offered seconds per arm. The right panel is an explicitly85–100% line-plot scale. No confidence interval or independent-run count is inferred. JointOn/On is RevTrace. The positive control and all15whole-runD2failures remain in caption/text.','unchanged pooled-factorial presentation',details)

def native(out,j):
 rows=native_rows(j);assert dict(core=core_rows(j),native=rows)==j['original_numeric_values']
 fig,ax=plt.subplots(figsize=tuple(SCENE['native']['size']));fig.subplots_adjust(**SCENE['native']['margins'])
 ys=[3.25,2.45,1.05,.25]
 for y,row in zip(ys,rows):
  left=0
  for key,col,hatch in [('matching',P['selected'],None),('unmatched','#DCCFF0','///'),('untimely','#EFF1F4',None)]:
   value=100*row[key]/row['offered'];ax.barh(y,value,left=left,height=.42,color=col,edgecolor='#7F8290',lw=.35,hatch=hatch,zorder=2)
   if value>=8:ax.text(left+value/2,y,f'{value:.1f}',ha='center',va='center',fontsize=8.5,color='white' if key=='matching' else P['ink'])
   if key=='untimely' and value<8:
    dy=.41 if row['bank']=='matched' else -.43;ax.annotate(f'{value:.1f}%',xy=(left+value/2,y),xytext=(98,y+dy),ha='right',va='center',fontsize=8.5,color=P['neutral'],arrowprops=dict(arrowstyle='-',color=P['neutral'],lw=.5,connectionstyle='angle,angleA=0,angleB=90,rad=0'))
   left+=value
 ax.set(yticks=ys,yticklabels=['Conservative','RevTrace','Conservative','RevTrace'],xlim=(0,100),ylim=(-.55,3.95),xticks=[0,50,100],xlabel='Offered audio (%)')
 ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0,pad=4)
 ax.text(0,3.82,'Matched',fontsize=9,fontweight='bold',color=P['ink']);ax.text(0,1.56,'Resident',fontsize=9,fontweight='bold',color=P['ink'])
 fig.text(.03,.985,'StreamCorrect · 4 speakers · 66.340 s / arm / bank',fontsize=8.5,color=P['neutral'],ha='left',va='top')
 handles=[Rectangle((0,0),1,1,color=P['selected']),Rectangle((0,0),1,1,facecolor='#DCCFF0',edgecolor='#7F8290',hatch='///'),Rectangle((0,0),1,1,facecolor='#EFF1F4',edgecolor='#7F8290')]
 fig.legend(handles,['Timely; matches later selected text','Timely; different from later selected text','Misses a delivery deadline'],loc='lower left',bbox_to_anchor=(.03,.005),ncol=1,fontsize=8.5,labelspacing=.20,handlelength=1.3,handletextpad=.5,borderaxespad=0)
 old=b.WIDTH;b.WIDTH=3.48
 try:return b.export(fig,out,'native_content','Single-column final native text partition. Four rows share66.33975offered audio seconds per arm/bank; matched and resident are groups, not independent speaker populations. Blue and purple-hatched timely categories use retrospective later-selected whole-text agreement, not human accuracy or onlineSUPvalidity. Small missed-deadline fractions0.8%/3.3% have external labels. Run/request Pass counts are intentionally absent and remain in the table/text.','unchanged retrospective native fractions',dict(preview_only=PREVIEW_MODE,numeric_values_equal_v7=True,pass_column_removed=True,actual_single_column_width_inches=3.48,new_model_calls=0,actual_reader_calls=0))
 finally:b.WIDTH=old

