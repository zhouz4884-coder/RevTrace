"""Source-scoped physical-cost boundary, not a pooled scaling experiment."""
from pathlib import Path
import csv,hashlib,json,statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

W=Path(__file__).resolve().parents[1];OUT=Path(__file__).resolve().parent
P=W/'public_tables/experiments/phase_d_20261021/tables/ALL_162_SERVICE_CELLS.csv'
T=W/'public_tables/experiments/phase_n_20261021/tables/T1_CELLS.csv'
def read(p):return list(csv.DictReader(p.open(newline='',encoding='utf8')))
def median(v):return statistics.median(map(float,v))
rows=[];groups=[];phase=read(P)
for n,arrival in [(4,'staggered'),(8,'sync')]:
 for label,prefix,stage,rho in [('Fine','Fine-D','R4_strict',1),('DGFT','coarse-keep1-two_lane','R2_transfer',3),('Standard','Safe-Async','R4_strict',3)]:
  selected=[r for r in phase if r['stage']==stage and r['cell'].startswith(prefix+f'-c{n}-{arrival}-r')]
  assert len(selected)==3 and all(r['strict_task_audio_warmup_isolation']==r['baseline_valid']=='True' for r in selected)
  for r in selected:rows.append(dict(panel=f'phaseD-c{n}-{arrival}',method=label,rho=rho,cell=r['cell'],
   energy=float(r['GPU_J_per_audio_s']),display_P99=float(r['display_P99_consumer']),commit_P99=float(r['commit_P99']),
   whole_dual_pass=r['dual_2_8_pass']=='True',WER=float(r['WER']),journal='durable',clock='actual local Consumer',source=str(P.relative_to(W))))
  groups.append((f'phaseD-c{n}-{arrival}',label))
for label,prefix in [('Fine barrier','fine_certified-segment'),('Fine decoupled','fine_certified-decoupled'),
                     ('Coarse barrier','coarse-segment'),('Coarse decoupled','coarse-decoupled')]:
 selected=[r for r in read(T) if r['cell'].startswith(prefix+'-obs1-r')];assert len(selected)==3
 for r in selected:rows.append(dict(panel='T1-c16-sync',method=label,rho=1 if prefix.startswith('fine') else 3,
  cell=r['cell'],energy=float(r['gpu_j_per_audio_second']),display_P99=float(r['display_p99']),commit_P99=float(r['commit_p99']),
  whole_dual_pass=False,WER=None,journal='durable',clock='scheduler frontier (not actual Consumer)',source=str(T.relative_to(W))))
 groups.append(('T1-c16-sync',label))

plt.rcParams.update({'font.family':'Times New Roman','font.size':8.2,'mathtext.fontset':'stix',
 'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,
 'axes.linewidth':.75,'legend.frameon':False,'savefig.facecolor':'white'})
