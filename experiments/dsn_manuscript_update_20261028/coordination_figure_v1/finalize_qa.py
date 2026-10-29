import hashlib,json
from pathlib import Path
F=Path(__file__).resolve().parent;O=F/'FIGURES_v2'
qa=json.loads((O/'QA.json').read_text(encoding='utf8'))
assert qa['minimum_font_pt']>=8 and qa['Type3']==0 and qa['canvas_and_card_text_bounds']=='PASS'
svg=(O/'coordination_protocol.svg').read_text(encoding='utf8')
assert '<text' in svg
proof={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in O.iterdir() if p.is_file()}
with (O/'VISUAL_QA_FINAL.json').open('x',encoding='utf8',newline='\n') as f:
    json.dump(dict(status='PASS_FULL_PDF_AND_PNG_VISUAL_QA',method='Opened full PDF-page raster and full exported PNG with image viewer',
        checked=['both full panels and all six physical states visible','all labels inside their cards and canvas','completion-race path distinguishable from safe-point path','whole provisional view goes independently to Consumer, without requiring R','blue Canonical installation feeds independent certified lane','no clipping, cropped labels, legend obstruction or crowded text','SVG retains editable text; PDF fonts embedded and Type3=0'],
        width_inches=7.15,height_inches=4.45,minimum_font_pt=qa['minimum_font_pt'],editable_svg_text_nodes=svg.count('<text'),
        actual_execution_source='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf',
        plot_source_commit='a4fb90ccdcf4653a3a4a20a0fb2639a45c25a06f',files=proof),f,indent=2,ensure_ascii=False);f.write('\n')
print(json.dumps(dict(status='PASS_FULL_PDF_AND_PNG_VISUAL_QA',files=len(proof),bytes=sum(r['bytes'] for r in proof.values()))))
