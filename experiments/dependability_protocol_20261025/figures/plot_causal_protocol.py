"""Vector protocol/causal diagram, using a recorded N1 witness inset."""
from pathlib import Path
import argparse,hashlib,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
OUT=Path(__file__).resolve().parent;W=OUT.parent
ap=argparse.ArgumentParser();ap.add_argument('--pdf',action='store_true');args=ap.parse_args()
plt.rcParams.update({'font.family':'Times New Roman','font.size':9,'mathtext.fontset':'stix',
 'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','savefig.facecolor':'white'})
BLUE='#0F4D92';ORANGE='#AD6225';GREEN='#28734F';RED='#A53338';GREY='#525B68'
fig,ax=plt.subplots(figsize=(7.2,4.45));fig.subplots_adjust(left=.01,right=.99,top=.99,bottom=.01)
ax.set(xlim=(0,100),ylim=(0,100));ax.axis('off');box_text=[]
def box(x,y,w,h,text,color=GREY,face='white',fs=8.4):
 p=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.3,rounding_size=.6',ec=color,fc=face,lw=.9,zorder=3);ax.add_patch(p)
 t=ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=fs,color=color,zorder=4)
 box_text.append((p,t));return p
def arrow(a,b,color=GREY,dashed=False):
 p=FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=9,color=color,lw=.95,ls='--' if dashed else '-',zorder=2)
 ax.add_patch(p)
def line(points,color=GREY,dashed=False):
 ax.plot([p[0] for p in points],[p[1] for p in points],color=color,lw=.95,ls='--' if dashed else '-',zorder=2)
 arrow(points[-2],points[-1],color,dashed)
ax.text(1,98,'(a) A fixed write boundary; separately checked visibility and recovery',weight='bold',fontsize=9.8,va='top')
ax.add_patch(FancyBboxPatch((35,74),64,18,boxstyle='round,pad=.4',fc='#FCF1E7',ec='none',zorder=0))
ax.add_patch(FancyBboxPatch((35,47),64,23,boxstyle='round,pad=.4',fc='#EBF2F8',ec='none',zorder=0))
box(1,62,12,15,'Offered\naudio O',face='#F0F1F3')
box(18,62,15,15,'Accepted A\nsync prefix record\nbefore ACK',face='#F0F1F3',fs=7.8)
arrow((13.3,69.5),(17.6,69.5))
box(38,79,17,11,'Private job\nfrozen inputs\nmode-gated',ORANGE,fs=7.8)
box(61,79,16,11,'Owner\nfreshness',ORANGE)
box(83,79,15,11,'Exact-chain\nprovisional V',ORANGE,fs=8.1)
line([(33.4,72),(35.7,72),(35.7,84.5),(37.6,84.5)])
arrow((55.3,84.5),(60.6,84.5),ORANGE);arrow((77.3,84.5),(82.6,84.5),ORANGE)
line([(46.5,90.4),(46.5,93),(36.8,93),(36.8,86.5),(37.6,86.5)],ORANGE)
ax.text(58,92.8,'Private feedback only',fontsize=7.5,color=ORANGE,ha='left',va='center')
box(38,53,17,12,'Trusted Authority\nselects Z / P',BLUE,fs=8.1)
box(61,53,16,12,'Admission\n+ WAL C',BLUE)
box(83,53,15,12,'Certified view\nfrom durable C',BLUE,fs=8.0)
line([(33.4,66),(35.7,66),(35.7,59),(37.6,59)])
arrow((55.3,59),(60.6,59),BLUE);arrow((77.3,59),(82.6,59),BLUE)
line([(69,52.6),(69,48.8),(46.5,48.8),(46.5,52.6)],BLUE)
ax.text(58,47.3,'Canonical P parents subsequent trusted work',color=BLUE,ha='center',va='top',fontsize=7.5)
ax.text(55,71,'Display permission is not state-write permission',color=RED,ha='center',va='center',fontsize=8.1)
box(18,29,60,13,'Envelope: NORMAL / DEGRADED / CERTIFIED-ONLY / BACKPRESSURE / RECOVERY\n'
 'Observed A-C debt, actual leases/queues, current-root Consumer V',GREEN,face='#EFF6EF',fs=7.9)
