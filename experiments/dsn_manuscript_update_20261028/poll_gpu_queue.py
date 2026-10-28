"""Small metadata-only progress poll; a read timeout never implies worker death."""
import hashlib,json
from pathlib import Path
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_dsn_service_stability_20261028';O=B/'results/revtrace/physical_retirement_20261028'
def live(h):
 p=Path('/proc',str(h['pid']))
 try:
  return (p/'stat').read_text().rsplit(')',1)[1].split()[19]==h['start_ticks'] and hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==h['command_sha256']
 except FileNotFoundError:return False
h=json.loads((P/'GPU_HANDLE_v1.json').read_text())
result=dict(exact_controller_live=live(h),pid=h['pid'])
D=O/'dsn_service_stability_controller_v1'
for n in ['PROGRESS.json','GATE.json','STOP.json']:
 if (D/n).exists():result[n]=json.loads((D/n).read_text())
print(json.dumps(result))
