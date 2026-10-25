set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/n5_v2';O=B/'results/revtrace/dependability_20261025/n5_v2'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
sys.path.insert(0,str(P/'runtime/scripts'));from audit_dsn_journal import audit
checks=[]
for name in json.loads((O/'development/SUMMARY.json').read_text())['completed']:
 E=O/'development'/name;f=E/'canonical.wal';before=hashlib.sha256(f.read_bytes()).hexdigest();r=audit(f,E/'attempt0')
 assert hashlib.sha256(f.read_bytes()).hexdigest()==before;checks.append(dict(episode=name,audit=r))
out=O/'DEVELOPMENT_CANONICAL_WAL_REPLAY_v1.json';assert not out.exists();out.write_text(json.dumps(dict(checks=checks),indent=2)+'\n')
cmd=[sys.executable,str(P/'audit_assets_n5.py'),'--stage',str(O/'development'),'--manifest',str(P/'DEVELOPMENT_MANIFEST.json'),
 '--model',str(B/'models/Qwen3-ASR-1.7B'),'--output',str(O/'DEVELOPMENT_ASSET_REPLAY_v1.json')]
with (O/'asset_audit.log').open('xb') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 d=dict(pid=p.pid,start_ticks=(Path('/proc')/str(p.pid)/'stat').read_text().rsplit(')',1)[1].split()[19],scope='CPU only; no neural generation')
 (O/'ASSET_AUDIT_LAUNCH.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
print('PASS_WAL',len(checks))
PY
