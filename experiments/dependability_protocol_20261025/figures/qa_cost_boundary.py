from pathlib import Path
import hashlib,json
from pypdf import PdfReader
W=Path(__file__).resolve().parent;pdf=W/'cost_boundary_v1.pdf';r=PdfReader(pdf);assert len(r.pages)==1
page=r.pages[0];assert abs(float(page.mediabox.width)-7.2*72)<.01
fonts=[]
for name,ref in page['/Resources']['/Font'].items():
 f=ref.get_object();assert str(f['/Subtype'])!='/Type3'
 descendants=f.get('/DescendantFonts',[f])
 for child in descendants:
  c=child.get_object();d=c['/FontDescriptor'].get_object();assert '/FontFile2' in d or '/FontFile3' in d
 fonts.append(dict(resource=name,base=str(f['/BaseFont']),subtype=str(f['/Subtype']),embedded=True))
assert '<image' not in (W/'cost_boundary_v1.svg').read_text()
d=json.loads((W/'FIGURE_AUDIT_v1.json').read_text());d.update(status='PASS_SOURCE_BYTES_BOUNDS_EMBEDDED_VECTOR_STRUCTURE_PDF_RENDER_REVIEW_PENDING',
 PDF_pages=1,PDF_fonts=fonts,no_Type3=True,SVG_raster_images=0,
 exports={name:hashlib.sha256((W/name).read_bytes()).hexdigest() for name in ['cost_boundary_v1.pdf','cost_boundary_v1.svg','cost_boundary_v1.png']})
(W/'FIGURE_STRUCTURAL_QA_v1.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(dict(fonts=fonts,no_Type3=True,SVG_raster_images=0)))
