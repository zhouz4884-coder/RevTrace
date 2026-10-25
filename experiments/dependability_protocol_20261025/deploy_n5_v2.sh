set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,shutil
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_dependability_20261025/n5_v2';O=B/'results/revtrace/dependability_20261025/n5_v2'
P.mkdir(exist_ok=False);O.mkdir(exist_ok=False)
shutil.copyfile(B/'projects/revtrace_dependability_20261025/n5_v1/DEVELOPMENT_MANIFEST.json',P/'DEVELOPMENT_MANIFEST.json')
print(json.dumps({'project':str(P),'result':str(O)}))
PY
