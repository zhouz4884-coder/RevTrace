from pathlib import Path
import json,datetime
F=Path(__file__).resolve().parent
h=json.loads((F/'GPU_HANDLE_v1.json').read_text())
v=dict(experiment_id=h['experiment_id'],status='RUNNING_FROZEN_TWELVE_MIDPOINT_CELLS',
       updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),planned_cells=12,
       completed_cells=None,handle=h,plan_sha256='fb344f88774b8cdae15af213e66f296adcaf4632fa982383e730f92a18023b84',
       strong_witness='PENDING: execution completion and scientific witness are separate gates',
       stop='No10/11 search or repeat extension',source_independence='reused first12 of16 development speakers')
(F/'ACTIVE_STATE.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps({'status':v['status'],'pid':h['pid']}))
