"""Read only expected HF cache/model metadata; never enumerate token content."""
import pathlib,json,os,sys,urllib.request,urllib.error
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
from huggingface_hub import constants,get_token
cache_roots=[pathlib.Path(constants.HF_HUB_CACHE),B/'cache/huggingface/hub',B/'caches/huggingface/hub',B/'hf_cache/hub',B/'models']
rows=[]
for root in cache_roots:
 if not root.exists():continue
 matches=[str(p) for p in root.iterdir() if 'Llama-3.2' in p.name or 'ultravox' in p.name.lower()]
 rows.append(dict(root=str(root),exact_backbone_candidates=matches))
token=get_token();status=None
if token:
 try:
  req=urllib.request.Request('https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct/resolve/main/config.json',headers={'Authorization':'Bearer '+token})
  with urllib.request.urlopen(req,timeout=20) as r:r.read(100001);status=r.status
 except urllib.error.HTTPError as e:status=e.code
 except Exception as e:status=type(e).__name__
token=None
print(json.dumps(dict(cache_inventory=rows,existing_hf_login=bool(status is not None),original_backbone_config_access=status,gpu_launched=False),indent=2))
