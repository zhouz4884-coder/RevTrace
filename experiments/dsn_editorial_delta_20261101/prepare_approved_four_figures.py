"""Finalize the approved four-figure code and scene before its sole freeze."""
from pathlib import Path
import json,shutil,hashlib
E=Path(__file__).resolve().parent;A=E/'style_source_dev';S=E/'final_source_v1'
assert S.exists() and not (S/'.git').exists()
for n in ['.gitattributes','.gitignore','base_renderer.py','numeric_reuse.py','SOURCE_MAP.json']:shutil.copyfile(A/n,S/n)
for p in (A/'inputs').iterdir():
 if p.is_file():shutil.copyfile(p,S/'inputs'/p.name)
scene=dict(case=json.loads((A/'SCENE.json').read_bytes())['case'],mechanism=dict(size=[7.125,3.4]),core=dict(size=[7.125,2.6],margins=dict(left=.08,right=.98,bottom=.23,top=.73,wspace=.34)),native=dict(size=[3.48,2.5],margins=dict(left=.25,right=.95,bottom=.37,top=.90)))
scene['case']['legend_anchor_y']=1.018
(S/'SCENE.json').write_bytes((json.dumps(scene,indent=2)+'\n').encode())
palette=json.loads((A/'COLOUR_SCENE.json').read_bytes())['palette']
(S/'COLOUR_SCENE.json').write_bytes((json.dumps(dict(palette=palette,roles=dict(compute='owned original execution',selected='selected facts and parent evidence',view='provisional whole views and supported retention',unknown='unresolved eligibility or missed deadline marker',withdraw='withdrawal action, not invalid selected state')),indent=2)+'\n').encode())
def module(src,dest,transform=lambda x:x):
 s=(A/src).read_text(encoding='utf8').split("if __name__=='__main__':")[0]
 s=s.replace('from style_preview import load_inputs\n','').replace('HERE=Path(__file__).resolve().parent','HERE=Path(__file__).resolve().parent\nPREVIEW_MODE=True',1).replace('preview_only=True','preview_only=PREVIEW_MODE')
 (S/dest).write_bytes(transform(s).encode())
module('icon_mechanism_preview.py','draw_mechanism.py',lambda s:s.replace("p=json.loads((HERE/'COLOUR_SCENE.json').read_bytes())['palette'];W=7.125;H=3.40","p=json.loads((HERE/'COLOUR_SCENE.json').read_bytes())['palette'];W,H=json.loads((HERE/'SCENE.json').read_bytes())['mechanism']['size']"))
def time_code(s):
 s=s[:s.index('def effects(')]
 return s.replace('figsize=(7.125,3.0)','figsize=(7.125,cfg[\'height\'])').replace('bbox_to_anchor=(.57,1.018)','bbox_to_anchor=(.57,cfg[\'legend_anchor_y\'])')
module('colour_quant_preview.py','draw_time.py',time_code)
def stat_code(s):
 s=s.replace("P=json.loads((HERE/'COLOUR_SCENE.json').read_bytes())['palette']","P=json.loads((HERE/'COLOUR_SCENE.json').read_bytes())['palette']\nSCENE=json.loads((HERE/'SCENE.json').read_bytes())")
 s=s.replace('figsize=(7.125,2.60)',"figsize=tuple(SCENE['core']['size'])").replace('fig.subplots_adjust(left=.08,right=.98,bottom=.23,top=.73,wspace=.34)',"fig.subplots_adjust(**SCENE['core']['margins'])")
 s=s.replace('figsize=(3.48,2.50)',"figsize=tuple(SCENE['native']['size'])").replace('fig.subplots_adjust(left=.25,right=.95,bottom=.37,top=.90)',"fig.subplots_adjust(**SCENE['native']['margins'])")
 return s
module('academic_quant_preview.py','draw_statistics.py',stat_code)
old=S/'draw_quantitative.py'
if old.exists():old.unlink()
engine=(E/'render_final_engine.txt').read_text(encoding='utf8').replace('import draw_quantitative as dq','import draw_time as dt\nimport draw_statistics as ds').replace('b.style();dm.PREVIEW_MODE=False;dq.PREVIEW_MODE=False','b.style();dm.PREVIEW_MODE=False;dt.PREVIEW_MODE=False;ds.PREVIEW_MODE=False').replace('qa=[dq.comparison(out,j),dm.draw(out),dq.effects(out,j)]','qa=[dt.comparison(out,j),dm.draw(out),ds.core(out,j),ds.native(out,j)]').replace('figures=3','figures=4')
(S/'render.py').write_bytes(engine.encode())
cfg=dict(experiment_id='DSN_EDITORIAL_DELTA_APPROVED_FOUR_FIGURES_20261101',scope='Shape-first mechanism and standard factorial/native statistical plots; unchanged v7 evidence',paper_double_width_inches=7.125,paper_single_width_inches=3.48,min_label_pt=8.5,new_model_calls=0,actual_reader_calls=0,input_map_sha256=hashlib.sha256((S/'SOURCE_MAP.json').read_bytes()).hexdigest())
(S/'CONFIG.json').write_bytes((json.dumps(cfg,indent=2)+'\n').encode())
(S/'README.md').write_bytes(b'Approved four-figure editorial renderer. Shape-first colour mechanism, two-panel core factorial line contrasts, and separate single-column native fractions. Root complete-manifest/no-argument source gate required before formal CLI. No actual interval reader or model is included. Numeric reuse functions remain byte-derived from frozen v7 arithmetic.\n')
print(S)
