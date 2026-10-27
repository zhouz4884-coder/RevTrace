"""Read installed text-model config and file sizes; no model import or GPU call."""
from pathlib import Path
import importlib.util,shlex,json
spec=importlib.util.spec_from_file_location('authorized_ssh',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
script="""from pathlib import Path
import json,hashlib
base=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/models')
rows=[]
for d in sorted(base.iterdir()):
 if not d.is_dir() or not (d/'config.json').is_file():continue
 cfg=json.loads((d/'config.json').read_text());g=d/'generation_config.json'
 weights=[p for p in d.glob('*.safetensors') if p.is_file()]
 rows.append(dict(path=str(d),config_sha256=hashlib.sha256((d/'config.json').read_bytes()).hexdigest(),
  architectures=cfg.get('architectures'),model_type=cfg.get('model_type'),dtype=cfg.get('dtype',cfg.get('torch_dtype')),
  hidden_size=cfg.get('hidden_size'),layers=cfg.get('num_hidden_layers'),
  weight_bytes=sum(p.stat().st_size for p in weights),weight_shards=len(weights),
  generation=json.loads(g.read_text()) if g.is_file() else None))
print(json.dumps(rows,indent=2))
"""
c=helper.ssh_client()
try:
 _,o,e=c.exec_command(B+'/envs/revbatch-cu128/bin/python -c '+shlex.quote(script),timeout=40)
 rows=json.loads(o.read().decode());assert not e.read()
 p=Path(__file__).parent/'INSTALLED_MODEL_METADATA.json';assert not p.exists();p.write_text(json.dumps(rows,indent=2)+'\n')
 print(json.dumps(rows,indent=2))
finally:c.close()
