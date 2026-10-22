from pathlib import Path
import subprocess,sys,time,json
B=Path(sys.argv[1]);P=B/'projects/revtrace_elastic_20261022';O=B/'results/revtrace/elastic_20261022'
while not (O/'STRESS_SCOUT_SUMMARY.json').exists():
 if (O/'STOP_STRESS.json').exists():raise RuntimeError('Stress scout failed')
 time.sleep(5)
for cmd in [[sys.executable,str(P/'audit_stress_records.py'),str(B),'stress_scout','9'],[sys.executable,str(P/'stress_space_gate.py'),str(B)]]:
 q=subprocess.run(cmd)
 if q.returncode:raise RuntimeError('Stress independent audit or gate failed')
