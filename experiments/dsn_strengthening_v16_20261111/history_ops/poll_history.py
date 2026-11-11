from pathlib import Path
import importlib.util,json,time
E=Path(__file__).resolve().parents[1];R=E.parents[1];H=E/'history_ops'
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
launch=json.loads((H/'PROCESS_LAUNCH_v1.json').read_bytes())
code='L='+repr(launch)+'\n'+r'''
from pathlib import Path
import json,time
state=Path('/proc/'+str(L['pid'])+'/stat')
identity=state.exists() and state.read_text().split()[21]==L['start_ticks']
O=Path(L['raw_result_location']);gate=O/'GATE.json';control=O/'CPU_CONTROLS.json'
print(json.dumps(dict(pid=L['pid'],same_process_identity=identity,process_state=state.read_text().split()[2] if identity else None,
 completed_cell_folders=len(list((O/'cells').glob('*/SOURCE_SUMMARIES.json'))) if (O/'cells').exists() else 0,
 gate=json.loads(gate.read_bytes()) if gate.exists() else None,controls=json.loads(control.read_bytes()) if control.exists() else None,
 log_tail=Path(L['log']).read_text()[-4500:] if Path(L['log']).exists() else None)))
'''
with m.Remote() as c:raw=c.python(code,timeout=30)
(H/('POLL_'+str(time.time_ns())+'.json')).write_bytes(raw+b'\n');print(raw.decode())
