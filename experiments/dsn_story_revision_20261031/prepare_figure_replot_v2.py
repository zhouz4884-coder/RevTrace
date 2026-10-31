"""Preserve the first artwork failure; prepare pure replot from its fixed data."""
from pathlib import Path
import hashlib,json,subprocess,sys
E=Path(__file__).resolve().parent;R=E.parents[1];S=E/'figure_source_dev';OUT=E/'FIGURES_v1'
sys.path.insert(0,str(S))
import render_story_figures as frozen
before=json.loads((OUT/'CONTROL_HASHES_BEFORE.json').read_bytes())
after={p:frozen.sha(p) for p in before};assert after==before
frozen.put(OUT/'CONTROL_HASHES_AFTER.json',after)
m=json.loads((S/'SOURCE_MAP.json').read_bytes())
for row in m['bounded_inputs']:assert frozen.sha(S/row['copy'])==row['sha256']==frozen.sha(row['original'])
for row in m['protected_v4_files']:assert frozen.sha(row['path'])==row['sha256']
assert frozen.gate(E/'FIGURE_SOURCE_v1.json')=='73026a11f6db202d723e6028ad85e6833888ec78'
frozen.put(OUT/'GATE.json',dict(gate='FAIL_FINAL_COMPARISON_PLOT_OUT_OF_CANVAS_TICK',
 failure='AssertionError: automatic tick4.5 outside canvas',actual_reader_completed=True,
 actual_analysis_source_commit='73026a11f6db202d723e6028ad85e6833888ec78',formal_CLI_exit=1,
 actual_comparison='ACTUAL_INTERVAL_COMPARISON.json',
 controls='10/10 RAM controls PASS before actual extraction',
 all_pinned_inputs_and_originals_after_SHA_unchanged=True,all_frozen_controls_after_SHA_unchanged=True,
 source_clean_after=True,new_model_calls=0,figure_visual_issues='Composite footer/legend overlap; final comparison automatic tick out of bounds'))
