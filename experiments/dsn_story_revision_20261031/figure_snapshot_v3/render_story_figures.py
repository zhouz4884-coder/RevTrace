"""Frozen writing figures from bounded original measurements; no neural calls."""
from pathlib import Path
import argparse,hashlib,json,platform,subprocess,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import numpy as np
import fitz
import base_renderer as b
from extract_comparison import extract_comparison,controls

HERE=Path(__file__).resolve().parent
WIDTH=7.125
ARMS=('R0_S0','R0_S1','R1_S0','R1_S1')
NAMES=('Recompute +\nsnapshot','View only','Compute only','RevTrace')
BLUE=b.BLUE;TEAL=b.TEAL;GRAY=b.GRAY;INK=b.INK;RED=b.RED
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,o):Path(p).write_bytes((json.dumps(o,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode())
def git(*args):return subprocess.check_output(['git','-C',str(HERE),*args],text=True).strip()
def gate(mp):
 m=json.loads(mp.read_bytes());commit=git('rev-parse','HEAD')
 assert Path(git('rev-parse','--show-toplevel')).resolve()==HERE
 assert not git('status','--porcelain','--untracked-files=all')
 assert m['code_commit']==commit and set(git('ls-files').splitlines())=={r['path'] for r in m['files']}
 for row in m['files']:
  p=HERE/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
 return commit
def environment():
 return dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
   matplotlib=matplotlib.__version__,numpy=np.__version__,pymupdf=fitz.VersionBind,new_model_calls=0)

def case(out,j):
 s=j['case_summary'];t=j['case_trace'];snap=j['case_snapshots']
 D,L,C=[s[k] for k in ('D','loss_start','C')]
 assert [r['relative_to_offered_F_seconds'] for r in snap[1:]]==[D,L,C]
 assert s['compatible'] and s['actual_input_prompt_equals_selected_root_P'] and s['first_and_recovered_complete_text_equal']
 fig,ax=plt.subplots(figsize=(WIDTH,2.35))
 fig.subplots_adjust(left=.09,right=.99,bottom=.235,top=.82)
 ax.step([r['t'] for r in t],[r['visible_F'] for r in t],where='post',color=TEAL,lw=1.75,label='Actual whole view')
 ax.step([r['t'] for r in t],[r['certified_F'] for r in t],where='post',color=BLUE,lw=1.25,ls=(0,(4,2)),label='Selected-state coverage')
 ax.add_patch(Rectangle((L,12),C-L,2,facecolor='#FAEEEE',edgecolor=RED,hatch='////',lw=.4,zorder=0))
 ax.axvline(2,color=INK,ls=(0,(2,2)),lw=.8)
 props=dict(arrowstyle='->',color=GRAY,lw=.65,shrinkB=3)
 ax.plot(D,14,'o',ms=3.3,color=TEAL);ax.plot(L,12,'x',ms=4,color=RED,mew=1.1);ax.plot(C,14,'D',ms=3.3,color=BLUE)
 ax.annotate('Visible: 1.444 s',xy=(D,14),xytext=(.35,14.75),fontsize=9,arrowprops=props,va='bottom')
 ax.annotate('Compatible update: 1.544 s\nwhole view withdrawn',xy=(L,12),xytext=(.12,11.25),fontsize=8.5,arrowprops=props,va='top')
 ax.annotate('Same text returns: 3.720 s',xy=(C,14),xytext=(2.83,14.75),fontsize=9,arrowprops=props,va='bottom')
 ax.text(2.72,13.0,'2.176 s\nvisibility gap',color=RED,ha='center',va='center',fontsize=9,
   bbox=dict(facecolor='white',edgecolor='none',alpha=.95,pad=1.4))
 ax.text(2.05,10.65,'D2 read point:\ninterval absent',fontsize=8.5,va='bottom')
 ax.set(xlim=(0,4.25),ylim=(9.6,15.45),xticks=[0,1,2,3,4],yticks=[10,12,14],
  xlabel='Wall time since this interval became ready (s)',ylabel='Audio frontier (s)')
 ax.grid(axis='y',alpha=.15,lw=.4)
 fig.legend(*ax.get_legend_handles_labels(),loc='upper center',ncol=2,bbox_to_anchor=(.53,1.01),columnspacing=2)
 cap=('Meeting first-delivery deadlines does not guarantee continued availability. '
 'The same complete interval appears at1.444s, is withdrawn under a compatible selected update at1.544s, '
 'and returns with identical text at3.720s. All times use its original ready clock. '
 'The2.176s shaded gap spans the original D2 read; first display D2 and certified C8 both pass for this interval. '
 'This actual c16-overload computation-only case introduces37raw code points including whitespace; '
 'it is not natural prevalence or a measured RevTrace counterfactual.')
 return b.export(fig,out,'timely_full_interval_case',cap,'measured single-arm explanatory trace',
  dict(D=D,withdrawal=L,certified_return=C,gap=C-L,new_raw_code_points=37,original_D2=2,
   original_C8=8,whole_run_D2=False,paired_counterfactual=False))

def mechanism(out):
 fig=plt.figure(figsize=(WIDTH,3.0));ax=fig.add_axes([.004,.015,.992,.98]);ax.axis('off');ax.set(xlim=(0,WIDTH),ylim=(0,3.0))
 txt=b.txt;box=b.box;arrow=b.arrow
 txt(ax,.08,2.88,'(a) Confirm the input; preserve the original selection',ha='left',fontweight='bold')
 box(ax,.10,2.28,1.18,.42,'Selected '+r'$P_2$',BLUE,'#EAF1F8')
 box(ax,1.57,2.28,1.37,.42,'[EL] '+r'$\widehat P_2=P_2$'+'?',BLUE,'#EAF1F8')
 arrow(ax,(1.28,2.49),(1.57,2.49),BLUE)
 box(ax,3.23,2.16,1.72,.66,'Keep running full call '+r'$j_3$'+'\nfrozen '+r'$\widehat P_2$'+'\nASR → Correct/Update',TEAL,'#F0F8F7')
 arrow(ax,(2.94,2.49),(3.23,2.49),BLUE)
 box(ax,5.08,2.10,1.93,.78,'Original Correct/Update result '+r'$P_3$'+'\n[AU] complete result +\nchecked parent\nsync → install',BLUE,'#EAF1F8')
 arrow(ax,(4.95,2.49),(5.08,2.49),BLUE)
 txt(ax,.10,1.86,'Match: keep call    Refuted: reject    Unknown: may run/buffer; no commit',ha='left',color=GRAY)
 txt(ax,4.12,1.65,'Own ASR forecast '+r'$\widehat P_3$'+' may differ from '+r'$P_3$',color=TEAL)
 ax.plot([.08,7.04],[1.46,1.46],color='#BDBDBD',lw=.6)
 txt(ax,.08,1.28,'(b) Apply the same selected update; check the whole visible view',ha='left',fontweight='bold')
 box(ax,.10,.49,1.18,.42,'Selected '+r'$P_2$',BLUE,'#EAF1F8')
 box(ax,1.66,.87,1.62,.36,'Snapshot replacement',GRAY,'#F4F4F4')
 arrow(ax,(1.28,.78),(1.66,1.05),GRAY)
 box(ax,3.67,.87,1.58,.36,'Render '+r'$P_2$'+'; lose ahead '+r'$h$',GRAY,'#F4F4F4')
 arrow(ax,(3.28,1.05),(3.67,1.05),GRAY)
 box(ax,1.66,.28,1.62,.39,'[SUP] '+r'$S(P_2,h)$'+'?',TEAL,'#F0F8F7')
 arrow(ax,(1.28,.61),(1.66,.48),BLUE)
 box(ax,3.67,.28,1.58,.39,'Supported: retain whole '+r'$h$',TEAL,'#F0F8F7')
 arrow(ax,(3.28,.48),(3.67,.48),TEAL)
 box(ax,5.54,.28,1.47,.39,'Unsupported:\nwithdraw '+r'$h$',RED,'#FAEEEE',ls=(0,(3,2)))
 ax.plot([3.28,3.45,6.275],[.61,.76,.76],color=RED,ls=(0,(2,2)),lw=.8)
 arrow(ax,(6.275,.76),(6.275,.67),RED,ls=(0,(2,2)))
 txt(ax,5.97,1.02,r'$h$'+' is the ahead\nprovisional whole view',color=TEAL)
 txt(ax,.10,.075,'Schematic; not to scale. Input confirmation does not endorse the forecast.',ha='left',color=GRAY)
 cap=('A selected revision has separate consequences for computation and presentation. '
 '(a)[EL] The selected parentP2 confirms the complete frozen input of callj3. '
 'Its own forecastP3-hat may be wrong;[AU] original Correct/Update still suppliesP3 and durable selection requires complete, authorized evidence. '
 '(b) The sameP2 update would replace an ahead whole viewh under snapshot consumption. '
 '[SUP] Retainh only with its complete dependency path; otherwise render the selected cut. '
 'Unknown future input is not refuted input and grants no commit authority. '
 'Full input/frontier/contract bindings and source assumptions are given in the method. This is a causal schematic, not a measured timeline.')
 return b.export(fig,out,'coordination_protocol',cap,'causal mechanism schematic; no measured timings',
  dict(judgment_tags=['EL','AU','SUP'],original_selection_preserved=True,shared_selected_state='P2',
   same_whole_view='h',unknown_not_refuted=True,no_prediction_to_selected_shortcut=True,producer_death_in_execution_text=True))

def core_rows(j):
 rows=[r for r in j['core_runs'] if r['phase']=='primary' and r['adapter']=='qwen' and r['rho']==1 and r['arrival']=='staggered']
 assert len(rows)==15 and all(not r['whole_run_dual_P99_pass'] for r in rows)
 totals=[]
 for arm,withdraw,credit in zip(ARMS,(12,1,17,0),(654.115,628.435,664.150,680.760)):
  group=sorted([r for r in rows if r['arm']==arm],key=lambda x:x['cohort']);assert [r['cohort'] for r in group]==['A','B','C']
  vals=dict(arm=arm,withdrawals=sum(r['audio_rollback_events'] for r in group),credit=sum(r['dual_credited_audio_seconds'] for r in group),
    offered=sum(r['offered_audio_seconds'] for r in group),cohorts=[dict(cohort=r['cohort'],cell_id=r['cell_id'],withdrawals=r['audio_rollback_events'],
      credit=r['dual_credited_audio_seconds'],offered=r['offered_audio_seconds']) for r in group])
  assert vals['withdrawals']==withdraw and abs(vals['credit']-credit)<1e-9 and abs(vals['offered']-714.110)<1e-9
  table=next(r for r in j['core_tables']['tables'] if all(r[k]==v for k,v in dict(phase='primary',adapter='qwen',rho=1,arrival='staggered',arm=arm).items()))
  assert table['audio_rollback_events_sum']==withdraw and abs(table['dual_credited_audio_seconds_sum']-credit)<1e-9
  totals.append(vals)
 return totals

def native_rows(j):
 rows=[]
 for proposed in j['proposed_values']['rows']:
  key=('paired' if proposed['bank']=='matched' else 'resident')+'/'+proposed['policy'];g=j['native_content']['groups'][key]
  p=g['posterior_whole_text_support']['raw'];assert p['original_credit_unknown_seconds']==0
  vals=dict(bank=proposed['bank'],policy=proposed['policy'],offered=g['offered_audio_seconds'],timely=g['original_dual_credit_audio_seconds'],
   matching=p['original_credit_supported_seconds'],unmatched=p['original_credit_mismatching_seconds'],passes=g['original_request_gate_passes'],requests=g['request_instances'])
  vals['untimely']=vals['offered']-vals['timely']
  counts=p['all_offered_frontier_counts'];assert sum(counts.values())==136
  assert g['content']['raw']['introduced_code_point_occurrences']==180 and g['content']['raw']['retracted_occurrence_code_points']==14
  for actual,field in [('offered','offered_s'),('timely','timely_s'),('matching','timely_same_frontier_selected_text_s'),
    ('unmatched','timely_without_same_frontier_text_agreement_s'),('untimely','not_timely_s')]:assert abs(vals[actual]-proposed[field])<1e-9
  assert vals['passes']==proposed['pass_count'] and vals['requests']==8 and abs(sum(vals[k] for k in ('matching','unmatched','untimely'))-vals['offered'])<1e-9
  rows.append(vals)
 return rows

def matrix(ax,totals):
 ax.set(xlim=(-.32,2.04),ylim=(-.08,2.15));ax.axis('off')
 b.txt(ax,.96,2.055,'View retention S',fontweight='bold')
 for x,label in [(.5,'Off'),(1.5,'On')]:b.txt(ax,x,1.88,label,color=GRAY)
 b.txt(ax,-.22,.86,'Computation R',rotation=90,fontweight='bold')
 for y,label in [(1.26,'Off'),(.47,'On')]:b.txt(ax,-.065,y,label,rotation=90,color=GRAY)
 for i,row in enumerate(totals):
  x=(i%2)*1.0+.05;y=1.61-(i//2)*.82-.73
  color=BLUE if row['arm']=='R1_S1' else GRAY
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
   left+=value
  ax.text(102,y,f"{row['passes']}/8",va='center',fontsize=8.5,color=BLUE if row['policy']=='fullcall' else GRAY)
 ax.set(yticks=ys,yticklabels=['Conservative','RevTrace','Conservative','RevTrace'],xlim=(0,114),ylim=(-.4,3.8),xticks=[0,50,100],xlabel='Fraction of offered audio (%)')
 ax.spines['left'].set_visible(False);ax.spines['bottom'].set_bounds(0,100);ax.tick_params(axis='y',length=0,pad=4)
 ax.text(0,3.70,'Matched trials',fontsize=9,fontweight='bold');ax.text(0,1.50,'Resident requests',fontsize=9,fontweight='bold')
 ax.text(103,3.70,'Pass',fontsize=8.5,ha='center',color=GRAY)
 handles=[Rectangle((0,0),1,1,color=BLUE),Rectangle((0,0),1,1,facecolor='#B5C8D8',edgecolor='#666666',hatch='////'),Rectangle((0,0),1,1,facecolor='#F2F2F2',edgecolor='#666666')]
 return handles

def effects(out,j):
 totals=core_rows(j);native=native_rows(j)
 fig=plt.figure(figsize=(WIDTH,3.40))
 a=fig.add_axes([.025,.28,.405,.59]);c=fig.add_axes([.60,.30,.345,.57])
 matrix(a,totals);handles=native_bars(c,native)
 fig.text(.03,.965,'(a) Joint retention resolves the conflict',fontsize=9,fontweight='bold',va='top')
 fig.text(.49,.965,'(b) More matching content meets deadlines',fontsize=9,fontweight='bold',va='top')
 fig.text(.235,.14,'714.110 s offered per arm; three cohorts',fontsize=8.5,ha='center',color=GRAY)
 fig.text(.235,.205,'Big: frontier withdrawals; below: timely audio (s)',fontsize=8.5,ha='center',color=GRAY)
 fig.legend(handles,['Timely + text match','Timely + no text match','Misses a deadline'],
   loc='lower center',bbox_to_anchor=(.52,.005),ncol=3,fontsize=8.5,columnspacing=1.6,handlelength=1.4,handletextpad=.5)
 cap=('Joint retention preserves delivery while full input confirmation makes existing content timely. '
 '(a) Four arms share selected histories in the predeclared24-speaker Qwen,rho1,staggered stratum. '
 'Each cell shows total frontier withdrawals and seconds of offered audio meeting both deadlines; each arm offers714.110s over three cohorts. '
 'All15runs including the alternative joint positive control fail whole-runD2. '
 '(b) Final native matched and resident banks each offer66.33975s per policy from four sources and two repeats. '
 'The three segments partition that common denominator: timely with posterior whole first-view agreement at its actual frontier, timely without that agreement, or missing at least one original deadline. '
 'Agreement is with selected model text, not human correctness. Each bank/policy introduces180 and retracts14code-point occurrences; passes are6/8 and7/8 for RevTrace. '
 'The native bank is not a new factorial continuity test. Values and all raw-cohort points remain in the companion evidence.')
 put(out/'MAIN_EFFECT_NUMERIC_VALUES.json',dict(core=totals,native=native))
 return b.export(fig,out,'composition_and_content',cap,'measured core factorization plus retrospective native text partition',
  dict(core_offered_seconds=714.110,core_independent_speakers=24,cohorts=3,core_whole_run_D2_passes=0,
   native_offered_seconds=66.33975,native_independent_sources=4,new_neural_runs=0,no_unknown_category=True,
   original_raw_cohort_points_in_companion=True,human_accuracy_claim=False))

def factorial_detail(out,j):
 totals=core_rows(j)
 fig,axes=plt.subplots(1,2,figsize=(WIDTH,2.6));fig.subplots_adjust(left=.075,right=.98,bottom=.25,top=.77,wspace=.28)
 for ax,key,title,ylab in zip(axes,('withdrawals','credit'),('(a) Frontier withdrawals','(b) Audio meeting both deadlines'),('Count per cohort','Fraction of offered audio (%)')):
  for cohort_i,marker in enumerate(('o','s','^')):
   ys=[row['cohorts'][cohort_i][key] if key=='withdrawals' else 100*row['cohorts'][cohort_i]['credit']/row['cohorts'][cohort_i]['offered'] for row in totals]
   ax.plot(range(4),ys,lw=.65,color='#A7A7A7',zorder=1)
   ax.scatter(np.arange(4)+(cohort_i-1)*.035,ys,marker=marker,s=21,facecolor='white' if cohort_i==1 else GRAY,edgecolor=INK,linewidth=.7,zorder=3)
  ax.set_xticks(range(4),NAMES);ax.set_xlim(-.3,3.3);ax.set_title(title,loc='left',fontweight='bold');ax.set_ylabel(ylab)
  ax.grid(axis='y',color='#DDDDDD',lw=.4)
  if key=='withdrawals':ax.set_ylim(-.3,8);ax.set_yticks([0,2,4,6,8])
  else:ax.set_ylim(0,100);ax.set_yticks([0,25,50,75,100])
 handles=[Line2D([],[],ls='none',marker=m,color=GRAY,label='Cohort '+name,markerfacecolor='white' if name=='B' else GRAY) for m,name in zip(('o','s','^'),('A','B','C'))]
 fig.legend(handles=handles,ncol=3,loc='upper center',bbox_to_anchor=(.5,.99))
 cap=('All three original cohorts show the predeclared factorization. Points are actual cohort runs, paired lines join the same cohort across arms; there are no confidence intervals. '
 'Withdrawals are counts per cohort while deadline coverage is normalized by that cohort original offered audio. The main matrix instead reports sums over all three cohorts. '
 'The24speakers are independent acoustic sources; repeats/arms do not add sources. All15headline runs fail whole-runD2, and the fresh-processcohortA repeat has a negative credit interaction retained in the paper.')
 return b.export(fig,out,'factorial_cohorts_detail',cap,'companion original raw-cohort points',dict(actual_cohorts=3,actual_runs=12,confidence_intervals=False,paired_lines=True))

def comparison_plot(out,result):
 fig,axes=plt.subplots(2,1,sharex=True,figsize=(WIDTH,2.75))
 fig.subplots_adjust(left=.095,right=.985,bottom=.19,top=.85,hspace=.27)
 end=max(4.35,max(max(r['first_visible'],r['first_certified']) for r in result['arms'].values())+.3)
 top=max(14,max(p['visible_F'] for r in result['arms'].values() for p in r['complete_trace'] if 0<=p['t']<=end))
 for ax,arm,title in zip(axes,('R1_S0','R1_S1'),('(a) Computation retention only','(b) RevTrace: joint retention')):
  r=result['arms'][arm];trace=r['complete_trace'];x=[p['t'] for p in trace]
  ax.step(x,[p['visible_F'] for p in trace],where='post',color=TEAL,lw=1.5,label='Actual whole view')
  ax.step(x,[p['certified_F'] for p in trace],where='post',color=BLUE,lw=1.15,ls=(0,(4,2)),label='Selected-state coverage')
  for window in r['observed_target_loss_windows']:
   ax.add_patch(Rectangle((window['start'],12),window['end']-window['start'],2,facecolor='#FAEEEE',edgecolor=RED,hatch='////',lw=.35))
  ax.axvline(2,color=INK,ls=(0,(2,2)),lw=.75);ax.axhline(14,color=GRAY,lw=.5,ls=(0,(1,2)))
  ax.set(xlim=(0,end),ylim=(9.6,top+1.1),yticks=list(range(10,int(top)+1,2)),xticks=list(range(int(end)+1)));ax.set_title(title,loc='left',fontsize=9,fontweight='bold',pad=3)
  miss_note=f" (D2 +{(r['first_visible']-2)*1000:.1f} ms)" if not r['first_D2_pass'] else ''
  ax.text(.985,.09,f"First coverage: {r['first_visible']:.3f} s{miss_note}; selected: {r['first_certified']:.3f} s",
   transform=ax.transAxes,ha='right',va='bottom',fontsize=8.5,bbox=dict(facecolor='white',edgecolor='none',alpha=.93,pad=1))
  ax.grid(axis='y',alpha=.13,lw=.4)
 gap=next(w for w in result['arms']['R1_S0']['observed_target_loss_windows'] if w['classification']=='compatible')
 axes[0].text((gap['start']+gap['end'])/2,13.0,f"{gap['gap_seconds']:.3f} s gap",ha='center',va='center',fontsize=8.5,color=RED,
  bbox=dict(facecolor='white',edgecolor='none',alpha=.95,pad=1))
 axes[-1].set_xlabel('Wall time since the same input interval became ready in each run (s)')
 fig.text(.023,.52,'Audio frontier (s)',rotation=90,va='center',fontsize=8.5)
 fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',ncol=2,bbox_to_anchor=(.58,1.02),columnspacing=2)
 cap=('Actual policy runs on the same input interval can have different timing. '
 'Both panels track the same source and original12–14s non-EOS interval from their own original ready clocks. '
 'The computation-only run reproduces the measured1.444/1.544/3.720s events and2.176s compatible gap; '
 'the RevTrace panel is reconstructed independently from its actual Consumer applications. '
 'Selected updates and provisional objects differ between executions; this is not a same-interleaving counterfactual or proof that the second run preserved the first run\'s object. '
 'Each panel refers to its own actual whole view; whole-text and actual-frontier comparisons are recorded separately. '
 'Both runs are c16-overload observations; original cohort and48-run denominators are unchanged.')
 return b.export(fig,out,'timely_interval_comparison',cap,'actual same-input two-arm observations, not counterfactual',
  dict(same_input_interval=True,own_ready_clocks=True,same_execution_interleaving=False,
   first_visible_whole_text_equal_across_arms=result['first_visible_whole_text_equal_across_arms'],
   arm_endpoints={a:{k:r[k] for k in ('first_visible','first_certified','first_D2_pass','first_C8_pass')} for a,r in result['arms'].items()}))

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--environment',type=Path,required=True);p.add_argument('--root-preflight',type=Path,required=True);a=p.parse_args()
 commit=gate(a.manifest);env=json.loads(a.environment.read_bytes());assert env==environment()
 root=json.loads(a.root_preflight.read_bytes());assert root['gate']=='SOURCE_IDENTITY_PASS' and root['code_commit']==commit and root['manifest_sha256']==sha(a.manifest)
 control_hashes={str(p):sha(p) for p in [a.manifest,a.environment,a.root_preflight,HERE/'CONFIG.json',HERE/'SOURCE_MAP.json']}
 sm=json.loads((HERE/'SOURCE_MAP.json').read_bytes());inputs={}
 assert json.loads((HERE/'CONFIG.json').read_bytes())['input_map_sha256']==sha(HERE/'SOURCE_MAP.json')
 for row in sm['bounded_inputs']:
  p=HERE/row['copy'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'] and sha(row['original'])==row['sha256']
  inputs[row['key']]=json.loads(p.read_bytes())
 for row in sm.get('dependencies',[]):assert sha(HERE/row['path'])==row['sha256'] and sha(row['original'])==row['sha256']
 inventory={r['path']:r for r in inputs['comparison_download_inventory']}
 for row in inputs['comparison_index']['input_files']:
  original=inventory[row['remote_extracted_path']]
  assert original['bytes']==row['bytes'] and original['sha256']==row['sha256']
 for row in sm['protected_v4_files']:assert sha(row['path'])==row['sha256']
 for row in sm['protected_v2_artwork']:assert sha(row['path'])==row['sha256']
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 put(out/'ENVIRONMENT.json',env);put(out/'CONTROL_HASHES_BEFORE.json',control_hashes)
 put(out/'RUN_RECORD.json',dict(experiment_id=json.loads((HERE/'CONFIG.json').read_bytes())['experiment_id'],
  actual_figure_source_commit=commit,actual_interval_analysis_source_commit=sm['actual_interval_analysis_source_commit'],source_manifest_sha256=sha(a.manifest),frozen_config_sha256=sha(HERE/'CONFIG.json'),
  environment_sha256=sha(a.environment),raw_result_location='Pinned bounded measurement copies; original raw stays on8TB',
  intended_summary=str(out/'SUMMARY.json'),intended_gate=str(out/'GATE.json'),new_model_calls=0,operation='writing artwork only'))
 controls_result=controls();put(out/'COMPARISON_RAM_CONTROLS.json',controls_result)
 comparison=inputs['actual_interval_comparison'];assert comparison['status']=='PASS_ACTUAL_TWO_ARM_INTERVAL_OBSERVATIONS'
 assert inputs['actual_interval_analysis_receipt']['actual_figure_source_commit']==sm['actual_interval_analysis_source_commit']=='73026a11f6db202d723e6028ad85e6833888ec78'
 put(out/'ACTUAL_INTERVAL_COMPARISON.json',comparison)
 b.style();qa=[case(out,inputs),mechanism(out),effects(out,inputs),b.plot_workloads(out,inputs['run_endpoints_48']),factorial_detail(out,inputs),comparison_plot(out,comparison)]
 assert gate(a.manifest)==commit
 for row in sm['bounded_inputs']:assert sha(HERE/row['copy'])==row['sha256'] and sha(row['original'])==row['sha256']
 for row in sm['protected_v4_files']:assert sha(row['path'])==row['sha256']
 for row in sm['protected_v2_artwork']:assert sha(row['path'])==row['sha256']
 for row in sm.get('dependencies',[]):assert sha(HERE/row['path'])==row['sha256'] and sha(row['original'])==row['sha256']
 assert {path:sha(path) for path in control_hashes}==control_hashes
 put(out/'CONTROL_HASHES_AFTER.json',control_hashes)
 put(out/'SUMMARY.json',dict(figures=len(qa),main_candidates=3,companion_figures=3,actual_figure_source_commit=commit,actual_interval_analysis_source_commit=sm['actual_interval_analysis_source_commit'],
  all_original_values_unchanged=True,all_48_runs_retained=True,all_12_core_cohort_rows_retained=True,
  native_four_rows_match_proposed_and_frozen=True,protected_v4_files_unchanged=True,new_model_calls=0,figure_QA=qa))
 put(out/'GATE.json',dict(gate='PASS_FROZEN_WRITING_FIGURE_SOURCE_NUMERIC_AND_VECTOR_QA',visual_review='PENDING_ACTUAL_PDF_AND_GRAYSCALE_REVIEW',new_model_calls=0))
 put(out/'OUTPUT_INDEX.json',[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir()) if p.is_file()])
 print(json.dumps(dict(out=str(out),source_commit=commit,figures=len(qa),new_model_calls=0)))
if __name__=='__main__':main()
