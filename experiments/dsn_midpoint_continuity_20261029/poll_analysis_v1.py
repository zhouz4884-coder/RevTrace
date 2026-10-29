from pathlib import Path
import hashlib,json
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_midpoint_continuity_20261029';O=B/'results/revtrace/physical_retirement_20261028/dsn_midpoint_analysis_v1'
h=json.loads((P/'CPU_HANDLE_v1.json').read_text());p=Path('/proc',str(h['pid']))
live=p.exists() and (p/'stat').read_text().rsplit(')',1)[1].split()[19]==h['start_ticks'] and hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==h['command_sha256']
out=dict(exact_analysis_alive=live,pid=h['pid'])
for name in ['GATE.json','SUMMARY.json','STRONG_WITNESS_DECISION.json']:
 if (O/name).exists():out[name]=json.loads((O/name).read_text())
print(json.dumps(out))
if not live and not (O/'GATE.json').exists():
 p=Path(h['log']);n=p.stat().st_size
 with p.open('rb') as f:f.seek(max(0,n-5000));print(f.read().decode(errors='replace'))