frozen.put(OUT/'OUTPUT_INDEX.json',[dict(path=p.name,bytes=p.stat().st_size,sha256=frozen.sha(p)) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='OUTPUT_INDEX.json'])
N=E/'figure_source_v2';assert not N.exists()
subprocess.run(['git','-c','core.autocrlf=false','clone','--no-hardlinks',str(S),str(N)],check=True,capture_output=True)
def git(*args):return subprocess.check_output(['git','-C',str(N),*args],text=True).strip()
git('config','core.autocrlf','false');git('config','user.name','RevTrace artifact');git('config','user.email','artifact@revtrace.invalid')
git('switch','-c','codex/dsn-story-figures-v2')
sm=json.loads((N/'SOURCE_MAP.json').read_bytes())
for key,name in [('actual_interval_comparison','ACTUAL_INTERVAL_COMPARISON.json'),('actual_interval_analysis_receipt','RUN_RECORD.json')]:
 p=OUT/name;data=p.read_bytes();dest='inputs/V1_'+name;(N/dest).write_bytes(data)
 sm['bounded_inputs'].append(dict(key=key,copy=dest,original=str(p.resolve()),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
sm['actual_interval_analysis_source_commit']='73026a11f6db202d723e6028ad85e6833888ec78'
(N/'SOURCE_MAP.json').write_bytes((json.dumps(sm,indent=2)+'\n').encode())
config=json.loads((N/'CONFIG.json').read_bytes());config.update(experiment_id='DSN_STORY_REVISION_FIGURES_20261031_V2_REPLOT',
 scope='Pure artwork rerender of frozen original datasets and already-completed73026 interval extraction; no repeat real-input reader',
 input_map_sha256=hashlib.sha256((N/'SOURCE_MAP.json').read_bytes()).hexdigest(),interval_analysis_mode='reuse_frozen73026_result')
(N/'CONFIG.json').write_bytes((json.dumps(config,indent=2)+'\n').encode())
p=N/'base_renderer.py';s=p.read_text(encoding='utf8');s=s.replace("'legend.fontsize': 8.5, 'axes.linewidth': .65,","'legend.fontsize': 8.5, 'legend.frameon': False, 'axes.linewidth': .65,")
p.write_bytes(s.encode())
p=N/'render_story_figures.py';s=p.read_text(encoding='utf8')
s=s.replace("b.txt(ax,x+.47,y+.07,'RevTrace' if row['arm']=='R1_S1' else NAMES[i].replace('\\n',' '),color=color)",
 "b.txt(ax,x+.47,y+.07,('Recompute','View only','Compute only','RevTrace')[i],color=color)")
s=s.replace(" b.txt(ax,.98,-.015,'Big number: frontier withdrawals\\nSecond line: audio meeting both deadlines',color=GRAY)",'')
s=s.replace("fig=plt.figure(figsize=(WIDTH,3.10))","fig=plt.figure(figsize=(WIDTH,3.40))")
s=s.replace("a=fig.add_axes([.025,.155,.405,.72]);c=fig.add_axes([.60,.205,.345,.65])", "a=fig.add_axes([.025,.28,.405,.59]);c=fig.add_axes([.60,.30,.345,.57])")
s=s.replace("fig.text(.235,.055,'714.110 s offered per arm; three cohorts'", "fig.text(.235,.14,'714.110 s offered per arm; three cohorts'")
s=s.replace(" fig.legend(handles,['Timely + text match'", " fig.text(.235,.205,'Big: frontier withdrawals; below: timely audio (s)',fontsize=8.5,ha='center',color=GRAY)\n fig.legend(handles,['Timely + text match'")
s=s.replace("bbox_to_anchor=(.52,-.005)","bbox_to_anchor=(.52,.005)")
s=s.replace("  ax.set(xlim=(0,end),ylim=(9.6,top+1.1),yticks=list(range(10,int(top)+1,2)));", "  ax.set(xlim=(0,end),ylim=(9.6,top+1.1),yticks=list(range(10,int(top)+1,2)),xticks=list(range(int(end)+1)));")
s=s.replace("  ax.text(.985,.09,f\"First coverage: {r['first_visible']:.3f} s; selected: {r['first_certified']:.3f} s\",", "  miss_note=f\" (D2 +{(r['first_visible']-2)*1000:.1f} ms)\" if not r['first_D2_pass'] else ''\n  ax.text(.985,.09,f\"First coverage: {r['first_visible']:.3f} s{miss_note}; selected: {r['first_certified']:.3f} s\",")
old=" comparison_inputs={arm:{name:inputs['comparison_'+arm+'_'+name] for name in ('CONSUMER','EVENTS','WORKER_RECORDS','SESSION','EPISODE','MANIFEST_ROW','PROOF')} for arm in ('R1_S0','R1_S1')}\n comparison=extract_comparison(comparison_inputs);put(out/'ACTUAL_INTERVAL_COMPARISON.json',comparison)"
new=" comparison=inputs['actual_interval_comparison'];assert comparison['status']=='PASS_ACTUAL_TWO_ARM_INTERVAL_OBSERVATIONS'\n assert inputs['actual_interval_analysis_receipt']['actual_figure_source_commit']==sm['actual_interval_analysis_source_commit']=='73026a11f6db202d723e6028ad85e6833888ec78'\n put(out/'ACTUAL_INTERVAL_COMPARISON.json',comparison)"
assert old in s;s=s.replace(old,new)
s=s.replace("  actual_figure_source_commit=commit,source_manifest_sha256=sha(a.manifest),", "  actual_figure_source_commit=commit,actual_interval_analysis_source_commit=sm['actual_interval_analysis_source_commit'],source_manifest_sha256=sha(a.manifest),")
s=s.replace("actual_figure_source_commit=commit,\n  all_original_values", "actual_figure_source_commit=commit,actual_interval_analysis_source_commit=sm['actual_interval_analysis_source_commit'],\n  all_original_values")
p.write_bytes(s.encode())
p=N/'README.md';s=p.read_text(encoding='utf8')
s+='\n## V2 pure replot\n\nThe actual two-arm interval reader completed under73026 before a final plotting\naxis tick failed export. That failed CLI/gate remains intact. This source pins\nits ACTUAL_INTERVAL_COMPARISON and original run receipt and reuses their data;\nit does not call the real-input reader again. V2 changes only layout, labels,\nlegend framing and explicit Joint D2-miss annotation. The10 RAM controls may\nrepeat as component controls. Analysis commit73026 and this plot commit remain\ndistinct.\n'
p.write_bytes(s.encode())
import ast
for p in N.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
print(json.dumps(dict(new_source=str(N),old_CLI_failure_preserved=True,actual_reader_repeated=False,
 reused_actual_comparison_sha256=hashlib.sha256((OUT/'ACTUAL_INTERVAL_COMPARISON.json').read_bytes()).hexdigest(),bounded_inputs=len(sm['bounded_inputs']))))
