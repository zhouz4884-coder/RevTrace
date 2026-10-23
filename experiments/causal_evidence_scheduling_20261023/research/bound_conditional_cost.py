"""Freeze robust prediction bounds from training costs, not target outcomes."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
B=Path(sys.argv[1]);O=B/'results/revtrace/ces_20261023';D=O/'calibration_v5';D.mkdir(exist_ok=False)
src=O/'calibration_v4';x=json.loads((src/'CALIBRATION.json').read_text())
rows=[json.loads(l) for l in (src/'COST_TRAINING_ROWS.jsonl').read_text().splitlines()]
for mode,m in x['contextual_cost_models'].items():
 y=[r['seconds'] for r in rows if r['mode']==mode]
 m.update(prediction_floor_s=float(np.quantile(y,.05)),prediction_ceiling_s=float(np.quantile(y,.99)))
x.update(schema='CES-calibration-v5',parent_calibration_sha256=hashlib.sha256((src/'CALIBRATION.json').read_bytes()).hexdigest(),
 prediction_bounds='training-only5th/99th percentiles; same predictions for cost and CES; actual observations never clipped')
(D/'CALIBRATION.json').write_text(json.dumps(x,indent=2)+'\n')
print(json.dumps({k:{z:v for z,v in m.items() if 'prediction_' in z} for k,m in x['contextual_cost_models'].items()}))
