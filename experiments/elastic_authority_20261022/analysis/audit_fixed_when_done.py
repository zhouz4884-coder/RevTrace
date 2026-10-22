"""CPU-only postflight, waits for the already running scout, never launches GPU."""
from pathlib import Path
import json,subprocess,sys,time
B=Path(sys.argv[1]);P=B/'projects/revtrace_elastic_20261022';O=B/'results/revtrace/elastic_20261022'
while not (O/'FIXED_SCOUT_SUMMARY.json').exists():
 if (O/'STOP_FIXED.json').exists():raise RuntimeError('Scouts failed; no audit PASS')
 time.sleep(5)
r=subprocess.run([sys.executable,str(P/'audit_records.py'),str(B),'fixed_scout','9'])
if r.returncode:(O/'STOP_AUDIT_FIXED.json').write_text(json.dumps({'exit_code':r.returncode}));raise RuntimeError('Independent scout audit failed')
print('COMPLETE_INDEPENDENT_FIXED_SCOUT_AUDIT',flush=True)
