from pathlib import Path
import importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];H=E/'external_rule_ops';launch=json.loads((H/'PROCESS_LAUNCH_V2.json').read_bytes())
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
with m.Remote() as c:
 script='L='+repr(launch)+'\n'+r'''
from pathlib import Path
import json,subprocess
O=Path(L['raw_result_location']);p=Path('/proc/'+str(L['pid'])+'/stat');status=dict(pid=L['pid'],same_generation=False)
if p.exists():
 a=p.read_text().rsplit(')',1)[1].split();status.update(same_generation=a[19]==L['start_ticks'],process_state=a[0])
status['files']=len(list(O.glob('*')))
for name in ('SUMMARY.json','GATE.json'):
 if (O/name).exists():status[name]=json.loads((O/name).read_bytes())
if (O/'CONTROLS.log').exists():status['controls_tail']=(O/'CONTROLS.log').read_text()[-3500:]
if Path(L['log']).exists():status['process_log_tail']=Path(L['log']).read_text()[-3500:]
print(json.dumps(status))
'''
 print(c.python(script,timeout=60).decode())
