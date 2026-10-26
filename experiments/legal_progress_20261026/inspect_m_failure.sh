set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - "$B" <<'PY'
import sys,pathlib,json
from transformers import AutoTokenizer,GenerationConfig
b=pathlib.Path(sys.argv[1]);m=b/'models/Qwen2.5-1.5B-Instruct';t=AutoTokenizer.from_pretrained(m,local_files_only=True)
print('generation_config',GenerationConfig.from_pretrained(m,local_files_only=True).to_dict())
s=json.loads((b/'results/revtrace/dependability_20261025/lp1_20261026/m_gpu_v1/SELF_CHECKS.json').read_text())
for r in s:
 d=[dict(i=i,generated=a,predicted=p,g=t.decode([a]),v=t.decode([p])) for i,(a,p) in enumerate(zip(r['actual']['new_tokens'],r['verify']['predicted'])) if a!=p]
 print(r['task'],d)
PY
