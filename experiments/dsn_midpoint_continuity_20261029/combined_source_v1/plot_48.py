"""IEEE-width figures showing every frozen fresh-process service result."""
from pathlib import Path
import argparse,csv,hashlib,json,math,platform,subprocess,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator,PercentFormatter
import numpy as np

ARMS=('R0_S0','R0_S1','R1_S0','R1_S1')
COLORS={'R0_S0':'#767676','R0_S1':'#42949E','R1_S0':'#B64342','R1_S1':'#0F4D92'}
MARKERS={'R0_S0':'o','R0_S1':'s','R1_S0':'^','R1_S1':'D'}
LABELS={'R0_S0':'Neither','R0_S1':'Two-lane only','R1_S0':'Retention only','R1_S1':'Joint'}
POINTS=('c8-sync','c8-staggered','c12-staggered','c16-staggered')
XTICKS=('8/sync','8/stg','12/stg','16/stg')
INPUTS={}

def read(p):
    b=Path(p).read_bytes();INPUTS[str(Path(p).resolve())]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest());return json.loads(b)
def values(rows,key):return [r[key] for r in rows if type(r.get(key)) in (int,float) and math.isfinite(r[key])]
def x_for(point,arm,repeat):return POINTS.index(point)+(ARMS.index(arm)-1.5)*.18+(repeat-1)*.038

def style():
    plt.rcParams.update({'font.family':['Arial','DejaVu Sans','sans-serif'],'font.size':8.5,
        'axes.titlesize':9.,'axes.labelsize':8.5,'xtick.labelsize':8.,'ytick.labelsize':8.,
        'legend.fontsize':8.,'axes.linewidth':.7,'axes.spines.top':False,'axes.spines.right':False,
        'xtick.major.width':.6,'ytick.major.width':.6,'xtick.major.size':2.5,'ytick.major.size':2.5,
        'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','savefig.facecolor':'white',
        'mathtext.fontset':'dejavusans','figure.dpi':150})

def base_axis(ax,title,ylabel):
    ax.set_title(title,loc='left',fontweight='bold',pad=6)
    ax.set_ylabel(ylabel,labelpad=3);ax.set_xticks(range(len(POINTS)),XTICKS)
    ax.set_xlabel('Sessions / arrival',labelpad=3)
    ax.set_xlim(-.5,len(POINTS)-.5);ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
    ax.grid(axis='y',alpha=.16,linewidth=.4,zorder=0);ax.set_axisbelow(True)

def dots(ax,rows,key, *, scale=1.,face=True,median=True):
    for point in POINTS:
        for arm in ARMS:
            group=sorted((r for r in rows if r['point']==point and r['arm']==arm),key=lambda r:r['repeat'])
            assert len(group)==3
            ys=[]
            for r in group:
                value=r.get(key)
                if type(value) not in (float,int) or not math.isfinite(value):continue
                value*=scale;ys.append(value)
                ax.scatter(x_for(point,arm,r['repeat']),value,s=14,marker=MARKERS[arm],
                    facecolors=COLORS[arm] if face else 'white',edgecolors=COLORS[arm],
                    linewidths=.7,zorder=4)
            if median and ys:
                x=POINTS.index(point)+(ARMS.index(arm)-1.5)*.18
                ax.vlines(x,min(ys),max(ys),color=COLORS[arm],lw=.65,zorder=2)
                ax.hlines(np.median(ys),x-.066,x+.066,color=COLORS[arm],lw=1.2,zorder=3)

def tails(ax,rows,key,threshold,title,ylabel):
    base_axis(ax,title,ylabel);dots(ax,rows,key)
    ax.axhline(threshold,color='#272727',lw=.8,ls=(0,(3,2)),zorder=1)
    ax.text(.99,threshold,('D2' if threshold==2 else 'C8')+' ',ha='right',va='bottom',fontsize=8.,
        color='#272727',transform=ax.get_yaxis_transform())
    top=max([threshold]+values(rows,key))*1.14;ax.set_ylim(0,top)

