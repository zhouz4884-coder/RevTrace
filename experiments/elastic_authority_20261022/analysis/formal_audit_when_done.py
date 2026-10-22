from pathlib import Path
import subprocess,sys,time
B=Path(sys.argv[1]);P=B/'projects/revtrace_elastic_20261022';O=B/'results/revtrace/elastic_20261022'
while not (O/'FORMAL_SUMMARY.json').exists():
 if (O/'STOP_FORMAL.json').exists():raise RuntimeError('Formal failure, no PASS')
 time.sleep(5)
subprocess.run([sys.executable,str(P/'audit_formal_records.py'),str(B),'formal','24'],check=True)
