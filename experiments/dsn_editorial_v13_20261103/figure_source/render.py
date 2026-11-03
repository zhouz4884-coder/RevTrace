"""Editorial vector figures from immutable bounded observations, never model calls."""
from pathlib import Path
import argparse, csv, hashlib, json, platform, subprocess, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch, Polygon, Patch
import fitz

HERE=Path(__file__).resolve().parent
P=dict(ink='#26344B',compute='#6653A0',compute_bg='#F0EBF9',selected='#285B91',selected_bg='#E8F0FC',view='#1C817B',view_bg='#E4F4EF',unknown='#A8761C',unknown_bg='#FFF1CF',withdraw='#AD554F',withdraw_bg='#FCEAE6',neutral='#607083')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,j):Path(p).write_text(json.dumps(j,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def style():
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8.0,'axes.labelsize':8.0,'xtick.labelsize':8.0,'ytick.labelsize':8.0,'legend.fontsize':8.0,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.65,'hatch.linewidth':.5,'savefig.facecolor':'white','text.color':P['ink'],'axes.labelcolor':P['ink']})
def export(fig,out,name,detail):
 files=[]
 for ext in ['pdf','svg','png']:
  p=out/(name+'.'+ext);fig.savefig(p,dpi=220);files.append(dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)))
 doc=fitz.open(out/(name+'.pdf'));page=doc[0]
 spans=[s for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans'] if s['text'].strip()]
 page.get_pixmap(matrix=fitz.Matrix(1.6,1.6),colorspace=fitz.csGRAY,alpha=False).save(out/(name+'_gray.png'))
 result=dict(name=name,width_inches=fig.get_figwidth(),height_inches=fig.get_figheight(),minimum_pdf_span_pt=min(s['size'] for s in spans),files=files,details=detail)
 put(out/(name+'.QA.json'),result);plt.close(fig);return result

def case(out,j):
 assert j['status']=='PASS_ACTUAL_TWO_ARM_INTERVAL_OBSERVATIONS' and not j['paired_counterfactual']
 fig=plt.figure(figsize=(7.125,3.10))
 axes=[fig.add_axes([.087,.563,.895,.258]),fig.add_axes([.087,.159,.895,.258])]
 for i,(ax,arm) in enumerate(zip(axes,['R1_S0','R1_S1'])):
  r=j['arms'][arm];t=r['complete_trace'];x=[p['t'] for p in t]
  ax.step(x,[p['visible_F'] for p in t],where='post',color=P['view'],lw=1.45,zorder=3)
  ax.step(x,[p['certified_F'] for p in t],where='post',color=P['selected'],lw=1.1,ls=(0,(4,2)),zorder=3)
  for g in r['observed_target_loss_windows']:
   ax.add_patch(Rectangle((g['start'],12),g['end']-g['start'],2,facecolor=P['withdraw_bg'],edgecolor=P['withdraw'],hatch='///',lw=.4,zorder=1))
  ax.axvline(2,color=P['unknown'],ls=(0,(1,2)),lw=.85,zorder=2)
  ax.axhline(14,color='#ABB4BF',ls=(0,(2,3)),lw=.5,zorder=0)
  ax.set(xlim=(0,4.35),ylim=(9.6,17.6),yticks=[10,12,14,16],xticks=[0,1,2,3,4]);ax.grid(axis='y',color='#E2E6EB',lw=.4)
  ax.tick_params(axis='x',labelbottom=i==1)
  first=r['first_visible'];cert=r['first_certified']
  ax.annotate(f'first {first:.3f} s',xy=(first,14),xytext=(first-.55,16.75),ha='center',va='center',fontsize=8,color=P['view'],arrowprops=dict(arrowstyle='-',color=P['view'],lw=.65),bbox=dict(facecolor='white',edgecolor='none',pad=.5))
  ax.annotate(f'certified {cert:.3f} s',xy=(cert,14),xytext=(3.65,10.6),ha='center',va='center',fontsize=8,color=P['selected'],arrowprops=dict(arrowstyle='-',color=P['selected'],lw=.65),bbox=dict(facecolor='white',edgecolor='none',pad=.5))
  yy=.905 if i==0 else .501
  fig.text(.087,yy,('(a) Computation only','(b) RevTrace: joint retention')[i],fontsize=9,fontweight='bold',color=P['compute'] if i==0 else P['selected'],ha='left')
  label=('First delivery: D2 met   |   Compatible-update gap: 2.176 s' if i==0 else 'First delivery: D2 +27.4 ms   |   Compatible-update gap: none in shown interval')
  fig.text(.087,yy-.052,label,fontsize=8,color=P['ink'])
 gap=next(g for g in j['arms']['R1_S0']['observed_target_loss_windows'] if g['classification']=='compatible')
 axes[0].text((gap['start']+gap['end'])/2,13,f"{gap['gap_seconds']:.3f} s",ha='center',va='center',fontsize=9,fontweight='bold',color=P['withdraw'],bbox=dict(facecolor='white',edgecolor='none',alpha=.9,pad=.7))
 axes[-1].set_xlabel('Wall time since the 12–14-s input interval became ready in each run (s)',labelpad=3)
 fig.text(.018,.487,'Audio frontier (s)',rotation=90,va='center',fontsize=8)
 handles=[Line2D([],[],color=P['view'],lw=1.45,label='Whole view'),Line2D([],[],color=P['selected'],lw=1.1,ls=(0,(4,2)),label='Selected coverage'),Line2D([],[],color=P['unknown'],lw=.85,ls=(0,(1,2)),label='D2 = 2 s')]
 fig.legend(handles=handles,ncol=3,loc='upper right',bbox_to_anchor=(.99,1.01),columnspacing=1.6,handlelength=2,frameon=False)
 return export(fig,out,'timely_full_interval_case',dict(input_same=True,interleavings_different=True,not_event_matched_counterfactual=True,first_delivery_s=[j['arms'][k]['first_visible'] for k in ['R1_S0','R1_S1']],compatible_gap_s=gap['gap_seconds'],D2_excess_joint_ms=(j['arms']['R1_S1']['first_visible']-2)*1000,leaders_anchor_real_events=True))

def mechanism(out):
 W,H=7.125,3.24;fig=plt.figure(figsize=(W,H));ax=fig.add_axes([.002,.002,.996,.996]);ax.set(xlim=(0,W),ylim=(0,H));ax.axis('off')
 def text(x,y,t,c='ink',size=8.,bold=False,ha='center'):
  return ax.text(x,y,t,color=P.get(c,c),fontsize=size,fontweight='bold' if bold else 'normal',ha=ha,va='center',zorder=9)
 def box(x,y,w,h,c,fill='white',lw=.75):
  z=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.008,rounding_size=0.035',facecolor=P.get(fill,fill),edgecolor=P.get(c,c),lw=lw,zorder=3);ax.add_patch(z);return z
 def edge(points,c='neutral',dash=False,lw=.85):
  col=P.get(c,c);ls=(0,(3,2)) if dash else '-'
  if len(points)>2:ax.plot([v[0] for v in points[:-1]],[v[1] for v in points[:-1]],color=col,ls=ls,lw=lw,zorder=5)
  ax.add_patch(FancyArrowPatch(points[-2],points[-1],arrowstyle='-|>',mutation_scale=7.5,color=col,linestyle=ls,lw=lw,shrinkA=1,shrinkB=2,zorder=5))
 def gate(x,y,tag,col):
  ax.add_patch(Polygon([(x-.30,y),(x,y+.235),(x+.30,y),(x,y-.235)],closed=True,facecolor=P[col],edgecolor=P[col],lw=.9,zorder=6));text(x,y,tag,'white',8.,True)
 for y,h,c,label in [(2.30,.88,'compute','Execution'),(1.23,.98,'selected','Selection'),(.16,.97,'view','Consumer')]:
  ax.add_patch(Rectangle((.07,y),6.98,h,facecolor=P[c+'_bg'],edgecolor='none',zorder=0));ax.plot([.12,.12],[y+.10,y+h-.10],color=P[c],lw=2)
  text(.23,y+h-.16,label,c,8.5,True,'left')
 box(1.13,2.53,1.37,.37,'compute');text(1.815,2.715,r'input $\widehat P_2$','compute',10)
 text(1.815,3.045,'audio · target/EOS','compute');text(1.815,2.385,'full state · contract','compute')
 box(2.80,2.50,2.07,.43,'compute');text(3.835,3.055,r'already running original $j_3$','compute',8.5,True)
 for x,w,label in [(2.88,.45,'ASR'),(3.53,.55,'Correct'),(4.28,.51,'Update')]:
  box(x,2.57,w,.29,'compute','compute_bg',.5);text(x+w/2,2.715,label,'compute')
 edge([(2.50,2.715),(2.88,2.715)],'compute');edge([(3.33,2.715),(3.53,2.715)],'compute');edge([(4.08,2.715),(4.28,2.715)],'compute')
 box(5.28,2.53,.86,.37,'selected');text(5.71,2.715,r'$P_3$ + ID','selected',10);text(5.71,3.045,'complete result','selected')
 edge([(4.87,2.715),(5.28,2.715)],'compute')
 text(3.835,2.385,r'own prediction $\widehat P_3$ may differ','compute')
 box(1.20,1.56,.92,.36,'selected','selected_bg');text(1.66,1.74,r'$(P_2,F_2)$','selected',10);text(1.66,2.06,'parent fact','selected')
 gate(2.86,1.74,'[EL]','selected');edge([(2.12,1.74),(2.56,1.74)],'selected')
 edge([(1.815,2.53),(1.815,2.235),(2.86,2.235),(2.86,1.975)],'compute',True)
 text(2.86,1.37,'full input match','selected')
 gate(4.60,1.74,'[AU]','selected');edge([(3.16,1.74),(4.30,1.74)],'selected',True)
 edge([(5.71,2.53),(5.71,2.265),(4.60,2.265),(4.60,1.975)],'selected')
 text(3.86,2.075,'either may\narrive first','selected')
 box(3.59,1.265,1.24,.215,'unknown','unknown_bg',.5);text(4.21,1.372,'run / buffer','unknown')
 edge([(3.01,1.60),(3.36,1.372),(3.59,1.372)],'unknown',True)
 text(3.76,1.565,'unknown','unknown')
 box(5.30,1.50,.51,.47,'selected');text(5.555,1.82,r'$D$','selected',10)
 for yy in [1.68,1.61]:ax.plot([5.37,5.74],[yy,yy],color=P['selected'],lw=.5,zorder=6)
 edge([(4.90,1.74),(5.30,1.74)],'selected');text(5.10,1.94,'sync','selected')
 box(6.18,1.56,.70,.36,'selected','selected_bg');text(6.53,1.74,r'$P_3$','selected',11);edge([(5.81,1.74),(6.18,1.74)],'selected');text(6.53,2.06,'child fact','selected');text(6.53,1.36,'installed','selected')
 box(1.12,.44,1.03,.38,'view');text(1.635,.63,r'whole view $h$','view',9)
 gate(2.86,.63,'[SUP]','view');edge([(2.15,.63),(2.56,.63)],'view')
 edge([(1.66,1.56),(1.66,1.15),(2.86,1.15),(2.86,.865)],'selected',True)
 text(3.93,1.025,r'$P_2\;\rightarrow\;\cdots\;\rightarrow\;h$','view',10)
 box(4.18,.44,1.02,.38,'view','view_bg');text(4.69,.63,r'retain $h$','view',9)
 edge([(3.16,.63),(4.18,.63)],'view',True);text(3.67,.78,'supported','view')
 box(6.03,.44,.91,.38,'selected','selected_bg');text(6.485,.63,r'render $P_2$','selected',9)
 edge([(3.02,.46),(3.31,.27),(5.67,.27),(5.67,.63),(6.03,.63)],'withdraw',True);text(4.58,.32,'unsupported','withdraw')
 text(3.58,.045,'Solid: data/state   ·   Dashed: evidence   ·   Causal schematic','neutral')
 return export(fig,out,'coordination_protocol',dict(causal_schematic=True,three_distinct_checks=True,either_result_or_confirmation_may_arrive_first=True,unknown_run_buffer_only=True,SUP_independent_actual_whole_view=True,original_full_input_bindings=['audio','target/EOS','full state','contract'],parent_child_are_facts_not_event_sequence=True))

def core(out,j):
 data={r['arm']:r for r in j['core']};fig,axes=plt.subplots(1,2,figsize=(7.125,2.65));fig.subplots_adjust(left=.085,right=.979,bottom=.275,top=.79,wspace=.37)
 series=[('View retention off',['R0_S0','R1_S0'],'compute','o'),('View retention on',['R0_S1','R1_S1'],'view','s')]
 for panel,ax in enumerate(axes):
  for name,keys,c,mark in series:
   ys=[data[k]['withdrawals'] if panel==0 else 100*data[k]['credit']/data[k]['offered'] for k in keys]
   ax.plot([0,1],ys,color=P[c],lw=1.15,marker=mark,markersize=4.3,label=name,zorder=3)
   for xx,yy in zip([0,1],ys):
    joint=xx==1 and keys[-1]=='R1_S1';off=7 if panel==0 or (xx==0 and keys[-1]=='R1_S0') or joint else -8
    val=f'{yy:.0f}' if panel==0 else f'{yy:.1f}'
    if joint and panel==1:val+=' · RevTrace'
    ax.annotate(val,(xx,yy),xytext=(0,off),textcoords='offset points',ha='right' if joint else 'center',va='bottom' if off>0 else 'top',fontsize=8,color=P[c])
  ax.set(xlim=(-.15,1.15),xticks=[0,1],xticklabels=['Off','On'],xlabel='Computation retention');ax.grid(axis='y',color='#DEE2E8',lw=.4,zorder=0)
  if panel==0:
   ax.set(ylim=(-.9,21),yticks=[0,5,10,15,20],ylabel='Frontier withdrawals (total)');ax.set_title('(a) Withdrawals',loc='left',fontsize=9,fontweight='bold')
   ax.text(.44,18.7,'12 → 17 withdrawals',color=P['compute'],fontsize=8,ha='center')
   ax.annotate('0 frontier withdrawals\nin this stratum',xy=(1,0),xytext=(.36,3.9),fontsize=8,color=P['view'],ha='center',arrowprops=dict(arrowstyle='-',color=P['view'],lw=.6))
  else:
   ax.set(ylim=(85,100),yticks=[85,90,95,100],ylabel='Timely audio (%)');ax.set_title('(b) Both delivery deadlines',loc='left',fontsize=9,fontweight='bold')
 fig.text(.085,.982,'Core Qwen · 24 speakers · 3 cohorts\n714.110 audio-s offered per arm',va='top',fontsize=8,color=P['neutral'])
 fig.legend(*axes[0].get_legend_handles_labels(),loc='upper right',bbox_to_anchor=(.99,1.02),ncol=2,columnspacing=1.25,handlelength=1.8,frameon=False)
 ints=[]
 for cohort in ['A','B','C']:
  y={k:next(x['credit'] for x in v['cohorts'] if x['cohort']==cohort) for k,v in data.items()}
  ints.append(y['R1_S1']-y['R1_S0']-y['R0_S1']+y['R0_S0'])
 assert all(abs(a-b)<1e-8 for a,b in zip(ints,[18.530,6.205,17.555]))
 fig.text(.50,.025,'Credit interaction by cohort (audio-s):  A +18.530   B +6.205   C +17.555',ha='center',fontsize=8,color=P['neutral'])
 return export(fig,out,'core_interaction',dict(core_totals=j['core'],credit_interactions_audio_s=ints,pooled_points=True,confidence_intervals=False,coverage_axis_min=85,all_headline_15_runs_fail_D2=True))

def native(out,j):
 rows=j['rows'];assert len(rows)==4 and not any(r['unknown'] for r in rows)
 fig,ax=plt.subplots(figsize=(3.48,3.10));fig.subplots_adjust(left=.285,right=.965,bottom=.255,top=.978)
 ys=[3.38,2.58,1.18,.38]
 parts=[('matching',P['selected'],None,'Timely; matches later selected text'),('mismatching','#DCCFF0','///','Timely; different from later selected text'),('untimely','#EFF1F4',None,'Misses a delivery deadline')]
 totals=[]
 for r,y in zip(rows,ys):
  assert abs(sum(r[k] for k,_,_,_ in parts)-r['offered'])<1e-8
  left=0.
  for k,c,h,label in parts:
   val=100*r[k]/r['offered'];ax.barh(y,val,left=left,height=.36,color=c,edgecolor='#737D89',lw=.35,hatch=h,zorder=2)
   if val>=8:ax.text(left+val/2,y,f'{val:.1f}',ha='center',va='center',color='white' if k=='matching' else P['ink'],fontsize=8)
   elif val>0:
    xx=left+val/2;tx=99 if k=='untimely' else xx
    ax.annotate(f'{val:.1f}',xy=(xx,y-.18),xytext=(tx,y-.36),ha='right' if k=='untimely' else 'center',va='center',fontsize=8,color=P['neutral'],arrowprops=dict(arrowstyle='-',lw=.5,color=P['neutral']))
   left+=val
  total=100*(r['matching']+r['mismatching'])/r['offered'];totals.append(total)
  ax.plot([total,total],[y+.18,y+.27],color=P['ink'],lw=.65)
  ax.text(total,y+.31,f'{total:.1f}%',ha='right' if total>90 else 'center',va='bottom',fontsize=8,fontweight='bold',color=P['ink'])
 ax.set(yticks=ys,yticklabels=['Conservative','RevTrace','Conservative','RevTrace'],xlim=(0,100),ylim=(-.17,4.17),xticks=[0,50,100],xlabel='Offered audio (%)');ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0,pad=4)
 for y,title,lo,hi in [(4.02,'Independent (8 speakers)',totals[0],totals[1]),(1.82,'Resident (4 speakers)',totals[2],totals[3])]:
  ax.text(0,y,title,fontsize=8,fontweight='bold',ha='left');ax.text(100,y-.25,f'+{hi-lo:.1f} pp',fontsize=8,color=P['selected'],ha='right')
 fig.legend(handles=[Patch(facecolor=c,edgecolor='#737D89',hatch=h,linewidth=.4,label=l) for _,c,h,l in parts],loc='lower left',bbox_to_anchor=(.025,.005),ncol=1,fontsize=8,labelspacing=.18,handlelength=1.25,handletextpad=.5,borderaxespad=0,frameon=False)
 return export(fig,out,'native_content',dict(rows=rows,timely_total_percent=totals,gains_pp=[totals[1]-totals[0],totals[3]-totals[2]],separate_cohort_denominators=True,retrospective_agreement_not_accuracy_or_online_SUP=True))

