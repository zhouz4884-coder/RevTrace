"""Run the declared 15-file runtime CPU regression, not absent legacy campaigns."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile

here=Path(__file__).resolve().parent
W=here.parent if here.name=='analysis' else here
scope=json.loads((W/'supplemental_audits/CPU_PROTOCOL_SCOPE.json' if here.name=='analysis'
                 else W/'CPU_PROTOCOL_SCOPE.json').read_text())
assert scope['status']=='PASS' and len(scope['tests'])==15
out=Path(tempfile.mkdtemp(prefix='revtrace_runtime_cpu_',dir=W))
cmd=[sys.executable,'-X','utf8','-B','-m','pytest','-q','--tb=short','-p','no:cacheprovider',
     '--basetemp',str(out/'pytest'),*['tests/'+n for n in scope['tests']]]
q=subprocess.run(cmd,cwd=W/'runtime',capture_output=True,text=True,encoding='utf-8',errors='replace',
                 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
(out/'CPU.log').write_text(q.stdout+'\n'+q.stderr)
(out/'CPU.json').write_text(json.dumps({'status':'PASS' if q.returncode==0 else 'FAIL',
 'command':cmd,'returncode':q.returncode,'scope':scope['tests'],'model_calls':0,
 'not_a_GPU_performance_result':True},indent=2)+'\n')
print(q.stdout)
print('Retained CPU record:',out)
raise SystemExit(q.returncode)