fig,axes=plt.subplots(1,3,figsize=(7.2,2.65));fig.subplots_adjust(left=.07,right=.985,top=.84,bottom=.30,wspace=.42)
colors={'Fine':'#0F4D92','DGFT':'#AD6225','Standard':'#28734F'};markers={'Fine':'o','DGFT':'^','Standard':'s'}
summaries=[]
for i,(ax,panel) in enumerate(zip(axes,['phaseD-c4-staggered','phaseD-c8-sync','T1-c16-sync'])):
 ax.axhline(2,color='#A53338',ls='--',lw=.9,zorder=0)
 for _,label in [g for g in groups if g[0]==panel]:
  rs=[r for r in rows if r['panel']==panel and r['method']==label]
  x=median(r['energy'] for r in rs);y=median(r['display_P99'] for r in rs)
  color=colors[label] if i<2 else colors['Fine' if label.startswith('Fine') else 'DGFT']
  marker=markers[label] if i<2 else ('s' if label.endswith('barrier') else 'o')
  ax.errorbar(x,y,xerr=[[x-min(r['energy'] for r in rs)],[max(r['energy'] for r in rs)-x]],
   yerr=[[y-min(r['display_P99'] for r in rs)],[max(r['display_P99'] for r in rs)-y]],
   color=color,marker=marker,ms=4.5,capsize=2,lw=.9,mec='white',mew=.45,zorder=3)
  text=label if i<2 else label.replace('decoupled','async')
  xy=(0,9) if i<2 else (0,9)
  if label=='DGFT':xy=(0,-16)
  if i==2 and label=='Fine decoupled':xy=(0,-8)
  if i==2 and label=='Coarse decoupled':xy=(0,-8)
  if i==2 and label=='Fine barrier':xy=(0,-14)
  ax.annotate(text,(x,y),xytext=xy,textcoords='offset points',ha='center',fontsize=6.8,color=color)
  summaries.append(dict(panel=panel,method=label,energy_median=x,display_P99_median=y,
   commit_P99_median=median(r['commit_P99'] for r in rs),whole_dual_passes=sum(r['whole_dual_pass'] for r in rs),
   WER_median=None if rs[0]['WER'] is None else median(r['WER'] for r in rs)))
 ax.set_xlabel('GPU J / audio-s',labelpad=3)
 ax.set_title(['(a) c4, staggered','(b) c8, synchronous','(c) c16, synchronous'][i],fontsize=8.4,loc='left',pad=7)
 ax.tick_params(labelsize=7,length=3,pad=2)
 if i<2:ax.set_ylim(.7,2.3)
 else:ax.set_ylim(0,18)
 if i==0:ax.set_xlim(80,102);ax.set_ylabel('Display P99 (s)',labelpad=3)
 elif i==1:ax.set_xlim(45,62)
 else:ax.set_xlim(26,51)
 ax.set_xticks([[80,90,100],[45,50,55,60],[30,40,50]][i])
 ax.text(.98,.97,'2s display target' if i<2 else 'All 3 repeats miss 2s',transform=ax.transAxes,
  fontsize=6.8,ha='right',va='top',color='#A53338')
fig.text(.07,.075,'(a,b) Phase D: actual Consumer; three repeats per point.  (c) repaired T1: scheduler-frontier clock.',fontsize=7)
fig.text(.07,.018,'Different audio/arrival contracts; not one scaling curve. Error bars: range, not CI. All are durable.',fontsize=7)
fig.canvas.draw();renderer=fig.canvas.get_renderer();bounds=fig.bbox;clipped=[]
for text in fig.findobj(matplotlib.text.Text):
 if text.get_visible() and text.get_text():
  b=text.get_window_extent(renderer)
  if b.x0<bounds.x0-1 or b.y0<bounds.y0-1 or b.x1>bounds.x1+1 or b.y1>bounds.y1+1:clipped.append(text.get_text())
assert not clipped,clipped
overlap=[]
for ax in axes:
 texts=[t for t in ax.texts if t.get_text()]
 for i,a in enumerate(texts):
  for b in texts[i+1:]:
   if a.get_window_extent(renderer).overlaps(b.get_window_extent(renderer)):overlap.append([a.get_text(),b.get_text()])
assert not overlap,overlap
for ext in ['pdf','svg','png']:fig.savefig(OUT/('cost_boundary_v1.'+ext),dpi=300)
plt.close(fig)
with (OUT/'COST_BOUNDARY_SOURCE_v1.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
caption='Actual GPU energy versus display P99 under three distinct finite workloads. Each point is the median of three measured runs; error bars show their full range. Phase D panels use task-isolated final R4_strict/R2_transfer and actual local Consumer clocks. Fine uses rho1; DGFT and complete Standard use rho3. At c4, Fine/Coarse WER is3.540/3.982%; at c8,2.421/2.663%. Commit P99 remains distinct (see source table), so the2s line applies only to display. T1 uses full-observer repaired v4 at c16, not Phase D inputs or Consumer semantics; its barrier/decoupled points are not joined to the other facets. No exclusive advantage over Standard, steady-state capacity, universal scaling law, or nonmonotonic phase transition follows.'
(OUT/'cost_boundary_v1.caption.txt').write_text(caption+'\n')
(OUT/'FIGURE_AUDIT_v1.json').write_text(json.dumps(dict(status='SOURCE_BYTES_RECOUNT_AND_BOUNDS_PASS_VISUAL_REVIEW_PENDING',
 font=font_manager.findfont('Times New Roman'),inputs={str(p.relative_to(W)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [P,T]},
 rows=len(rows),summaries=summaries,renderer_clipped_text=clipped,annotation_pair_overlaps=overlap,vector_exports=['pdf','svg'],no_new_GPU=True),indent=2)+'\n')
print(json.dumps(dict(source_rows=len(rows),points=len(summaries),out=str(OUT/'cost_boundary_v1.png'))))
