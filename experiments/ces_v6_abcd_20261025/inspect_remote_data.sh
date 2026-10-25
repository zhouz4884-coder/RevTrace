set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,os
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');R=B/'datasets/revtrace'
out={}
for name in ['librispeech','librispeech_dev','librispeech_hf','librispeech_r9_final2']:
 d=R/name;rows=[]
 if d.exists():
  for base,dirs,files in os.walk(d):
   depth=len(Path(base).relative_to(d).parts)
   rows.append({'path':str(Path(base).relative_to(d)),'dirs':dirs[:6],'files':files[:5]})
   if depth>=3:dirs[:]=[]
   if len(rows)>=16:break
 out[name]=rows
print(json.dumps(out))
PY
