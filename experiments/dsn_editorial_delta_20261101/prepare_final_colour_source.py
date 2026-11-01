"""Prepare the once-approved shape-first colour renderer for formal freezing."""
from pathlib import Path
import json,shutil,hashlib
E=Path(__file__).resolve().parent;A=E/'style_source_dev';S=E/'final_source_v1'
assert not S.exists();S.mkdir();(S/'inputs').mkdir()
for n in ['.gitattributes','.gitignore','base_renderer.py','numeric_reuse.py','SOURCE_MAP.json','SCENE.json','COLOUR_SCENE.json']:shutil.copyfile(A/n,S/n)
for p in (A/'inputs').iterdir():
 if p.is_file():shutil.copyfile(p,S/'inputs'/p.name)
for src,dest in [('icon_mechanism_preview.py','draw_mechanism.py'),('colour_quant_preview.py','draw_quantitative.py')]:
 s=(A/src).read_text(encoding='utf8').split("if __name__=='__main__':")[0]
 s=s.replace('from style_preview import load_inputs\n','')
 s=s.replace('HERE=Path(__file__).resolve().parent','HERE=Path(__file__).resolve().parent\nPREVIEW_MODE=True',1)
 s=s.replace('preview_only=True','preview_only=PREVIEW_MODE')
 (S/dest).write_bytes(s.encode())
cfg=dict(experiment_id='DSN_EDITORIAL_DELTA_APPROVED_COLOUR_FIGURES_20261101',scope='Approved shape-first colour editorial renderer; unchanged v7 numerical evidence',paper_width_inches=7.125,min_label_pt=8.5,new_model_calls=0,actual_reader_calls=0,input_map_sha256=hashlib.sha256((S/'SOURCE_MAP.json').read_bytes()).hexdigest())
(S/'CONFIG.json').write_bytes((json.dumps(cfg,indent=2)+'\n').encode())
(S/'README.md').write_bytes(b'Approved shape-first editorial figures. Original numerical data are immutable. Root full-manifest/no-argument gate is required for the final CLI. No actual interval reader or model is included. Numeric reuse source is verbatim v7 arithmetic.\n')
print(S)
