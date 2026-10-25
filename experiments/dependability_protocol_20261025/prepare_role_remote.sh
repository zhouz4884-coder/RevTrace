set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
P=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dependability_20261025/role_probe_v1')
P.mkdir(exist_ok=False)
print('PREPARED_SOURCE_ONLY_NO_GPU',P)
PY
