"""Post-hoc explanatory single-arm case; original36/48 denominators unchanged."""
from pathlib import Path
import argparse,hashlib,json,platform,subprocess,sys
from interaction_opportunities_v1 import complete_chain

def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def put(p,v):
    with Path(p).open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def lcp(a,b):
    n=0
    for x,y in zip(a,b):
        if x!=y:break
        n+=1
    return n
def delta(a,b):
    n=lcp(a,b)
    return dict(LCP_code_points=n,introduced_raw_code_points=len(b)-n,erased_raw_code_points=len(a)-n,
        introduced_nonwhitespace_code_points=sum(not x.isspace() for x in b[n:]),introduced_suffix=b[n:])
def source_gate(m):
    root=Path(__file__).resolve().parent;git=lambda *a:subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
    assert Path(git('rev-parse','--show-toplevel')).resolve()==root
    assert git('rev-parse','HEAD')==m['code_commit'] and not git('status','--porcelain','--untracked-files=all')
    assert set(git('ls-files').splitlines())=={r['path'] for r in m['files']}
    for r in m['files']:assert (root/r['path']).stat().st_size==r['bytes'] and sha((root/r['path']).read_bytes())==r['sha256']
def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    cfg=load(a.config);m=load(a.source_manifest);source_gate(m);out=a.out;out.mkdir(exist_ok=False,parents=True)
    put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',dict(python=sys.version,platform=platform.platform(),new_model_calls=0))
    put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=m['code_commit'],frozen_config=str(a.config.resolve()),frozen_config_sha256=sha(a.config.read_bytes()),environment_sha256=sha((out/'ENVIRONMENT.json').read_bytes()),raw_result_location=[r['path'] for r in cfg['inputs'].values()],aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    data={}
    for name,r in cfg['inputs'].items():
        path=Path(r['path']);b=path.read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256'];data[name]=json.loads(b)
    rows=data['consumer'];events=data['events'];records={r['job']['job_id']:r for r in data['workers']};session=data['session'];episode=data['episode'];F=cfg['offered_F'];rootF=cfg['canonical_F']
    sid=cfg['session_id'];assert session['source_id']==cfg['source_id'] and F<round(session['duration']*16000)
    witness=next(r for r in data['timely_windows'] if r['cell_id']==cfg['cell_id'] and r['session_id']==sid and r['frontier']==F and r['version']==cfg['version'])
    assert witness['audio_seconds']==2.0 and witness['classification']=='compatible' and witness['original_D2_read_in_deficit']
    first=next(i for i,r in enumerate(rows) if r['valid_visible_frontier']>=F)
    loss=next(i for i,r in enumerate(rows) if i>first and r['source_kind']=='canonical-display' and r['canonical_version']==cfg['version'])
    recovery=next(i for i,r in enumerate(rows) if i>loss and r['valid_visible_frontier']>=F)
    assert rows[first]['valid_visible_frontier']==F and rows[loss]['valid_visible_frontier']==rootF
    source_origin=episode['origin_perf']+session['offset'];ready=source_origin+F/16000
    assert abs(rows[first]['observed_perf']-witness['first_visible_perf'])<1e-6
    assert abs(rows[loss]['observed_perf']-witness['start_perf'])<1e-6
    assert abs(rows[recovery]['observed_perf']-witness['recovery_perf'])<1e-6
    e=next(e for e in events if e['kind']=='display' and e['displayed']==rows[first]['server_time'])
    assert e['text']==rows[first]['visible_text'] and e['audio_end_sample']==F
    private=records[e['job_id']]
    commit=next(e for e in events if e['kind']=='commit' and e['version']==cfg['version'])
    assert commit['audio_end_sample']==rootF
    authority=records[commit['job_id']]
    assert authority['result']['token_ids']==commit['segment_tokens'] and authority['result']['state_tokens']==commit['next_prompt_tokens']
    owner=next(e['t0_perf'] for e in events if e['kind']=='run-start')
    published={e['job_id'] for e in events if e['kind']=='display' and owner+e['displayed']<=rows[loss]['observed_perf']}
    compatible,reason,chain=complete_chain(private['job']['job_id'],rootF,commit['next_prompt_tokens'],records,published,32000)
    assert compatible is True
    actual_prompt=private['result']['execution_context_audit']['executed_prompt_tokens']
    assert actual_prompt==private['job']['prompt_tokens']==commit['next_prompt_tokens']
    first_delta=delta(rows[first-1]['visible_text'],rows[first]['visible_text']);assert first_delta['introduced_nonwhitespace_code_points']>0
    loss_delta=delta(rows[loss-1]['visible_text'],rows[loss]['visible_text']);recovery_delta=delta(rows[recovery-1]['visible_text'],rows[recovery]['visible_text'])
    assert rows[first]['visible_text']==rows[recovery]['visible_text']
    result=dict(status='PASS_ACTUAL_NON_EOS_TIMELY_CONTENT_CASE',case_selection='Attachment-motivated post-hoc explanatory case, not prevalence or a paired counterfactual',
        cell_id=cfg['cell_id'],source_id=cfg['source_id'],session_id=sid,offered_F=F,offered_interval_audio_seconds=2.0,canonical_F=rootF,
        D=rows[first]['observed_perf']-ready,loss_start=rows[loss]['observed_perf']-ready,C=rows[recovery]['observed_perf']-ready,
        loss_duration=rows[recovery]['observed_perf']-rows[loss]['observed_perf'],original_D2_read_in_deficit=True,
        first_text_delta=first_delta,withdrawal_text_delta=loss_delta,recovery_text_delta=recovery_delta,
        first_and_recovered_complete_text_equal=True,compatible=compatible,compatibility_reason=reason,chain=chain,
        private_job=private['job']['job_id'],selected_root_job=commit['job_id'],actual_input_prompt_equals_selected_root_P=True,
        selected_root_P_sha256=sha(json.dumps(commit['next_prompt_tokens'],sort_keys=True,separators=(',',':')).encode()),new_model_calls=0)
    put(out/'SUMMARY.json',result)
    snapshots=[dict(name=name,relative_to_offered_F_seconds=rows[i]['observed_perf']-ready,**rows[i]) for name,i in [('before_first',first-1),('first',first),('withdrawal',loss),('recovery',recovery)]]
    put(out/'ACTUAL_SNAPSHOTS.json',snapshots)
    trace=[dict(t=r['observed_perf']-ready,visible_F=r['valid_visible_frontier']/16000,certified_F=r['certified_frontier']/16000,kind=r['source_kind']) for r in rows]
    put(out/'ACTUAL_TRACE.json',trace)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({'font.family':['Arial','DejaVu Sans','sans-serif'],'font.size':8.5,'axes.labelsize':8.5,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,'pdf.fonttype':42,'svg.fonttype':'none'})
    fig,ax=plt.subplots(figsize=(7.15,2.65));fig.subplots_adjust(left=.09,right=.99,bottom=.21,top=.82)
    x=[r['t'] for r in trace];ax.step(x,[r['visible_F'] for r in trace],where='post',color='#B64342',lw=1.5,label='Actual visible frontier')
    ax.step(x,[r['certified_F'] for r in trace],where='post',color='#4D4D4D',ls=(0,(4,2)),lw=1.2,label='Actual certified frontier')
    D,L,C=result['D'],result['loss_start'],result['C'];ax.fill_between([L,C],[12,12],[14,14],color='#B64342',alpha=.12)
    ax.axvline(2.,color='#272727',ls=(0,(2,2)),lw=.8)
    ax.plot(D,14,'o',color='#B64342',ms=3);ax.plot(L,12,'o',color='#272727',ms=3);ax.plot(C,14,'o',color='#4D4D4D',ms=3)
    ax.annotate('First view: D=1.444 s\n+37 raw code points',xy=(D,14),xytext=(.25,14.4),fontsize=8,arrowprops=dict(arrowstyle='->',lw=.6))
    ax.annotate('Compatible root advance\n1.544 s: content withdrawn',xy=(L,12),xytext=(.75,10.4),fontsize=8,arrowprops=dict(arrowstyle='->',lw=.6))
    ax.text(2.08,13.15,'Read at D2:\npreviously shown\n2-s interval missing',fontsize=8,va='center')
    ax.annotate('Exact text returns\nC=3.720 s',xy=(C,14),xytext=(3.22,14.4),fontsize=8,arrowprops=dict(arrowstyle='->',lw=.6))
    ax.set(xlim=(0,4.35),ylim=(9.5,15.05),xticks=[0,1,2,3,4],yticks=[10,12,14],xlabel='Seconds from original offered F=14 s (actual clock)',ylabel='Audio frontier (s)')
    ax.grid(axis='y',alpha=.15,lw=.5);fig.legend(*ax.get_legend_handles_labels(),loc='upper center',ncol=2,frameon=False,bbox_to_anchor=(.55,.99))
    fig.canvas.draw();renderer=fig.canvas.get_renderer();w,h=fig.get_size_inches()*fig.dpi;outside=[]
    for text in fig.findobj(matplotlib.text.Text):
        if not text.get_visible() or not text.get_text():continue
        b=text.get_window_extent(renderer)
        if b.x0< -1 or b.y0< -1 or b.x1>w+1 or b.y1>h+1:outside.append(text.get_text())
    assert not outside,outside
    for suffix in ('pdf','svg','png'):fig.savefig(out/('timely_full_interval_case.'+suffix),dpi=350)
    import fitz
    doc=fitz.open(out/'timely_full_interval_case.pdf');fonts=doc[0].get_fonts(full=True);assert not [x for x in fonts if 'Type3' in x]
    doc[0].get_pixmap(dpi=200).save(out/'timely_full_interval_case_PDF_PAGE.png');doc.close()
    caption=('A post-hoc single-arm case from c16-staggered repeat 0, source '+cfg['source_id']+'. The complete non-EOS offered interval ends at F=14 s. '
        'The first whole view introduces 37 raw code points (31 non-whitespace), replacing one prior punctuation mark. A later trusted F=12 s update withdraws that compatible whole view before the original D2 read point. '
        'At C=3.720 s the exact earlier whole text returns in the certified view. First-observation D2/C8 credit remains unchanged. '
        'The dependency witness uses actual consumed input and selected P, not text equality alone. No Joint counterfactual is drawn; it had no ahead view at the same root. '
        'This case does not change the original36/48 denominators or the negative midpoint decision and does not imply character/audio alignment or early semantic certification.')
    (out/'caption.txt').write_text(caption+'\n',encoding='utf8')
    put(out/'PLOT_MANIFEST.json',dict(code_commit=m['code_commit'],input_files=cfg['inputs'],new_model_calls=0,minimum_font_pt=min(t.get_fontsize() for t in fig.findobj(matplotlib.text.Text) if t.get_visible() and t.get_text()),figure_inches=[7.15,2.65],out_of_canvas_text=outside,Type3_fonts=0,caption=caption))
    source_gate(m);put(out/'GATE.json',dict(gate='PASS_ACTUAL_FULL2S_NON_EOS_CONTENT_AND_PLOT',new_model_calls=0));plt.close(fig)
    print(json.dumps(result))
if __name__=='__main__':main()
