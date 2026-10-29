"""Two original-clock actual service traces at a shared compatible root."""
from pathlib import Path
import argparse,hashlib,json,platform,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
from trace_extract import source_gate

def read(p):return json.loads(Path(p).read_text())
def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=read(a.source_manifest);source_gate(source);summary=read(a.data/'SUMMARY.json');assert summary['gate']=='PASS_SAME_SELECTED_HISTORY_AND_SHARED_COMPATIBLE_ROOT'
    colors={'R1_S0':'#B64342','R1_S1':'#0F4D92'};arms=('R1_S0','R1_S1');data={};proofs={}
    for arm in arms:
        rows=read(a.data/arm/'CONSUMER.json');proof=read(a.data/arm/'PROOF.json');proofs[arm]=proof
        x=[r['observed_perf']-proof['original_source_origin_perf'] for r in rows]
        visible=[r['valid_visible_frontier']/16000 for r in rows];certified=[r['certified_frontier']/16000 for r in rows]
        recovery=next(r['observed_perf']-proof['original_source_origin_perf'] for r in rows if r['certified_frontier']>=proof['before_visible_F'])
        data[arm]=dict(x=x,visible=visible,certified=certified,recovery=recovery)
    lo=min(proofs[arm]['Consumer_canonical_apply_seconds'] for arm in arms)-2.
    hi=max(data[arm]['recovery'] for arm in arms)+.45
    yf=summary['shared_F']/16000;yv=proofs['R1_S0']['before_visible_F']/16000
    plt.rcParams.update({'font.family':['Arial','DejaVu Sans','sans-serif'],'font.size':8.5,'axes.labelsize':8.5,
        'axes.titlesize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'axes.linewidth':.7,
        'axes.spines.right':False,'axes.spines.top':False,'pdf.fonttype':42,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,2,figsize=(7.15,2.4),sharey=True)
    fig.subplots_adjust(left=.08,right=.99,bottom=.24,top=.78,wspace=.19)
    for ax,arm,title in zip(axes,arms,('a. Retain computation; snapshot consumption','b. Joint coordination')):
        d=data[arm];proof=proofs[arm];at=proof['Consumer_canonical_apply_seconds']
        ax.step(d['x'],d['visible'],where='post',color=colors[arm],lw=1.5,zorder=3)
        ax.step(d['x'],d['certified'],where='post',color='#4D4D4D',lw=1.1,ls=(0,(4,2)),zorder=4)
        ax.plot(at,yf,'o',color='#272727',ms=3,zorder=5);ax.axvline(at,color='#767676',ls=(0,(1,2)),lw=.65)
        ax.set(xlim=(lo,hi),ylim=(yf-2.5,yv+.65),xlabel='Elapsed from original session arrival (s)')
        ax.set_title(title,loc='left',fontweight='bold',pad=8);ax.xaxis.set_major_locator(MaxNLocator(nbins=5));ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
        ax.grid(axis='y',alpha=.15,lw=.5)
        if arm=='R1_S0':
            ax.fill_between([at,d['recovery']],[yf,yf],[yv,yv],color=colors[arm],alpha=.13,zorder=1)
            ax.annotate('Compatible whole view\nwithdrawn',xy=(at+.03,yf+.2),xytext=(at-.8,yf-1.8),fontsize=8,
                arrowprops=dict(arrowstyle='->',lw=.65,color=colors[arm]),color=colors[arm])
        else:
            ax.annotate('Compatible whole view\nkept provisional',xy=(at+.05,yv),xytext=(at-.8,yf-1.7),fontsize=8,
                arrowprops=dict(arrowstyle='->',lw=.65,color=colors[arm]),color=colors[arm])
    axes[0].set_ylabel('Audio frontier (s)')
    fig.legend(handles=[Line2D([],[],color=colors['R1_S0'],lw=1.5,label='Visible: retention only'),
        Line2D([],[],color=colors['R1_S1'],lw=1.5,label='Visible: joint'),
        Line2D([],[],color='#4D4D4D',lw=1.1,ls=(0,(4,2)),label='Certified')],
        loc='upper center',bbox_to_anchor=(.5,1.005),ncol=3,frameon=False,columnspacing=2.)
    out=a.output;out.mkdir(parents=True,exist_ok=False);fig.canvas.draw();renderer=fig.canvas.get_renderer();w,h=fig.get_size_inches()*fig.dpi
    outside=[]
    for t in fig.findobj(matplotlib.text.Text):
        if not t.get_visible() or not t.get_text():continue
        box=t.get_window_extent(renderer)
        if box.x0< -1 or box.y0< -1 or box.x1>w+1 or box.y1>h+1:outside.append(t.get_text())
    assert not outside,outside
    for suffix in ('pdf','svg','png'):fig.savefig(out/('actual_compatible_progress.'+suffix),dpi=350)
    import fitz
    doc=fitz.open(out/'actual_compatible_progress.pdf');fonts=doc[0].get_fonts(full=True);assert not [x for x in fonts if 'Type3' in x]
    doc[0].get_pixmap(dpi=200).save(out/'actual_compatible_progress_PDF_PAGE.png');doc.close()
    caption=('Actual Consumer views for source '+summary['source_id']+' in the fixed c16-staggered repeat-0 block. '
        'Both panels have exactly the same selected Canonical F/Z/P/text history; both older complete Private views are independently proven compatible at the same trusted audio boundary F=18 s. '
        'Solid lines show actual visible audio and dashed lines the actual certified frontier. Dotted lines mark each run\'s actual Consumer application of that Canonical update. '
        'The shaded interval marks the retention-only withdrawal; the joint view remains provisional above the certified frontier. '
        'Each x-axis uses its own original session-arrival clock, without aligning or shifting Canonical update times. '
        'Source selection is maximum R1S0 withdrawal area within this fixed block among sources with a witnessed same-F compatible-ahead event in both arms; it illustrates a mechanism, not event prevalence.')
    (out/'caption.txt').write_text(caption+'\n')
    record=dict(code_commit=source['code_commit'],python=sys.version,platform=platform.platform(),new_model_calls=0,
        minimum_font_pt=min(t.get_fontsize() for t in fig.findobj(matplotlib.text.Text) if t.get_visible() and t.get_text()),
        figure_inches=[7.15,2.4],out_of_canvas_text=outside,PDF_fonts=[list(x) for x in fonts],caption=caption,
        input_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in a.data.rglob('*.json')},proofs=proofs,
        source_selection_limit='Diagnostic selection within one predeclared workload/repeat; all other outcomes retained in the 36-cell matrix.')
    (out/'PLOT_RECORD.json').write_text(json.dumps(record,indent=2)+'\n');plt.close(fig)
    print(json.dumps(dict(output=str(out),source=summary['source_id'],shared_F=summary['shared_F'],new_model_calls=0)))
if __name__=='__main__':main()
