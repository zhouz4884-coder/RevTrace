"""Prepare a new editorial renderer without executing measured-data plots."""
from pathlib import Path
import hashlib,json,shutil
R=Path(__file__).resolve().parents[2];E=Path(__file__).resolve().parent
OLD=R/'experiments/dsn_story_revision_20261031';S=E/'figure_source_dev'
assert not S.exists();S.mkdir();(S/'inputs').mkdir()
shutil.copyfile(OLD/'figure_source_v3/base_renderer.py',S/'base_renderer.py')
oldmap=json.loads((OLD/'figure_source_v3/SOURCE_MAP.json').read_bytes())
keys={'core_runs','core_tables','native_content','proposed_values','actual_interval_comparison'}
rows=[]
def add(key,p,name):
 data=p.read_bytes();dest=S/'inputs'/name;dest.write_bytes(data)
 rows.append(dict(key=key,copy='inputs/'+name,original=str(p.resolve()),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
for row in oldmap['bounded_inputs']:
 if row['key'] in keys:add(row['key'],Path(row['original']),Path(row['copy']).name)
add('original_numeric_values',OLD/'FIGURES_v3/MAIN_EFFECT_NUMERIC_VALUES.json','V7_NUMERIC_VALUES.json')
assert len(rows)==6
base=R/'Paper_DSN/revisions/20261031_dsn2027_release_v7'
paths=[base/r['target'] for r in json.loads((base/'PACKAGING_PROVENANCE.json').read_bytes())['files']]
paths += [base/'main.pdf',base/'RevTrace_DSN2027_anonymous_source_v7.zip']
paths += [p for p in (OLD/'FIGURES_v3').iterdir() if p.is_file()]
protected=[dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths]
sm=dict(scope='Editorial artwork only; frozen actual interval analysis is reused, no raw reader or neural call',
 actual_interval_analysis_commit='73026a11f6db202d723e6028ad85e6833888ec78',bounded_inputs=rows,protected=protected,
 dependencies=[dict(path='base_renderer.py',original=str((OLD/'figure_source_v3/base_renderer.py').resolve()),sha256=hashlib.sha256((S/'base_renderer.py').read_bytes()).hexdigest())])
(S/'SOURCE_MAP.json').write_bytes((json.dumps(sm,indent=2)+'\n').encode())
cfg=dict(experiment_id='DSN_EDITORIAL_DELTA_FIGURES_20261101',scope='Three editorial figure refinements; no new actual-data extraction',new_model_calls=0,actual_reader_calls=0,
 paper_width_inches=7.125,minimum_font_pt=8.5,input_map_sha256=hashlib.sha256((S/'SOURCE_MAP.json').read_bytes()).hexdigest())
(S/'CONFIG.json').write_bytes((json.dumps(cfg,indent=2)+'\n').encode())
(S/'.gitattributes').write_bytes(b'* -text\n');(S/'.gitignore').write_bytes(b'__pycache__/\n*.pyc\n')
(S/'README.md').write_bytes(b'Editorial-only renderer. Freeze source, manifest, config and environment; require root no-argument source receipt before formal plots. No actual interval reader is included.\n')
old=(OLD/'figure_source_v3/render_story_figures.py').read_text(encoding='utf8')
functions=old[old.index('def core_rows'):old.index('def matrix')]
(S/'numeric_reuse.py').write_bytes(('"""Verbatim frozen v7 presentation arithmetic; no new measurement."""\nARMS=(\'R0_S0\',\'R0_S1\',\'R1_S0\',\'R1_S1\')\n'+functions).encode())
print(json.dumps(dict(source=str(S),inputs=len(rows),protected=len(protected))))
