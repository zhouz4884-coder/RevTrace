"""Optional publication plots; render frozen curve arrays without recomputation."""
from __future__ import annotations
import pathlib

def render(bank_curves,full_curves,source_d2,repeat_d2,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    out=pathlib.Path(out);out.mkdir(exist_ok=False)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8.5,'axes.labelsize':9.,'axes.titlesize':9.5,'xtick.labelsize':8.5,'ytick.labelsize':8.5,'legend.fontsize':8.5,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','axes.linewidth':.65})
    colors={'conservative':'#747B82','fullcall':'#0072B2'};styles={'conservative':'--','fullcall':'-'};exports=[]
    def save(fig,stem):
        for ext in ('pdf','svg','png'):
            path=out/(stem+'.'+ext);fig.savefig(path,dpi=350,facecolor='white');exports.append(str(path))
        plt.close(fig)
    for stem,curves,limits in (('deadline_sensitivity',full_curves,(.5,6.)),('full_latency_CDF',full_curves,(0.,max(r['tau_d_seconds'] for r in full_curves)))):
        fig,axes=plt.subplots(1,2,figsize=(7.125,2.65),sharey=True)
        fig.subplots_adjust(left=.075,right=.985,bottom=.23,top=.78,wspace=.18)
        for i,(ax,bank) in enumerate(zip(axes,('matched','resident'))):
            for arm in ('conservative','fullcall'):
                items=sorted((r for r in curves if (r['bank'],r['arm'])==(bank,arm)),key=lambda r:r['tau_d_seconds'])
                x=[r['tau_d_seconds'] for r in items]
                ax.fill_between(x,[100*r['source_min_fraction'] for r in items],[100*r['source_max_fraction'] for r in items],step='post',color=colors[arm],alpha=.11,linewidth=0)
                ax.step(x,[100*r['duration_weighted_fraction'] for r in items],where='post',color=colors[arm],linestyle=styles[arm],linewidth=1.5)
            ax.axvline(2.,color='#A86026',linestyle=':',linewidth=1.)
            ax.text(2.04,3,'D2',color='#8C4F1F',fontsize=8.5)
            ax.set(xlim=limits,ylim=(0,100),xlabel=r'Display budget $\tau_d$ (s)',title=f'({chr(97+i)}) {bank.capitalize()}')
            ax.grid(axis='y',color='#D8DEE3',linewidth=.55);ax.set_axisbelow(True)
            ax.spines[['top','right']].set_visible(False)
            if limits[1]==6.:ax.set_xticks([.5,1,2,3,4,5,6])
        axes[0].set_ylabel('Timely audio coverage (%)')
        handles=[Line2D([0],[0],color=colors[a],linestyle=styles[a],linewidth=1.5,label=l) for a,l in (('conservative','Conservative'),('fullcall','RevTrace'))]
        fig.legend(handles=handles,loc='upper center',ncol=2,frameon=False,bbox_to_anchor=(.5,1.01))
        save(fig,stem)
    fig,axes=plt.subplots(1,2,figsize=(7.125,2.65),sharey=True)
    fig.subplots_adjust(left=.12,right=.985,bottom=.24,top=.84,wspace=.2)
    for i,(ax,bank) in enumerate(zip(axes,('matched','resident'))):
        items=sorted((r for r in source_d2 if r['bank']==bank),key=lambda r:r['source_id'])
        for y,item in enumerate(items):
            vals=[r['paired_gain_percentage_points'] for r in repeat_d2 if (r['bank'],r['source_id'])==(bank,item['source_id'])]
            ax.plot([min(vals),max(vals)],[y,y],color='#A9B8C6',linewidth=1.3,zorder=1)
            ax.scatter(vals,[y]*len(vals),s=18,facecolors='white',edgecolors='#7890A5',linewidths=.75,zorder=2)
            ax.scatter([item['paired_gain_percentage_points']],[y],s=25,color='#0072B2',marker='s',zorder=3)
        ax.axvline(0,color='#9AA3AC',linestyle=':',linewidth=.8);ax.set_yticks(range(len(items)),[r['source_id'][6:11] for r in items])
        ax.set(xlabel='Paired gain at original D2 (pp)',title=f'({chr(97+i)}) {bank.capitalize()}')
        ax.spines[['top','right']].set_visible(False);ax.grid(axis='x',color='#E2E7EC',linewidth=.55);ax.set_axisbelow(True)
    axes[0].invert_yaxis();save(fig,'source_paired_D2')
    return dict(matplotlib=matplotlib.__version__,exports=exports,width_inches=7.125,height_inches=2.65,
        minimum_font_points=8.5,step_curves=True,shading='descriptive four-source minmax, not CI',
        paired_whiskers='two timing-repeat range, not CI',actual_PDF_page_visual_QA_pending=True)

