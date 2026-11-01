"""Matching quantitative previews; data and axes are unchanged."""
from pathlib import Path
import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,FancyBboxPatch
from matplotlib.lines import Line2D
import base_renderer as b
from numeric_reuse import core_rows,native_rows
HERE=Path(__file__).resolve().parent
PREVIEW_MODE=True
P=json.loads((HERE/'COLOUR_SCENE.json').read_bytes())['palette']
def chip(fig,x,y,w,text,color,bg):
 patch=FancyBboxPatch((x,y-.022),w,.044,boxstyle='round,pad=0.006,rounding_size=0.012',transform=fig.transFigure,facecolor=P[bg],edgecolor=P[color],lw=.5)
 fig.add_artist(patch);fig.text(x+w/2,y,text,ha='center',va='center',fontsize=8.5,color=P[color]);return patch
def comparison(out,j):
 cfg=json.loads((HERE/'SCENE.json').read_bytes())['case'];result=j['actual_interval_comparison'];fig=plt.figure(figsize=(7.125,cfg['height']));axes=[fig.add_axes(pos) for pos in cfg['axes']]
 end=max(4.35,max(max(r['first_visible'],r['first_certified']) for r in result['arms'].values())+.3)
 top=max(14,max(p['visible_F'] for r in result['arms'].values() for p in r['complete_trace'] if 0<=p['t']<=end))
 chip_artists=[]
 for i,(ax,arm) in enumerate(zip(axes,('R1_S0','R1_S1'))):
  r=result['arms'][arm];trace=r['complete_trace'];x=[p['t'] for p in trace]
  ax.step(x,[p['visible_F'] for p in trace],where='post',color=P['view'],lw=1.45)
  ax.step(x,[p['certified_F'] for p in trace],where='post',color=P['selected'],lw=1.10,ls=(0,(4,2)))
  for g in r['observed_target_loss_windows']:
   ax.add_patch(Rectangle((g['start'],12),g['end']-g['start'],2,facecolor=P['withdraw_bg'],edgecolor=P['withdraw'],hatch='///',lw=.4,zorder=0))
  ax.axvline(2,color=P['unknown'],ls=(0,(1,2)),lw=.85)
  ax.set(xlim=(0,end),ylim=(9.6,top+1.1),yticks=list(range(10,int(top)+1,2)),xticks=list(range(int(end)+1)))
  ax.grid(axis='y',color='#E1E4E8',lw=.4);ax.tick_params(axis='x',labelbottom=(i==1))
  yy=cfg['rail_y'][i];col='compute' if i==0 else 'selected'
  fig.add_artist(Rectangle((.095,yy-.014),.007,.028,transform=fig.transFigure,facecolor=P[col],edgecolor='none'))
  fig.text(.111,yy,('(a) Compute only','(b) RevTrace joint')[i],fontsize=9,fontweight='bold',color=P[col],ha='left',va='center')
  chip_artists.append(chip(fig,.43,yy,.17,f"first {r['first_visible']:.3f} s",'view','view_bg'));chip_artists.append(chip(fig,.63,yy,.17,f"cert {r['first_certified']:.3f} s",'selected','selected_bg'))
  if not r['first_D2_pass']:chip(fig,.84,yy,.135,f"D2 +{(r['first_visible']-2)*1000:.1f} ms",'unknown','unknown_bg')
  fig.text(.095,cfg['subtitle_y'][i],('timely → loss → recovery','later first → retained coverage')[i],fontsize=8.5,color=P['withdraw'] if i==0 else P['view'],ha='left',va='center')
 g=next(w for w in result['arms']['R1_S0']['observed_target_loss_windows'] if w['classification']=='compatible')
 lab=axes[0].text((g['start']+g['end'])/2,13,f"{g['gap_seconds']:.3f} s gap",fontsize=9,fontweight='bold',color=P['withdraw'],ha='center',va='center',bbox=dict(facecolor='white',edgecolor='none',alpha=.8,pad=.7))
 fig.canvas.draw();bb=lab.get_window_extent(fig.canvas.get_renderer()).transformed(axes[0].transData.inverted());assert g['start']<bb.x0<bb.x1<g['end'] and 12<bb.y0<bb.y1<14
 axes[-1].set_xlabel('Wall time since this interval became ready in each run (s)');fig.text(.021,.47,'Audio frontier (s)',rotation=90,va='center',fontsize=8.5)
 handles=[Line2D([],[],color=P['view'],lw=1.45,label='Whole view'),Line2D([],[],color=P['selected'],lw=1.10,ls=(0,(4,2)),label='Selected coverage'),Line2D([],[],color=P['unknown'],lw=.85,ls=(0,(1,2)),label='D2 = 2 s')]
 legend=fig.legend(handles=handles,ncol=3,loc='upper center',bbox_to_anchor=(.57,cfg['legend_anchor_y']),columnspacing=2,handlelength=2)
 fig.canvas.draw();renderer=fig.canvas.get_renderer();gap_pt=(legend.get_window_extent(renderer).y0-max(t.get_window_extent(renderer).y1 for t in chip_artists[:2]))*72/fig.dpi
 assert gap_pt>=3, gap_pt
 return b.export(fig,out,'timely_interval_comparison','Actual unchanged two-arm observations. Short exterior policy/time chips keep first delivery and certified delivery separate, with original D2+27.4ms deadline excess. The actual loss has warm-red hatching. Separate original clocks/interleavings remain unchanged; this is not an event-matched counterfactual.','colour quantitative preview',dict(preview_only=PREVIEW_MODE,axes_and_values_unchanged=True,legend_to_first_chip_gap_pt=gap_pt,new_model_calls=0,actual_reader_calls=0))