def pairs(out,rows,j):
 ci=j['bootstrap']['intervals']['duration_weighted_ratio_gain_pp'];fig,ax=plt.subplots(figsize=(3.48,3.45));fig.subplots_adjust(left=.235,right=.95,bottom=.27,top=.90)
 yy=list(range(9,1,-1));xs=[float(r['paired_gain_pp']) for r in rows];assert all(x>0 for x in xs)
 ax.scatter(xs,yy,color=P['selected'],s=22,zorder=3)
 for x,y in zip(xs,yy):ax.annotate(f'{x:.1f}',(x,y),xytext=(5,0),textcoords='offset points',fontsize=8,va='center')
 ax.axhline(1.55,color='#C5CDD5',lw=.6)
 ax.errorbar(ci['point_estimate'],.8,xerr=[[ci['point_estimate']-ci['lower95']],[ci['upper95']-ci['point_estimate']]],fmt='D',markersize=4,color=P['view'],lw=1.0,capsize=3)
 ax.set(yticks=yy+[.8],yticklabels=[r['speaker_id'] for r in rows]+['Overall'],xlim=(0,74),ylim=(0,9.6),xticks=[0,20,40,60],xlabel='Coverage gain (percentage points)');ax.tick_params(axis='y',length=0);ax.spines['left'].set_visible(False);ax.axvline(0,color='#BAC2CB',lw=.6)
 fig.text(.06,.96,'Eight source-paired effects',fontsize=9,fontweight='bold');fig.text(.06,.025,'Overall: duration-weighted; speaker-paired 95% CI.\nTwo timing repeats/source; no per-source CI.',fontsize=8,color=P['neutral'])
 return export(fig,out,'source8_paired_effects',dict(artifact_only=True,individual_points_not_CI=True,independent_acoustic_units=8,overall_speaker_paired_CI=ci))

