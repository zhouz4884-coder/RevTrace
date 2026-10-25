"""Wait for this existing bounded GPU controller, then CPU-only audit/collect."""
from pathlib import Path
import json,os,subprocess,sys,time
B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/ces_v5_20261025'
assert not (O/'POST_CONTROLLER_PID.json').exists()
(O/'POST_CONTROLLER_PID.json').write_text(json.dumps({'pid':os.getpid(),'GPU_calls':0,'scope':'wait for existing controller then CPU only'})+'\n')
started=time.monotonic()
while not (O/'SUMMARY.json').exists():
 if (O/'STOP.json').exists():
  (O/'POST_WAIT_STOP.json').write_text(json.dumps({'reason':'GPU controller stopped; no new GPU launched','GPU_calls':0})+'\n');raise SystemExit(1)
 if time.monotonic()-started>6*3600:raise TimeoutError('Existing GPU controller not complete')
 time.sleep(15)
for script in ['post_cpu.py','collect_bounded.py']:
 p=subprocess.run([sys.executable,'-u',str(P/script),str(B)],cwd=P,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
 if p.returncode:
  (O/'POST_STAGE_STOP.json').write_text(json.dumps({'script':script,'returncode':p.returncode,'GPU_calls':0})+'\n');raise SystemExit(p.returncode)
