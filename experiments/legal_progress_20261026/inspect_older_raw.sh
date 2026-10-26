set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - "$B" <<'PY'
import pathlib,json,sys
b=pathlib.Path(sys.argv[1]);root=b/'results/revtrace'
for p in sorted(root.iterdir()):
 if not p.is_dir() or not any(k in p.name for k in ['dependability','ces_v6','row_completion','online_admission']):continue
 print('ROOT',p)
 for f in sorted(p.glob('*/SUMMARY.json'))[:18]:
  try:x=json.loads(f.read_text());print(f,dict(status=x.get('status'),keys=list(x)[:8],completed_type=type(x.get('completed')).__name__,expected=x.get('expected')))
  except Exception as e:print(type(e).__name__)
 for f in sorted(p.glob('*/FREEZE.json'))[:8]:print('FREEZE',f)
 for f in sorted(p.glob('*/attempt0/config.json'))[:3]:print('DIRECT_ATTEMPT',f)
PY