def main():
 a=argparse.ArgumentParser();a.add_argument('--manifest',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a=a.parse_args()
 m=json.loads(a.manifest.read_bytes());g=lambda *x:subprocess.check_output(['git','-C',str(HERE),*x],text=True).strip()
 assert not g('status','--porcelain','--untracked-files=all');assert g('rev-parse','HEAD')==m['code_commit']
 assert set(g('ls-files').splitlines())=={r['path'] for r in m['files']}
 for r in m['files']:assert (HERE/r['path']).stat().st_size==r['bytes'] and sha(HERE/r['path'])==r['sha256']
 im=json.loads((HERE/'INPUT_MAP.json').read_bytes())
 for r in im['sources']:assert sha(HERE/r['path'])==r['sha256']
 a.out.mkdir(parents=True,exist_ok=False);style()
 load=lambda n:json.loads((HERE/'inputs'/n).read_bytes())
 checks=[case(a.out,load('case.json')),mechanism(a.out),core(a.out,load('core.json')),native(a.out,load('native.json')),pairs(a.out,list(csv.DictReader((HERE/'inputs/pairs.csv').open(encoding='utf-8-sig',newline=''))),load('native_report.json'))]
 for r in m['files']:assert sha(HERE/r['path'])==r['sha256']
 env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),matplotlib=matplotlib.__version__,pymupdf=fitz.VersionBind)
 put(a.out/'SUMMARY.json',dict(status='PASS_FROZEN_FIGURE_EXPORTS_PENDING_VISUAL_INSPECTION',source_commit=m['code_commit'],source_manifest_sha256=sha(a.manifest),figures=checks,environment=env,new_model_calls=0,raw_service_readers=0))
 put(a.out/'GATE.json',dict(status='PASS_FROZEN_NUMERIC_VECTOR_EXPORTS',visual_QA='PENDING',new_model_calls=0,raw_service_readers=0))
 print(json.dumps(dict(source_commit=m['code_commit'],figures=len(checks),out=str(a.out),new_model_calls=0)))
if __name__=='__main__':main()
