"""Read-only bounded R7/R8 historical identity inventory; no model loading."""
from pathlib import Path
import hashlib,json,os,subprocess,platform
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
out=dict(host=platform.node(),scope='read-only historical metadata inventory; no GPU or environment mutation',roots={})
roots=[B/'projects/revtrace_r7_0849660',B/'results/revtrace/r7_efsc',B/'logs/revtrace/r7_efsc',
       B/'datasets/revtrace/librispeech',B/'models/whisper-base.en',B/'envs/streamtxn-cu128',
       B/'results/revtrace/r8_csdr',B/'logs/revtrace/r8_csdr']
for root in roots:
 r=dict(exists=root.exists(),files=[]);out['roots'][str(root)]=r
 if not root.exists():continue
 if root.name=='streamtxn-cu128':
  for p in [root/'pyvenv.cfg',root/'bin/python']:
   if p.exists():r['files'].append(dict(path=str(p),bytes=p.stat().st_size,realpath=str(p.resolve())))
  for p in root.glob('lib/python*/site-packages/*.dist-info/METADATA'):
   if any(p.parent.name.lower().startswith(n) for n in ('torch-','transformers-','numpy-','soundfile-','tokenizers-','qwen_asr-')):
    r['files'].append(dict(path=str(p),head=p.read_text(errors='replace')[:250],sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
  continue
 for folder,dirs,files in os.walk(root):
  rel=Path(folder).relative_to(root)
  dirs[:]=[d for d in dirs if d not in ['.git','__pycache__','.pytest_cache','node_modules'] and len(rel.parts)<4]
  for name in files:
   p=Path(folder)/name
   if root.name=='librispeech' and p.suffix not in ('.json','.txt','.csv'):continue
   if root.name=='revtrace_r7_0849660' and p.suffix not in ('.json','.md','.txt','.py','.sh') and name not in ('CODE_COMMIT','COMMIT','SOURCE_COMMIT'):continue
   st=p.stat();f=dict(path=str(p),bytes=st.st_size,mtime=st.st_mtime)
   if st.st_size<=32*1024*1024 and p.suffix not in ('.bin','.safetensors','.pt','.flac','.wav'):
    f['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
   r['files'].append(f)
 if (root/'.git').exists():
  q=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],capture_output=True,text=True,timeout=10)
  r['git_head']=dict(returncode=q.returncode,stdout=q.stdout,stderr=q.stderr)
out['related_project_names']=[str(p) for p in (B/'projects').iterdir() if any(x in p.name.lower() for x in ['revtrace_r7','revtrace_r8'])]
out['related_result_names']=[str(p) for p in (B/'results/revtrace').iterdir() if any(x in p.name.lower() for x in ['r7','r8'])]
print(json.dumps(out))
