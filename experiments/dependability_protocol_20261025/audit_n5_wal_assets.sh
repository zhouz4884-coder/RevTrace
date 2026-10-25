set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/n5_v1"
O="$B/results/revtrace/dependability_20261025/n5_v1"
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,sys
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/n5_v1';O=B/'results/revtrace/dependability_20261025/n5_v1'
sys.path.insert(0,str(P/'runtime/scripts'))
from audit_dsn_journal import audit
checks=[]
for name in json.loads((O/'pilot/SUMMARY.json').read_text())['completed']:
 E=O/'pilot'/name;p=E/'canonical.wal';before=hashlib.sha256(p.read_bytes()).hexdigest()
 r=audit(p,E/'attempt0');assert hashlib.sha256(p.read_bytes()).hexdigest()==before
 checks.append(dict(episode=name,audit=r))
(O/'PILOT_CANONICAL_WAL_REPLAY_v1.json').write_text(json.dumps({'checks':checks,'scope':'read-only independent frame replay using existing admission predicate; no GPU inference'},indent=2)+'\n')
print(json.dumps({'WAL_runs':len(checks),'commits':[r['audit']['commits'] for r in checks]}))
PY
"$B/envs/revbatch-cu128/bin/python" "$P/audit_assets_n5.py" --stage "$O/pilot" --manifest "$P/DEVELOPMENT_MANIFEST.json" --model "$B/models/Qwen3-ASR-1.7B" --output "$O/PILOT_ASSET_REPLAY_v1.json"