line([(25,42.4),(25,61.6)],GREEN,True)
ax.text(17,49,'credit / reject',rotation=90,color=GREEN,ha='center',va='center',fontsize=7.5)
line([(78.4,35.5),(99,35.5),(99,75.8),(95.5,75.8),(95.5,78.6)],GREEN,True)
ax.text(88.8,39,'typed view\nmode only',color=GREEN,ha='center',va='center',fontsize=7.3)
line([(90.5,78.6),(80,78.6),(80,42.5),(74,42.5)],GREEN,True)
ax.text(80.9,49.5,'actual ACK',rotation=90,ha='left',va='center',color=GREEN,fontsize=7.2)
ax.text(18,26.5,'Recovery: replay A and C; fence old epochs; reapply the certified view',color=BLUE,fontsize=7.6,va='center')
ax.text(1,22.5,'(b) N1 reachability witness: a current version tag does not prove a current-root computation',weight='bold',fontsize=9.1)
box(1,6,28,13,'At the same 6-s audio boundary\nPrivate P: 23 tokens; Canonical P: 22',ORANGE,face='#FCF1E7',fs=8.0)
box(36,6,27,13,'Private target 8 s is ahead of C = 6 s\nFreshness alone does not exclude it',GREY,fs=7.9)
box(70,6,28,13,'Snapshot: one false 2-s audio credit\nFull dual-lane: incompatible view fenced',BLUE,face='#EBF2F8',fs=7.8)
arrow((29.4,12.5),(35.6,12.5));arrow((63.4,12.5),(69.6,12.5))
ax.text(1,1.5,'Full Standard is a protected positive control. Witness precedes the selected later IPC hold; no Canonical pollution.',fontsize=7.6,va='bottom')
fig.canvas.draw();renderer=fig.canvas.get_renderer();outside=[];overflow=[]
for p,t in box_text:
 b=p.get_window_extent(renderer);z=t.get_window_extent(renderer)
 if z.x0<b.x0 or z.x1>b.x1 or z.y0<b.y0 or z.y1>b.y1:overflow.append(t.get_text())
for t in fig.findobj(matplotlib.text.Text):
 if t.get_visible() and t.get_text():
  b=t.get_window_extent(renderer)
  if b.x0<fig.bbox.x0 or b.y0<fig.bbox.y0 or b.x1>fig.bbox.x1 or b.y1>fig.bbox.y1:outside.append(t.get_text())
assert not overflow and not outside,(overflow,outside)
for ext in ['svg','png']+(['pdf'] if args.pdf else []):fig.savefig(OUT/('causal_protocol_v1.'+ext),dpi=300)
plt.close(fig)
caption='Three obligations share a trusted state boundary but not a progress counter. Durable accepted input A bounds job eligibility; only trusted selection followed by existing admission/WAL checks advances Canonical C. Private results retain no state-write permission and need both owner freshness and exact-chain Consumer legality. Actual Consumer telemetry can govern credit, unissued work and typed view mode, never waive selection; running physical GPU work remains billed. Recovery must restore accepted obligations, durable selected history and a new Consumer/epoch, not retag old private coverage. ACK denotes a server logical input receipt or local Consumer observation, not a network-ACK guarantee. Inset:the actual N1 snapshot-view witness has23private versus22canonical tokens at6s and an ahead8s target. Full two_lane RevTrace/Standard exclude it; all54normalized Canonical histories match. The witness precedes the later chosen IPC hold, so it is reachability, not that intervention\'s causal effect or natural incidence. Diagram expresses obligations, not a CDE performance superiority claim.'
(OUT/'causal_protocol_v1.caption.txt').write_text(caption+'\n')
(OUT/'CAUSAL_SOURCE_MAP_v1.json').write_text(json.dumps(dict(status='SOURCE_MAPPED_VECTOR_PREVIEW_VISUAL_REVIEW_PENDING',
 source_sha256={n:hashlib.sha256((W/n).read_bytes()).hexdigest() for n in ['N1_DECISION.json','N1_VISIBLE_WITNESS_FORWARD_v1.json','formal/ENVELOPE_OBLIGATIONS.md','UNIFIED_FAULT_MATRIX_v1.md']},
 box_overflow=overflow,canvas_overflow=outside,new_GPU_measurements=False),indent=2)+'\n')
print('SOURCE_MAP_AND_BOUNDS_PASS')