def percentages(ax,rows,key,title,ylabel):
    base_axis(ax,title,ylabel);dots(ax,rows,key,scale=100.)
    v=values(rows,key);lo=max(0.,math.floor(min(v)*20)/20*100-5) if v else 0.
    ax.set_ylim(lo,101.5);ax.yaxis.set_major_formatter(PercentFormatter(xmax=100,decimals=0))

def rollback(ax,rows):
    base_axis(ax,'c. Timely legal progress','Compatible deficit\n(audio s × wall s)');dots(ax,rows,'compatible_timely_deficit_area')
    yy=values(rows,'compatible_timely_deficit_area');ax.set_ylim(-.02*max([1.]+yy),max([1.]+yy)*1.14)

def opportunity(ax,rows):
    base_axis(ax,'b. Witnessed opportunities','Canonical updates (%)')
    chosen=[r for r in rows if r['clock_scope']=='consumer_apply']
    dots(ax,chosen,'ahead_rate_all_updates',scale=100.,face=False,median=False)
    dots(ax,chosen,'compatible_rate_all_updates',scale=100.,face=True,median=True)
    for r in chosen:
        if r['ahead_rate_all_updates'] is not None and r['compatible_rate_all_updates'] is not None:
            ax.vlines(x_for(r['point'],r['arm'],r['repeat']),100*r['compatible_rate_all_updates'],
                100*r['ahead_rate_all_updates'],color=COLORS[r['arm']],lw=.45,alpha=.65,zorder=1)
    top=max([.01]+values(chosen,'ahead_rate_all_updates'))*100*1.2
    ax.set_ylim(-.02*top,top);ax.yaxis.set_major_formatter(PercentFormatter(xmax=100,decimals=0))
    ax.text(.01,.98,'open: any ahead\nfilled: compatible',transform=ax.transAxes,va='top',fontsize=8.,
        bbox=dict(facecolor='white',edgecolor='none',alpha=.85,pad=1))

def legend(fig):
    handles=[Line2D([],[],color=COLORS[a],marker=MARKERS[a],ls='None',markersize=3.7,label=LABELS[a]) for a in ARMS]
    fig.legend(handles=handles,ncol=4,loc='upper center',bbox_to_anchor=(.5,1.005),frameon=False,
        handletextpad=.4,columnspacing=1.8)

