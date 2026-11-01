"""Three incremental editorial figures; byte-pinned v7 data, zero raw readers."""
from pathlib import Path
import argparse,hashlib,json,platform,subprocess,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import fitz
import base_renderer as b
from numeric_reuse import core_rows,native_rows

HERE=Path(__file__).resolve().parent
WIDTH=7.125;BLUE=b.BLUE;TEAL=b.TEAL;GRAY=b.GRAY;INK=b.INK;RED=b.RED
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,o):Path(p).write_bytes((json.dumps(o,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode())
def git(*args):return subprocess.check_output(['git','-C',str(HERE),*args],text=True).strip()
def gate(mp):
 m=json.loads(mp.read_bytes());c=git('rev-parse','HEAD')
 assert Path(git('rev-parse','--show-toplevel')).resolve()==HERE
 assert not git('status','--porcelain','--untracked-files=all')
 assert c==m['code_commit'] and set(git('ls-files').splitlines())=={r['path'] for r in m['files']}
 for r in m['files']:
  p=HERE/r['path'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
 return c
def environment():
 return dict(python=sys.version,executable=sys.executable,platform=platform.platform(),matplotlib=matplotlib.__version__,numpy=np.__version__,pymupdf=fitz.VersionBind,new_model_calls=0,actual_reader_calls=0)

def comparison_plot(out,result):
 fig,axes=plt.subplots(2,1,sharex=True,figsize=(WIDTH,2.90))
 fig.subplots_adjust(left=.095,right=.985,bottom=.19,top=.85,hspace=.32)
 end=max(4.35,max(max(r['first_visible'],r['first_certified']) for r in result['arms'].values())+.3)
 top=max(14,max(p['visible_F'] for r in result['arms'].values() for p in r['complete_trace'] if 0<=p['t']<=end))
 titles=('(a) Compute only: earlier first delivery, interrupted coverage','(b) RevTrace joint: later first delivery, retained coverage')
 for ax,arm,title in zip(axes,('R1_S0','R1_S1'),titles):
  r=result['arms'][arm];trace=r['complete_trace'];x=[p['t'] for p in trace]
  ax.step(x,[p['visible_F'] for p in trace],where='post',color=TEAL,lw=1.5,label='Actual whole view')
  ax.step(x,[p['certified_F'] for p in trace],where='post',color=BLUE,lw=1.15,ls=(0,(4,2)),label='Selected-state coverage')
  for window in r['observed_target_loss_windows']:
   ax.add_patch(Rectangle((window['start'],12),window['end']-window['start'],2,facecolor='#FAEEEE',edgecolor=RED,hatch='////',lw=.35))
  ax.axvline(2,color=INK,ls=(0,(2,2)),lw=.75);ax.axhline(14,color=GRAY,lw=.5,ls=(0,(1,2)))
  ax.set(xlim=(0,end),ylim=(9.6,top+1.1),yticks=list(range(10,int(top)+1,2)),xticks=list(range(int(end)+1)))
  ax.set_title(title,loc='left',fontsize=9,fontweight='bold',pad=3)
  miss=f" (D2 +{(r['first_visible']-2)*1000:.1f} ms)" if not r['first_D2_pass'] else ''
  ax.text(.985,.08,f"First coverage: {r['first_visible']:.3f} s{miss}; selected: {r['first_certified']:.3f} s",transform=ax.transAxes,ha='right',va='bottom',fontsize=8.5,bbox=dict(facecolor='white',edgecolor='none',alpha=.94,pad=1))
  ax.grid(axis='y',alpha=.13,lw=.4)
 gap=next(w for w in result['arms']['R1_S0']['observed_target_loss_windows'] if w['classification']=='compatible')
 axes[0].text((gap['start']+gap['end'])/2,13,f"{gap['gap_seconds']:.3f} s gap",ha='center',va='center',fontsize=8.5,color=RED,bbox=dict(facecolor='white',edgecolor='none',alpha=.95,pad=1))
 axes[1].text(.985,.94,'No later F14 coverage gap observed',transform=axes[1].transAxes,ha='right',va='top',fontsize=8.5,color=TEAL,bbox=dict(facecolor='white',edgecolor='none',alpha=.94,pad=1))
 axes[-1].set_xlabel('Wall time since the same input interval became ready in each run (s)')
 fig.text(.023,.52,'Audio frontier (s)',rotation=90,va='center',fontsize=8.5)
 fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',ncol=2,bbox_to_anchor=(.58,1.01),columnspacing=2)
 cap=('An interval can be delivered on time and later lose coverage. These separate actual c16-overload executions use the same12–14s input interval and their own ready clocks. Computation-only first covers it at1.444s, loses coverage for2.176s, and certifies at3.720s. Joint first covers at2.027s(D2+27.4ms), then has no observed laterF14 gap; its own3.794s selectedF14 update retains an aheadF16 view. The27.4ms is deadline excess, not the cross-arm first-delivery difference. The figure separates first-delivery and subsequent availability; it is not an event-matched causal counterfactual.')
 return b.export(fig,out,'timely_interval_comparison',cap,'unchanged actual two-arm observations',dict(original_comparison_sha256=sha(HERE/next(r['copy'] for r in json.loads((HERE/'SOURCE_MAP.json').read_bytes())['bounded_inputs'] if r['key']=='actual_interval_comparison')),unchanged_actual_axes=True,deadline_excess_is_not_cross_arm_difference=True))

def mechanism(out):
 fig=plt.figure(figsize=(WIDTH,3.45));ax=fig.add_axes([.004,.008,.992,.985]);ax.axis('off');ax.set(xlim=(0,WIDTH),ylim=(0,3.45))
 txt=b.txt;box=b.box;arrow=b.arrow
 txt(ax,.08,3.33,'(a) Early execution and later input confirmation meet at selection',ha='left',fontweight='bold')
 box(ax,.10,2.66,1.34,.48,'Predicted input\n'+r'$\widehat P_2$',TEAL,'#F0F8F7')
 box(ax,1.76,2.62,2.32,.56,'Already running full call '+r'$j_3$'+'\nOriginal ASR → Correct/Update',GRAY,'#F6F6F6')
 arrow(ax,(1.44,2.90),(1.76,2.90),TEAL)
 box(ax,5.00,2.44,2.02,.86,'[AU] Original result '+r'$P_3$'+'\n+ confirmed current parent\n+ owned identity\nsync → install',BLUE,'#EAF1F8')
 arrow(ax,(4.08,2.90),(5.00,2.90),GRAY)
 txt(ax,4.52,3.09,'result',fontsize=8.5,color=GRAY)
 box(ax,.10,1.94,1.34,.46,'Later selected\nparent '+r'$P_2$',BLUE,'#EAF1F8')
 box(ax,1.94,1.91,1.80,.52,'[EL] Complete frozen input\n'+r'$\widehat P_2=P_2$'+' at same frontier?',BLUE,'#EAF1F8')
 arrow(ax,(1.44,2.17),(1.94,2.17),BLUE)
 ax.plot([3.74,4.46,4.46],[2.17,2.17,2.55],color=BLUE,ls=(0,(3,2)),lw=.85)
 arrow(ax,(4.46,2.55),(5.00,2.55),BLUE,ls=(0,(3,2)))
 txt(ax,2.95,1.70,'Match: keep call   Refuted: reject   Unknown: may run/buffer; no commit',ha='center',color=GRAY,fontsize=8.5)
 txt(ax,3.57,1.49,'Own predicted '+r'$\widehat P_3$'+' may differ from original result '+r'$P_3$',color=TEAL,fontsize=8.5)
 ax.plot([.08,7.04],[1.35,1.35],color='#BDBDBD',lw=.6)
 txt(ax,.08,1.24,'(b) The selected parent independently triggers whole-view support',ha='left',fontweight='bold')
 box(ax,.10,.48,1.34,.43,'Selected parent\n'+r'$P_2$',BLUE,'#EAF1F8')
 box(ax,1.74,.80,1.65,.35,'Snapshot replacement',GRAY,'#F4F4F4')
 arrow(ax,(1.44,.78),(1.74,.975),GRAY)
 box(ax,3.69,.80,1.59,.35,'Render '+r'$P_2$'+'; lose ahead '+r'$h$',GRAY,'#F4F4F4')
 arrow(ax,(3.39,.975),(3.69,.975),GRAY)
 box(ax,1.74,.26,1.65,.38,'[SUP] Whole path\n'+r'$S(P_2,h)$'+'?',TEAL,'#F0F8F7')
 arrow(ax,(1.44,.58),(1.74,.45),BLUE)
 box(ax,3.69,.26,1.59,.38,'Supported:\nretain whole '+r'$h$',TEAL,'#F0F8F7')
 arrow(ax,(3.39,.45),(3.69,.45),TEAL,ls=(0,(3,2)))
 box(ax,5.56,.26,1.46,.38,'Unsupported:\nrender selected state',RED,'#FAEEEE',ls=(0,(3,2)))
 ax.plot([3.39,3.55,6.29],[.60,.70,.70],color=RED,ls=(0,(3,2)),lw=.85)
 arrow(ax,(6.29,.70),(6.29,.64),RED,ls=(0,(3,2)))
 txt(ax,6.12,.96,r'$h$'+' is the whole\nahead view',color=TEAL,fontsize=8.5)
 txt(ax,.10,.07,'Solid: data flow. Dashed: check evidence. Schematic; no measured time scale.',ha='left',color=GRAY,fontsize=8.5)
 cap=('The full call has already started before its parent input is confirmed. The original ASR/Correct/Update pipeline and its complete result form one branch; the later selected parent and [EL] form another. [AU] combines a complete original result, confirmed current parent, and owned identity before durable sync and installation. [SUP] independently checks the actual whole view from the selected parent. Unknown eligibility permits running/buffering but no selection. Gray operator box is the unchanged model pipeline; colored outlined boxes are coordination checks. Solid arrows carry data/state; dashed arrows carry check evidence. This is a causal schematic, not a measured timeline.')
 return b.export(fig,out,'coordination_protocol',cap,'causal schematic; no neural execution timing',dict(call_started_before_confirmation=True,result_may_complete_before_or_after_confirmation=True,AU_joins_result_parent_and_identity=True,SUP_independent=True,solid='data/state flow',dashed='check evidence'))

def matrix(ax,totals):
 ax.set(xlim=(-.32,2.04),ylim=(-.08,2.15));ax.axis('off')
 b.txt(ax,.96,2.055,'View retention S',fontweight='bold')
 for x,label in [(.5,'Off'),(1.5,'On')]:b.txt(ax,x,1.88,label,color=GRAY)
 b.txt(ax,-.22,.86,'Computation R',rotation=90,fontweight='bold')
 for y,label in [(1.26,'Off'),(.47,'On')]:b.txt(ax,-.065,y,label,rotation=90,color=GRAY)
 for i,row in enumerate(totals):
  x=(i%2)+.05;y=1.61-(i//2)*.82-.73;color=BLUE if row['arm']=='R1_S1' else GRAY
  ax.add_patch(Rectangle((x,y),.94,.73,facecolor='#EDF3F9' if row['arm']=='R1_S1' else 'white',edgecolor=color,lw=1.1 if row['arm']=='R1_S1' else .65))
  b.txt(ax,x+.47,y+.47,str(row['withdrawals']),color=color,fontsize=20,fontweight='bold')
  b.txt(ax,x+.47,y+.245,f"{row['credit']:.3f} s",color=INK)
  b.txt(ax,x+.47,y+.07,('Recompute','View only','Compute only','RevTrace')[i],color=color)

def native_bars(ax,rows):
 ys=[3.25,2.45,1.05,.25]
 for y,row in zip(ys,rows):
  left=0
  for k,color,hatch in [('matching',BLUE,None),('unmatched','#B5C8D8','////'),('untimely','#F2F2F2',None)]:
   value=100*row[k]/row['offered'];ax.barh(y,value,left=left,height=.46,color=color,edgecolor='#666666',linewidth=.45,hatch=hatch,zorder=2)
   if value>=8:ax.text(left+value/2,y,f'{value:.1f}',ha='center',va='center',fontsize=8.5,color='white' if k=='matching' else INK)
   if k=='untimely' and value<8:
    dy=.44 if row['bank']=='matched' else -.43
    ax.annotate(f'{value:.1f}%',xy=(left+value/2,y),xytext=(98,y+dy),ha='right',va='center',fontsize=8.5,color=GRAY,arrowprops=dict(arrowstyle='-',color=GRAY,lw=.6,connectionstyle='angle,angleA=0,angleB=90,rad=0'))
   left+=value
  ax.text(102,y,f"{row['passes']}/8",va='center',fontsize=8.5,color=BLUE if row['policy']=='fullcall' else GRAY)
 ax.set(yticks=ys,yticklabels=['Conservative','RevTrace','Conservative','RevTrace'],xlim=(0,114),ylim=(-.55,3.95),xticks=[0,50,100],xlabel='Fraction of offered audio (%)')
 ax.spines['left'].set_visible(False);ax.spines['bottom'].set_bounds(0,100);ax.tick_params(axis='y',length=0,pad=4)
 ax.text(0,3.70,'Matched trials',fontsize=9,fontweight='bold');ax.text(0,1.50,'Resident requests',fontsize=9,fontweight='bold')
 ax.text(103,3.70,'Pass',fontsize=8.5,ha='center',color=GRAY)
 return [Rectangle((0,0),1,1,color=BLUE),Rectangle((0,0),1,1,facecolor='#B5C8D8',edgecolor='#666666',hatch='////'),Rectangle((0,0),1,1,facecolor='#F2F2F2',edgecolor='#666666')]

def effects(out,j):
 totals=core_rows(j);native=native_rows(j);assert dict(core=totals,native=native)==j['original_numeric_values']
 fig=plt.figure(figsize=(WIDTH,3.60));a=fig.add_axes([.025,.28,.405,.56]);c=fig.add_axes([.60,.295,.345,.54])
 matrix(a,totals);handles=native_bars(c,native)
 fig.text(.03,.972,'(a) Core Qwen: joint retention',fontsize=9,fontweight='bold',va='top')
 fig.text(.03,.916,'24 speakers · 714.110 s per arm',fontsize=8.5,va='top',color=GRAY)
 fig.text(.49,.972,'(b) Native StreamCorrect',fontsize=9,fontweight='bold',va='top')
 fig.text(.49,.916,'4 speakers · 66.340 s per arm per bank',fontsize=8.5,va='top',color=GRAY)
 fig.text(.235,.18,'Big: frontier withdrawals; below: timely audio (s)',fontsize=8.5,ha='center',color=GRAY)
 fig.legend(handles,['Timely; matches later\nselected text','Timely; different from\nlater selected text','Misses a delivery\ndeadline'],loc='lower center',bbox_to_anchor=(.51,.006),ncol=3,fontsize=8.5,columnspacing=1.5,handlelength=1.4,handletextpad=.5)
 cap=('The panels measure complementary evidence under different contracts. (a) Core Qwen factorization sums three eight-speaker cohorts over714.110audio-s per arm; large numbers are frontier withdrawal counts, lower numbers are audio meeting both deadlines. All15headline runs including the separate alternative-joint positive control fail whole-runD2. (b) Native StreamCorrect partitions66.33975audio-s per policy per bank from four existing speakers. Timely coverage is separated by retrospective whole first-view agreement with later same-frontier selected text; both timely categories may be legally displayed online. Gray tails0.8% and3.3% are shown explicitly, as rounded audio-time fractions. Pass counts are trials for matched and requests for resident; they are not audio-time fractions or independent speaker counts. Agreement is not human transcription accuracy or [SUP] validity.')
 put(out/'MAIN_EFFECT_NUMERIC_VALUES.json',dict(core=totals,native=native))
 return b.export(fig,out,'composition_and_content',cap,'unchanged measured factorization and retrospective native content fractions',dict(core_offered_audio_s=714.110,native_offered_audio_s=66.33975,core_speakers=24,native_speakers=4,unchanged_numeric_values=True,no_SUP_or_accuracy_category=True))

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--environment',type=Path,required=True);p.add_argument('--root-preflight',type=Path,required=True);a=p.parse_args()
 c=gate(a.manifest);env=json.loads(a.environment.read_bytes());assert env==environment()
 root=json.loads(a.root_preflight.read_bytes());assert root['gate']=='SOURCE_IDENTITY_PASS' and root['code_commit']==c and root['manifest_sha256']==sha(a.manifest)
 controls={str(p):sha(p) for p in [a.manifest,a.environment,a.root_preflight,HERE/'CONFIG.json',HERE/'SOURCE_MAP.json']}
 sm=json.loads((HERE/'SOURCE_MAP.json').read_bytes());assert json.loads((HERE/'CONFIG.json').read_bytes())['input_map_sha256']==sha(HERE/'SOURCE_MAP.json')
 j={}
 for r in sm['bounded_inputs']:
  p=HERE/r['copy'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256'] and sha(r['original'])==r['sha256'];j[r['key']]=json.loads(p.read_bytes())
 for r in sm['protected']:assert Path(r['path']).stat().st_size==r['bytes'] and sha(r['path'])==r['sha256']
 for r in sm['dependencies']:assert sha(HERE/r['path'])==r['sha256'] and sha(r['original'])==r['sha256']
 comparison=j['actual_interval_comparison'];assert comparison['status']=='PASS_ACTUAL_TWO_ARM_INTERVAL_OBSERVATIONS'
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 put(out/'RUN_RECORD.json',dict(experiment_id=json.loads((HERE/'CONFIG.json').read_bytes())['experiment_id'],source_commit=c,manifest_sha256=sha(a.manifest),config_sha256=sha(HERE/'CONFIG.json'),environment_sha256=sha(a.environment),original_interval_analysis_commit=sm['actual_interval_analysis_commit'],raw_location='Frozen bounded derived evidence; original actual service raw remains on designated8TB',intended_summary=str(out/'SUMMARY.json'),intended_gate=str(out/'GATE.json'),new_model_calls=0,actual_reader_calls=0))
 put(out/'CONTROL_HASHES_BEFORE.json',controls);put(out/'ENVIRONMENT.json',env)
 b.style();qa=[comparison_plot(out,comparison),mechanism(out),effects(out,j)]
 assert gate(a.manifest)==c
 for r in sm['bounded_inputs']:assert sha(HERE/r['copy'])==r['sha256'] and sha(r['original'])==r['sha256']
 for r in sm['protected']:assert sha(r['path'])==r['sha256']
 assert {path:sha(path) for path in controls}==controls
 put(out/'CONTROL_HASHES_AFTER.json',controls)
 put(out/'ACTUAL_INTERVAL_COMPARISON.json',comparison)
 put(out/'SUMMARY.json',dict(figures=3,actual_source_commit=c,actual_interval_analysis_commit=sm['actual_interval_analysis_commit'],all_original_data_unchanged=True,all_v7_protected_files_unchanged=True,actual_reader_calls=0,new_model_calls=0,QA=qa))
 put(out/'GATE.json',dict(gate='PASS_FROZEN_EDITORIAL_FIGURES_NUMERIC_VECTOR',visual_review='PENDING_ACTUAL_VIEW',new_model_calls=0,actual_reader_calls=0))
 put(out/'OUTPUT_INDEX.json',[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir()) if p.is_file()])
 print(json.dumps(dict(source_commit=c,out=str(out),figures=3,new_model_calls=0,actual_reader_calls=0)))
if __name__=='__main__':main()
