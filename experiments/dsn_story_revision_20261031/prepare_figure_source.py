"""Prepare bounded artwork source; no renderer/model/remote operation."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2];E=Path(__file__).resolve().parent
S=E/'figure_source_dev';S.mkdir();(S/'inputs').mkdir()
old=R/'experiments/dsn_writing_closure_20261031/figure_source_dev'
base=(old/'redraw_figures.py').read_text(encoding='utf8')
base=base.replace('fig.get_figheight() <= 3','fig.get_figheight() <= 3.6')
base=base.replace("'Neither', 'View only (S)', 'Compute only (R)', 'Joint (R+S)'",
    "'Recompute + snapshot', 'View only (S)', 'Compute only (R)', 'RevTrace (R+S)'")
(S/'base_renderer.py').write_bytes(base.encode())
(S/'.gitattributes').write_bytes(b'* -text\n');(S/'.gitignore').write_bytes(b'__pycache__/\n*.pyc\n')
specs=[('case_summary',R/'experiments/dsn_full_interval_case_20261029/RESULTS_v2/SUMMARY.json','CASE_SUMMARY.json'),
 ('case_trace',R/'experiments/dsn_full_interval_case_20261029/RESULTS_v2/ACTUAL_TRACE.json','CASE_TRACE.json'),
 ('case_snapshots',R/'experiments/dsn_full_interval_case_20261029/RESULTS_v2/ACTUAL_SNAPSHOTS.json','CASE_SNAPSHOTS.json'),
 ('run_endpoints_48',R/'experiments/dsn_midpoint_continuity_20261029/COMBINED_DATA_v1/RUN_ENDPOINTS.json','RUN_ENDPOINTS_48.json'),
 ('core_runs',R/'experiments/physical_retirement_20261028/H3_RESULTS_v2/aggregate/RUNS.json','CORE_RUNS_110.json'),
 ('core_tables',R/'experiments/physical_retirement_20261028/H3_RESULTS_v2/COMPACT_TABLES.json','CORE_COMPACT_TABLES.json'),
 ('native_content',R/'experiments/dsn_writing_closure_20261031/CONTENT_CPU_V4_RESULTS/complete20/SUMMARY.json','FINAL4F_CONTENT.json'),
 ('proposed_values',Path('E:/Downloads/proposed_content_chart_values.json'),'PROPOSED_CONTENT_VALUES.json')]
rows=[]
for key,p,name in specs:
 data=p.read_bytes();(S/'inputs'/name).write_bytes(data)
 rows.append(dict(key=key,copy='inputs/'+name,original=str(p.resolve()),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
protected=[]
for p in (R/'Paper_DSN/revisions/20261031_dsn2027_release_v4').rglob('*'):
 if p.is_file() and p.suffix in ['.tex','.bib','.pdf','.zip']:
  data=p.read_bytes();protected.append(dict(path=str(p.resolve()),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
(S/'SOURCE_MAP.json').write_bytes((json.dumps(dict(scope='CPU-only artwork from frozen bounded existing measurements; no NN or raw modifications',
 bounded_inputs=rows,protected_v4_files=protected,old_renderer_source_commit='60211b74f78b8420ea48f7a08746aedbbcbfb868'),indent=2)+'\n').encode())
(S/'CONFIG.json').write_bytes((json.dumps(dict(experiment_id='DSN_STORY_REVISION_FIGURES_20261031_V1',scope='Writing artwork only; no neural experiment',
 minimum_font_pt=8.5,paper_width_inches=7.125,formats=['pdf','svg','png'],new_model_calls=0,
 input_map_sha256=hashlib.sha256((S/'SOURCE_MAP.json').read_bytes()).hexdigest()),indent=2)+'\n').encode())
print(json.dumps(dict(source=str(S),input_files=len(rows),protected_v4_files=len(protected))))
