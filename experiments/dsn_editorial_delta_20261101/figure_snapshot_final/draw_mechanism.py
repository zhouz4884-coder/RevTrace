"""Shape-first coloured mechanism preview. No models or actual trace readers."""
from pathlib import Path
import json,sys,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch,Polygon,Rectangle,Circle
import base_renderer as b
HERE=Path(__file__).resolve().parent
PREVIEW_MODE=True
def draw(out):
 p=json.loads((HERE/'COLOUR_SCENE.json').read_bytes())['palette'];W,H=json.loads((HERE/'SCENE.json').read_bytes())['mechanism']['size']
 fig=plt.figure(figsize=(W,H));ax=fig.add_axes([.002,.002,.996,.996]);ax.axis('off');ax.set(xlim=(0,W),ylim=(0,H))
 def text(x,y,t,c='ink',size=8.5,bold=False,ha='center'):
  return ax.text(x,y,t,color=p.get(c,c),fontsize=size,fontweight='bold' if bold else 'normal',ha=ha,va='center',zorder=9)
 def box(x,y,w,h,c,fill='white',radius=.04,lw=.75,z=4):
  patch=FancyBboxPatch((x,y),w,h,boxstyle=f'round,pad=0.008,rounding_size={radius}',facecolor=p.get(fill,fill),edgecolor=p.get(c,c),lw=lw,zorder=z);ax.add_patch(patch);return patch
 def edge(pts,c='neutral',dash=False,lw=.9):
  col=p.get(c,c);ls=(0,(3,2)) if dash else '-'
  if len(pts)>2:ax.plot([a[0] for a in pts[:-1]],[a[1] for a in pts[:-1]],color=col,ls=ls,lw=lw,zorder=5)
  ax.add_patch(FancyArrowPatch(pts[-2],pts[-1],arrowstyle='-|>',mutation_scale=7.5,color=col,linestyle=ls,lw=lw,shrinkA=1,shrinkB=2,zorder=5))
 def gate(x,y,tag,c='selected'):
  ax.add_patch(Polygon([[x-.32,y],[x,y+.26],[x+.32,y],[x,y-.26]],closed=True,facecolor='white',edgecolor=p[c],lw=.95,zorder=6));text(x,y,tag,c,8.5,True)
 def state(x,y,t,c='selected',w=.65,h=.34):
  box(x-w/2,y-h/2,w,h,c,p[c+'_bg'],radius=.035);text(x,y,t,c,11)
 def check(x,y,c='view'):
  ax.plot([x-.055,x-.01,x+.065],[y,y-.045,y+.065],color=p[c],lw=1.25,zorder=8)
 def monitor(x,y,mode,c):
  w=.96;h=.54;box(x,y,w,h,c,'white',radius=.055)
  ax.plot([x+.40,x+.40],[y-.08,y],color=p[c],lw=.8,zorder=7);ax.plot([x+.22,x+.72],[y-.08,y-.08],color=p[c],lw=.8,zorder=7)
  if mode=='stack':
   box(x+.11,y+.07,.53,.22,'selected','selected_bg',radius=.02,lw=.55);text(x+.375,y+.18,r'$P_2$','selected',9)
   box(x+.33,y+.27,.53,.22,'view','view_bg',radius=.02,lw=.55);text(x+.595,y+.38,r'$h$','view',10)
  else:text(x+w/2,y+h/2,r'$P_2$',c,12)
 # Three actors and their objects, with fixed semantic colours.
 for y,h,col,label in [(2.48,.84,'compute','Execution'),(1.38,1.00,'selected','Selection'),(.18,1.10,'view','Consumer')]:
  box(.08,y,6.96,h,col+'_bg',col+'_bg',radius=.08,lw=.3,z=0)
  ax.plot([.13,.13],[y+.10,y+h-.10],color=p[col],lw=2.5,zorder=1)
  text(.24,y+h-.16,label,col,9,True,ha='left')
 # Frozen input is four compact symbols: source audio, target/EOS, full state, cfg.
 box(1.05,2.74,1.60,.43,'compute','white',radius=.05)
 text(1.85,3.25,'input','compute')
 for x in (1.10,1.49,1.88,2.27):box(x,2.79,.32,.32,'compute','compute_bg',radius=.025,lw=.5)
 ax.plot([1.13,1.17,1.21,1.25,1.29,1.33,1.37],[2.94,3.02,2.86,3.03,2.87,2.99,2.94],color=p['compute'],lw=.9,zorder=8)
 ax.plot([1.56,1.56],[2.84,3.06],color=p['compute'],lw=.7,zorder=8);ax.add_patch(Polygon([[1.56,3.06],[1.75,3.00],[1.56,2.95]],closed=True,facecolor=p['compute'],zorder=8));text(1.66,2.87,'EOS','compute',8.5)
 text(2.04,2.95,r'$\widehat P_2$','compute',10)
 cx,cy=2.43,2.95
 ax.add_patch(Circle((cx,cy),.075,facecolor='white',edgecolor=p['compute'],lw=.8,zorder=8));ax.add_patch(Circle((cx,cy),.025,fill=False,edgecolor=p['compute'],lw=.7,zorder=8))
 for angle in range(0,360,45):
  u=math.radians(angle);ax.plot([cx+.075*math.cos(u),cx+.115*math.cos(u)],[cy+.075*math.sin(u),cy+.115*math.sin(u)],color=p['compute'],lw=1.1,zorder=8)
 # Original worker operators retain their names; the small prediction is not a result.
 box(2.82,2.73,1.99,.45,'compute','white',radius=.055,lw=.55)
 text(3.82,3.25,'Original '+r'$j_3$','compute')
 box(2.91,2.80,.55,.30,'compute','compute_bg',radius=.035,lw=.65);text(3.185,2.95,'ASR','compute')
 box(3.66,2.80,1.06,.30,'compute','compute_bg',radius=.035,lw=.65);text(4.19,2.95,'Correct/Update','compute')
 edge([(2.65,2.95),(2.91,2.95)],'compute');edge([(3.46,2.95),(3.66,2.95)],'compute')
 # Own successor forecast is a separate typed token.
 box(4.12,2.50,.47,.20,'view','view_bg',radius=.035,lw=.55);text(4.355,2.60,r'$\widehat P_3$','view',9);text(3.89,2.60,'pred','view')
 # Complete original result packet and separately bound identity meet AU.
 box(5.10,2.76,.61,.41,'selected','white',radius=.025);text(5.405,2.965,r'$P_3$','selected',12);text(5.405,3.25,'result','selected')
 ax.add_patch(Polygon([[5.59,3.17],[5.71,3.05],[5.59,3.05]],closed=True,facecolor=p['selected_bg'],edgecolor=p['selected'],lw=.4,zorder=7))
 box(6.00,2.64,.40,.28,'selected','selected_bg',radius=.05,lw=.6);text(6.20,2.78,'ID','selected',8.5,True)
 edge([(4.72,2.95),(5.10,2.95)],'compute')
 # Parent and frozen-state bindings are distinct inputs of EL.
 state(1.50,1.95,r'$(P_2,F_2)$');text(1.50,2.23,'selected','selected')
 gate(2.85,1.95,'[EL]')
 edge([(1.825,1.95),(2.53,1.95)],'selected')
 edge([(2.04,2.79),(2.04,2.53),(2.85,2.53),(2.85,2.21)],'compute',True)
 text(2.85,1.57,r'$\widehat P_2\;?=\;P_2$','selected',10)
 # Gate AU consumes the original result + current parent evidence + owned identity.
 gate(4.65,1.95,'[AU]')
 edge([(3.17,1.95),(4.33,1.95)],'selected',True)
 edge([(5.405,2.76),(5.405,2.45),(4.65,2.45),(4.65,2.21)],'selected')
 edge([(6.20,2.64),(6.20,2.28),(4.98,2.28),(4.92,2.08)],'selected',True)
 check(4.25,2.22,'selected')
 # Amber pending state keeps work; it does not create a selected edge.
 box(3.24,1.42,1.12,.22,'unknown','unknown_bg',radius=.06,lw=.6);text(3.80,1.53,'run / buffer','unknown')
 ax.add_patch(Circle((3.33,1.53),.055,facecolor='white',edgecolor=p['unknown'],lw=.6,zorder=7));ax.plot([3.33,3.33,3.365],[1.565,1.53,1.51],color=p['unknown'],lw=.6,zorder=8)
 edge([(3.0,1.82),(3.80,1.82),(3.80,1.64)],'unknown',True)
 # Durable journal and installed state stay separate objects.
 box(5.30,1.71,.56,.48,'selected','white',radius=.025,lw=.65);text(5.58,2.05,r'$D$','selected',10)
 for yy in (1.94,1.87,1.80):ax.plot([5.38,5.78],[yy,yy],color=p['selected'],lw=.55,zorder=8)
 edge([(4.97,1.95),(5.30,1.95)],'selected');text(5.13,2.18,'sync','selected')
 state(6.57,1.95,r'$P_3$');edge([(5.86,1.95),(6.245,1.95)],'selected');text(6.57,1.64,'installed','selected')
 # Consumer icons encode the two whole-view lanes, rather than invented text.
 monitor(1.08,.45,'stack','view');gate(2.85,.72,'[SUP]','view')
 edge([(2.04,.72),(2.53,.72)],'view')
 edge([(1.50,1.78),(1.50,1.35),(2.85,1.35),(2.85,.98)],'selected',True)
 text(3.77,1.09,r'$P_2\;\rightarrow\;\cdots\;\rightarrow\;h$','view',10)
 monitor(4.17,.45,'stack','view');text(4.65,.23,'retain','view');check(3.70,.86,'view')
 monitor(5.98,.45,'selected','selected');text(6.46,.23,'withdraw','withdraw')
 edge([(3.17,.72),(4.17,.72)],'view',True)
 edge([(3.11,.55),(3.30,.31),(5.70,.31),(5.70,.72),(5.98,.72)],'withdraw',True)
 text(3.58,.055,'Solid: data/state   ·   Dashed: evidence   ·   Schematic','neutral')
 # Small repeated event numbers distinguish the shown P2 application from next P3.
 for xx,yy,n in [(1.02,2.23,'1'),(2.02,1.35,'1'),(6.94,2.18,'2')]:
  ax.add_patch(Circle((xx,yy),.075,facecolor='white',edgecolor=p['selected'],lw=.65,zorder=10))
  ax.text(xx,yy,n,ha='center',va='center',fontsize=8.5,fontweight='bold',color=p['selected'],zorder=11)
 return b.export(fig,out,'coordination_protocol','Shape-first preview of the existing input, original worker, result/identity, selected parent, journal and Consumer view objects. The same EL/AU/SUP decisions remain; long conditions are explained by the caption, not new algorithm steps.','shape-first coloured mechanism preview',dict(preview_only=PREVIEW_MODE,new_model_calls=0,actual_reader_calls=0))
