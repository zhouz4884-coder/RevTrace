"""Launch the single frozen midpoint scope after exact prerequisite checks."""
from pathlib import Path
import json,hashlib,subprocess,sys
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_dsn_midpoint_continuity_20261029'
a=json.loads((P/'ALLOCATION_v1.json').read_text())
r=a['additional_finished_quality_scope'];q=Path(r['path'])
assert hashlib.sha256(q.read_bytes()).hexdigest()==r['sha256']
assert json.loads(q.read_text())['gate']==r['gate']
subprocess.run([sys.executable,'-B',str(P/'analysis_source_v1/launch_midpoint.py'),'--allocation',str(P/'ALLOCATION_v1.json')],check=True)