def export(fig,out,name,caption):
    fig.canvas.draw();renderer=fig.canvas.get_renderer();outside=[]
    w,h=fig.get_size_inches()*fig.dpi
    for text in fig.findobj(matplotlib.text.Text):
        if not text.get_visible() or not text.get_text():continue
        box=text.get_window_extent(renderer)
        if box.x0< -1 or box.y0< -1 or box.x1>w+1 or box.y1>h+1:outside.append(text.get_text())
    qa=dict(figure=name,width_inches=fig.get_figwidth(),height_inches=fig.get_figheight(),
        font_minimum_pt=min(t.get_fontsize() for t in fig.findobj(matplotlib.text.Text) if t.get_visible() and t.get_text()),
        out_of_canvas_text=outside,caption=caption,synthetic_data=False)
    assert not outside,qa
    for suffix in ('pdf','svg','png'):
        fig.savefig(out/(name+'.'+suffix),dpi=350)
    (out/(name+'.caption.txt')).write_text(caption+'\n',encoding='utf8')
    try:
        import fitz
        doc=fitz.open(out/(name+'.pdf'));fonts=doc[0].get_fonts(full=True)
        qa['PDF_fonts']=[list(x) for x in fonts];qa['Type3_fonts']=[list(x) for x in fonts if 'Type3' in x]
        assert not qa['Type3_fonts'];doc.close()
    except ImportError:qa['PDF_font_check']='unavailable; configured fonttype42'
    (out/(name+'.QA.json')).write_text(json.dumps(qa,indent=2)+'\n',encoding='utf8')
    plt.close(fig)

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source-manifest',type=Path,required=True);a=p.parse_args()
    source=read(a.source_manifest);here=Path(__file__).resolve().parent
    def git(*args):return subprocess.check_output(['git','-C',str(here),*args],text=True).strip()
    assert Path(git('rev-parse','--show-toplevel')).resolve()==here and git('rev-parse','HEAD')==source['code_commit']
    assert not git('status','--porcelain','--untracked-files=all')
    assert set(git('ls-files').splitlines())=={r['path'] for r in source['files']}
    for r in source['files']:assert hashlib.sha256((here/r['path']).read_bytes()).hexdigest()==r['sha256'] and (here/r['path']).stat().st_size==r['bytes']
    rows=read(a.data/'RUN_ENDPOINTS.json');opps=read(a.data/'OPPORTUNITY_RATES.json')
    history=read(a.data/'POINT_BLOCK_CANONICAL_HISTORY.json')
    assert len(rows)==48 and len(opps)==96 and all(sum(r['point']==pt and r['arm']==arm for r in rows)==3 for pt in POINTS for arm in ARMS)
    out=a.output;out.mkdir(exist_ok=False,parents=True);style()
    fig,axes=plt.subplots(1,3,figsize=(7.15,2.4));fig.subplots_adjust(left=.065,right=.993,bottom=.22,top=.79,wspace=.40)
    tails(axes[0],rows,'display_P99',2.,'a. First actual visibility','Display P99 (s)')
    percentages(axes[1],rows,'dual_audio_fraction','b. Offered-input service','D2/C8 credit (%)')
    rollback(axes[2],rows);legend(fig)
    cap=('Four explicit development workloads: original36 plus a fixed exploratory midpoint12, not new independent source audio. Each arm has all three fresh-process runs; '
        'small horizontal ticks show medians and vertical ranges span the three observed values, without confidence-interval claims. '
        'D2/C8 credit uses every offered audio interval and original 2 s display / 8 s certified-view deadlines. '
        'Panel c is a secondary measure of later loss of previously dual-timely delivered intervals whose complete prior view is compatible with the new selected root; necessary incompatible revisions remain separate. Single-root windows are right-censored at the next Canonical root when no earlier covering view returns; original first credit is unchanged. The 16-session point expands to the metadata-nested original sources; '
        'the plot is not a pure-load universal capacity curve. No lines interpolate between workload points. '
        'Arrival phases are synchronized (sync) or staggered by 0.25 s per session (stg).')
    export(fig,out,'service_region',cap)
    fig,axes=plt.subplots(1,3,figsize=(7.15,2.4));fig.subplots_adjust(left=.065,right=.993,bottom=.22,top=.79,wspace=.40)
    tails(axes[0],rows,'commit_view_P99',8.,'a. Actual certified visibility','Certified-view P99 (s)')
    opportunity(axes[1],opps)
    supported=[dict(r,supported_audio_fraction=r['first_certified_or_same_F_raw_agreeing_timely_audio_seconds']/r['offered_audio_seconds']) for r in rows]
    percentages(axes[2],supported,'supported_audio_fraction','c. Supported timely content','Supported credit (%)');legend(fig)
    cap=('Separate certified-view timing and witnessed compatibility mechanism for the same 48 runs. '
        'Opportunity rates use all actual Canonical applications at the Consumer as denominator; open markers denote any already visible ahead view, '
        'filled markers denote a complete branch whose exact feedback ancestry reaches the selected root. '
        'This observed relative progress is an endogenous mechanism measurement. '
        'Supported credit counts first-certified content plus timely first-ahead complete views agreeing byte-for-byte with the later selected Canonical '
        'at that same visible audio boundary; it is a retrospective selected-model agreement metric, not semantic correctness or groundtruth. '
        'All offered intervals remain in its denominator. Arrival phases are synchronized (sync) or staggered by 0.25 s per session (stg).')
    export(fig,out,'service_region_mechanism',cap)
    manifest=dict(code_commit=source['code_commit'],script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        input_files=INPUTS,python=sys.version,matplotlib=matplotlib.__version__,platform=platform.platform(),
        actual_cells=48,fresh_processes_per_arm_point=3,history_comparison=history,new_model_calls=0,
        output_files=[dict(path=f.name,bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in sorted(out.iterdir())])
    (out/'FIGURE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(output=str(out),figures=2,actual_cells=48,new_model_calls=0)))

if __name__=='__main__':main()
