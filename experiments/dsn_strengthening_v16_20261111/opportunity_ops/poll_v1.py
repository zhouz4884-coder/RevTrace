from pathlib import Path
import importlib.util,json,time
E=Path(__file__).resolve().parents[1];R=E.parents[1];H=E/'opportunity_ops'
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
L=json.loads((H/'PROCESS_LAUNCH_V1.json').read_bytes())
code='L='+repr(L)+'\n'+r'''
from pathlib import Path
import json
O=Path(L['raw_result_location']);p=Path('/proc/'+str(L['pid'])+'/stat');same=p.exists() and p.read_text().rsplit(')',1)[1].split()[19]==L['start_ticks']
gate=O/'GATE.json';controls=O/'CONTROLS.log'
print(json.dumps(dict(same_process_identity=same,state=p.read_text().rsplit(')',1)[1].split()[0] if same else None,
 gate=json.loads(gate.read_bytes()) if gate.exists() else None,
 completed_cell_ledgers=len(list((O/'cells').glob('*/ACTUAL_PAID_WORK.json'))) if (O/'cells').exists() else 0,
 controls_tail=controls.read_text()[-4500:] if controls.exists() else None,
 process_log_tail=Path(L['log']).read_text()[-5000:])))
'''
with m.Remote() as c:raw=c.python(code,timeout=60)
(H/('POLL_'+str(time.time_ns())+'.json')).write_bytes(raw+b'\n');print(raw.decode())
