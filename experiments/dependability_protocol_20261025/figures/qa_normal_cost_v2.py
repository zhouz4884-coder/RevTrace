from pathlib import Path
import hashlib,json
from pypdf import PdfReader
W=Path(__file__).resolve().parent;p=W/'normal_cost_v2.pdf';r=PdfReader(p);assert len(r.pages)==1
fonts=[]
for name,ref in r.pages[0]['/Resources']['/Font'].items():
 f=ref.get_object();assert f['/Subtype']!='/Type3'
 for child in f.get('/DescendantFonts',[f]):
  d=child.get_object()['/FontDescriptor'].get_object();assert '/FontFile2' in d or '/FontFile3' in d
 fonts.append(dict(font=str(f['/BaseFont']),subtype=str(f['/Subtype']),embedded=True))
assert '<image' not in (W/'normal_cost_v2.svg').read_text()
out=dict(status='PASS_EMBEDDED_FONTS_AND_VECTOR_MARKS',fonts=fonts,PDF_pages=1,no_Type3=True,SVG_raster_images=0,
 exports={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [p,W/'normal_cost_v2.svg',W/'normal_cost_v2.png']})
(W/'NORMAL_COST_STRUCTURAL_QA_v2.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
