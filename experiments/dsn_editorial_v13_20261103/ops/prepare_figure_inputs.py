"""Copy already frozen, bounded plotting inputs; do not read service raw logs."""
from pathlib import Path
import hashlib, json, shutil
E = Path(__file__).resolve().parents[1]
R = E.parents[1]
S = E / 'figure_source'
(S / 'inputs').mkdir(parents=True, exist_ok=True)
sources = [
 ('case.json', 'experiments/dsn_story_revision_20261031/FIGURES_v3/ACTUAL_INTERVAL_COMPARISON.json'),
 ('core.json', 'experiments/dsn_story_revision_20261031/FIGURES_v3/MAIN_EFFECT_NUMERIC_VALUES.json'),
 ('native.json', 'experiments/dsn_native_confirmation_20261102/figures/INPUTS_v11.json'),
 ('pairs.csv', 'experiments/dsn_native_confirmation_20261102/confirmation/FINAL_REPORT/SOURCE8_PAIRED.csv'),
 ('native_report.json', 'experiments/dsn_native_confirmation_20261102/confirmation/FINAL_REPORT/PAPER_DATA.json'),
]
rows=[]
for name, rel in sources:
 p=R/rel; q=S/'inputs'/name;shutil.copyfile(p,q)
 rows.append(dict(path='inputs/'+name, original=rel, bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(S/'INPUT_MAP.json').write_text(json.dumps(dict(sources=rows, new_model_calls=0, raw_service_readers=0),indent=2)+'\n',encoding='utf-8')
(S/'.gitattributes').write_text('* -text\n',encoding='utf-8')
(S/'.gitignore').write_text('__pycache__/\n',encoding='utf-8')
(S/'CONFIG.json').write_text(json.dumps(dict(experiment_id='REVTRACE_V13_FROZEN_FIGURE_RENDER_20261103',scope='Editorial vector redraw only; no endpoint changes',main_figures=4,artifact_only_figures=1,minimum_font_pt=8.0,main_width_inches=7.125,column_width_inches=3.48),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(copied_inputs=len(rows),source=str(S))))
