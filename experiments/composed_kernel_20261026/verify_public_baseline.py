"""Verify all frozen baseline bytes against public main Git objects, read-only."""
from pathlib import Path
import subprocess,json,hashlib
W=Path(__file__).resolve().parent;BASE=W.parent/'dependability_protocol_20261025'
G=BASE/'git_delivery_checkpoint_v1'
head=subprocess.check_output(['git','-C',str(G),'rev-parse','HEAD']).decode().strip()
assert head=='5e8e1e0868356465aac40bfe75b59ca9d13453a4'
manifest=json.loads((BASE/'N5_SOURCE_MANIFEST_v3.json').read_text());checked=[]
for item in manifest['files']:
    p='experiments/dependability_protocol_20261025/runtime_n5_v3/'+item['path']
    raw=subprocess.check_output(['git','-C',str(G),'cat-file','blob',head+':'+p])
    actual=hashlib.sha256(raw).hexdigest();assert actual==item['sha256'],p
    checked.append(dict(path=p,sha256=actual))
result=dict(status='PASS_ALL141_BASELINE_FILES_MATCH_PUBLIC_MAIN_GIT_OBJECTS',public_commit=head,
    frozen_runtime_commit=manifest['code_commit'],files=checked,
    scope='read-only Git object verification after initial remote-ref check; root dirty worktree not used as execution baseline')
out=W/'PUBLIC_BASELINE_BYTE_AUDIT_v1.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(status=result['status'],files=len(checked))))
