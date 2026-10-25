from pathlib import Path
import hashlib,json
from pypdf import PdfReader
W=Path(__file__).resolve().parent;pdf=W/'causal_protocol_v1.pdf';reader=PdfReader(pdf);assert len(reader.pages)==1
page=reader.pages[0];assert abs(float(page.mediabox.width)-7.2*72)<.01
fonts=[]
for name,ref in page['/Resources']['/Font'].items():
 f=ref.get_object();assert f['/Subtype']!='/Type3'
 for child in f.get('/DescendantFonts',[f]):
  d=child.get_object()['/FontDescriptor'].get_object();assert '/FontFile2' in d or '/FontFile3' in d
 fonts.append(dict(resource=name,font=str(f['/BaseFont']),subtype=str(f['/Subtype']),embedded=True))
assert '<image' not in (W/'causal_protocol_v1.svg').read_text()
source=json.loads((W/'CAUSAL_SOURCE_MAP_v1.json').read_text());assert not source['box_overflow'] and not source['canvas_overflow']
out=dict(status='PASS_SOURCE_BOUNDS_AND_VECTOR_STRUCTURE_PDF_VISUAL_REVIEW_PENDING',PDF_pages=1,
 fonts=fonts,no_Type3=True,SVG_raster_images=0,source_map=source,
 exports={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [pdf,W/'causal_protocol_v1.svg',W/'causal_protocol_v1.png']})
(W/'CAUSAL_STRUCTURAL_QA_v1.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(fonts=fonts,no_Type3=True)))
