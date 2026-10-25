from pathlib import Path
import hashlib,json
from pypdf import PdfReader
W=Path(__file__).resolve().parent/'baseline';p=W/'main4.pdf';reader=PdfReader(p)
pages=[{'page':i+1,'text':page.extract_text()} for i,page in enumerate(reader.pages)]
(W/'main4_pypdf.txt').write_text('\n\n'.join(f"=== PAGE {r['page']} ===\n{r['text']}" for r in pages),encoding='utf8')
(W/'PDF_IDENTITY.json').write_text(json.dumps({'original':'E:/Downloads/main(4).pdf','bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'pages':len(pages),'metadata':dict(reader.metadata),'text_extraction':'pypdf; not a layout fidelity check'},indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print(json.dumps({'pages':len(pages),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
