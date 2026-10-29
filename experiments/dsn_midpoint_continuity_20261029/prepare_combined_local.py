"""Freeze four-point figure preparation before reading any midpoint outcome."""
from pathlib import Path
import hashlib,json,subprocess
H=Path(__file__).resolve().parent;R=H.parents[1];OLD=R/'experiments/dsn_service_stability_20261028';S=H/'combined_source_v1';S.mkdir(exist_ok=False)
text=(OLD/'figure_data_source_v4/summarize_results.py').read_text(encoding='utf8')
text=text.replace("p.add_argument('--plan',type=Path,required=True);p.add_argument('--analysis-root',type=Path,required=True)","p.add_argument('--old-plan',type=Path,required=True);p.add_argument('--new-plan',type=Path,required=True);p.add_argument('--old-root',type=Path,required=True);p.add_argument('--new-root',type=Path,required=True);p.add_argument('--old-secondary',type=Path,required=True)")
start=text.index("    plan=read(a.plan);n=len(plan['cells']);root=a.analysis_root")
end=text.index("    all_updates=defaultdict(list)",start)
replacement='''    oldplan=read(a.old_plan);newplan=read(a.new_plan)
    assert len(oldplan['cells'])==36 and len(newplan['cells'])==12
    assert oldplan['code_commit']==newplan['code_commit']=='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf'
    old=a.old_root;new=a.new_root/'core'
    assert read(old/'aggregate/SUMMARY.json')['accepted_cells']==36
    assert read(a.new_root/'GATE.json')['gate']=='PASS_ALL_12_MIDPOINT_RECOUNTS'
    assert read(new/'aggregate/SUMMARY.json')['accepted_cells']==12
    assert read(a.old_secondary/'GATE.json')['gate']=='PASS_ALL_36_READ_ONLY_CONTINUITY_RECOUNT'
    pointmap={x['point']:x for x in oldplan['points']+newplan['points']}
    plan=dict(cells=oldplan['cells']+newplan['cells'],points=[pointmap[k] for k in ('c8-sync','c8-staggered','c12-staggered','c16-staggered')])
    n=len(plan['cells']);assert n==48
    def joined(name):return read(old/name)+read(new/name)
    planned={c['cell_id']:c for c in plan['cells']};assert len(planned)==48
    runs={r['cell_id']:r for r in joined('aggregate/RUNS.json')};assert set(runs)==set(planned)
    opportunities=joined('opportunities/UPDATES.json');sources=joined('aggregate/SOURCE_METRICS.json')
    useful={r['cell_id']:r for r in joined('usefulness/RUNS.json')};assert set(useful)==set(planned)
    critical={r['cell_id']:r for r in joined('critical_path/RUNS.json')};assert set(critical)==set(planned)
    secondary={r['cell_id']:r for r in read(a.old_secondary/'RUNS.json')+read(a.new_root/'RUNS.json')};assert set(secondary)==set(planned)
    strong_decision=read(a.new_root/'STRONG_WITNESS_DECISION.json')
'''
text=text[:start]+replacement+text[end:]
text=text.replace("r=runs[cid];u=useful[cid];cr=critical[cid];assert cr['accepted']", "r=runs[cid];u=useful[cid];cr=critical[cid];ss=secondary[cid];assert cr['accepted']\n        assert abs(ss['original_dual_credited_audio_seconds']-r['dual_credited_audio_seconds'])<1e-6")
text=text.replace("whole_run_dual_P99_pass=r['whole_run_dual_P99_pass'],", "whole_run_dual_P99_pass=r['whole_run_dual_P99_pass'],\n            compatible_timely_deficit_area=ss['compatible']['timely_deficit_area'],\n            compatible_timely_loss_windows=ss['compatible']['timely_interval_loss_windows'],\n            compatible_unique_timely_withdrawn_audio_seconds=ss['compatible']['unique_timely_withdrawn_audio_seconds'],\n            compatible_D2_read_deficit_audio_seconds=ss['compatible']['original_D2_read_in_deficit_audio_seconds'],\n            incompatible_timely_deficit_area=ss['incompatible']['timely_deficit_area'],\n            UNKNOWN_timely_deficit_area=ss['UNKNOWN']['timely_deficit_area'],")
text=text.replace("'physical_lease_seconds','original_episode_wall_seconds')", "'physical_lease_seconds','original_episode_wall_seconds','compatible_timely_deficit_area',\n    'compatible_timely_loss_windows','compatible_unique_timely_withdrawn_audio_seconds',\n    'compatible_D2_read_deficit_audio_seconds','incompatible_timely_deficit_area','UNKNOWN_timely_deficit_area')")
text=text.replace("    put(out,'FIGURE_CONTRACT',", "    put(out,'FROZEN_MIDPOINT_STRONG_WITNESS',strong_decision)\n    put(out,'FIGURE_CONTRACT',")
text=text.replace("'Keep C8 endpoint separate and show every run, even though D2 may dominate.'", "'Retain original36 plus fixed midpoint12; the new point is exploratory, not a source-independent confirmation.',\n            'Single-root timely deficit area is secondary and right-censored at the next Canonical root when no earlier covering view returns; it never replaces original first credit.',\n            'Keep C8 endpoint separate and show every run, even though D2 may dominate.'")
text=text.replace("dict(panel='D',data='RUN_ENDPOINTS',x='point',y='audio_rollback_seconds'", "dict(panel='D',data='RUN_ENDPOINTS',x='point',y='compatible_timely_deficit_area'")
text=text.replace('from accepted offline recounters.', 'from accepted original36 and fixed midpoint12 offline recounters.')
(S/'summarize_48.py').write_text(text,encoding='utf8',newline='\n')
plot=(OLD/'figure_data_source_v4/plot_service_region.py').read_text(encoding='utf8')
plot=plot.replace("POINTS=('c8-sync','c8-staggered','c16-staggered')", "POINTS=('c8-sync','c8-staggered','c12-staggered','c16-staggered')")
plot=plot.replace("XTICKS=('8 / sync','8 / stag.','16 / stag.')", "XTICKS=('8/sync','8/stg','12/stg','16/stg')")
plot=plot.replace("ax.set_xticks(range(3),XTICKS)","ax.set_xticks(range(len(POINTS)),XTICKS)")
plot=plot.replace("ax.set_xlim(-.5,2.5)","ax.set_xlim(-.5,len(POINTS)-.5)")
plot=plot.replace("Sessions / arrival phase", "Sessions / arrival")
plot=plot.replace("len(rows)==36 and len(opps)==72", "len(rows)==48 and len(opps)==96")
plot=plot.replace("actual_cells=36", "actual_cells=48")
plot=plot.replace("same 36 runs", "same 48 runs")
plot=plot.replace("a. First actual visibility", "a. First actual visibility")
plot=plot.replace("base_axis(ax,'c. Visible withdrawal','Retracted audio (s)');dots(ax,rows,'audio_rollback_seconds')", "base_axis(ax,'c. Timely legal progress','Compatible deficit\\n(audio s × wall s)');dots(ax,rows,'compatible_timely_deficit_area')")
plot=plot.replace("yy=values(rows,'audio_rollback_seconds')", "yy=values(rows,'compatible_timely_deficit_area')")
plot=plot.replace("Withdrawal includes necessary incompatible revisions.", "Panel c is a secondary measure of later loss of previously dual-timely delivered intervals whose complete prior view is compatible with the new selected root; necessary incompatible revisions remain separate. Single-root windows are right-censored at the next Canonical root when no earlier covering view returns; original first credit is unchanged.")
plot=plot.replace("staggered by 0.25 s per session (stag.)", "staggered by 0.25 s per session (stg)")
plot=plot.replace("Service operating points on the reused development corpus.", "Four explicit development workloads: original36 plus a fixed exploratory midpoint12, not new independent source audio.")
(S/'plot_48.py').write_text(plot,encoding='utf8',newline='\n')
(S/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf8')
(S/'PROTOCOL.md').write_text('Read-only join of original36 and unique frozen midpoint12, retaining four workload points and all three repeats per arm. No raw inference or new metric definition: original primary endpoints, same-F retrospective support, exact compatibility incidence, and already-frozen secondary single-root timely deficit are distinct. Preserve negative points and the unchanged frozen strong-witness STOP decision. Point order c8sync,c8stagger,c12stagger,c16stagger is presentation only; no pure capacity or source-independence claim.\n',encoding='utf8')
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
subprocess.run(['git','-C',str(S),'init'],check=True,capture_output=True);git('config','core.autocrlf','false');git('checkout','-b','codex/midpoint-four-point-report-v1');git('add','.');git('commit','-m','Freeze all-four-workload 48-run report and figures before midpoint results')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=dict(code_commit=git('rev-parse','HEAD'),scope='CPU-only four-point report; existing neural and frozen continuity definitions unchanged',files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in git('ls-files').splitlines()])
with (H/'COMBINED_SOURCE_v1.json').open('x',encoding='utf8') as f:json.dump(m,f,indent=2);f.write('\n')
git('bundle','create',str(H/'COMBINED_SOURCE_v1.bundle'),'HEAD')
assert not git('status','--porcelain','--untracked-files=all');print(json.dumps(dict(commit=m['code_commit'],manifest_sha256=sha(H/'COMBINED_SOURCE_v1.json'),files=len(m['files']),new_GPU_calls=0)))
