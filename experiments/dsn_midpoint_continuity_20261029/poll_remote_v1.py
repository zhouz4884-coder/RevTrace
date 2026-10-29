"""Small exact-process and terminal metadata only; safe during timed cells."""
from pathlib import Path
import json,hashlib,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_dsn_midpoint_continuity_20261029';O=B/'results/revtrace/physical_retirement_20261028'
h=json.loads((P/'GPU_HANDLE_v1.json').read_text());p=Path('/proc',str(h['pid']))
live=p.exists()
if live:
    live=(p/'stat').read_text().rsplit(')',1)[1].split()[19]==h['start_ticks'] and hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==h['command_sha256']
out=Path(h['result']);report=dict(exact_controller_alive=live,pid=h['pid'])
for name in ['PROGRESS.json','GATE.json']:
    q=out/name
    if q.exists():
        v=json.loads(q.read_text())
        if name=='PROGRESS.json':
            n=v.get('completed',0);report['completed']=n if isinstance(n,int) else len(n)
            report['remaining']=v.get('remaining');report['current']=v.get('current')
        else:report['gate']=v
report['GPU_apps']=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader'],text=True).strip()
print(json.dumps(report))
