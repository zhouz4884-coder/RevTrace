"""Paper-artifact rendering only; retain frozen numerical outputs and source."""
from pathlib import Path
import csv,hashlib,importlib.metadata,json,os,platform,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1];source=E/'sensitivity/source_dev'
sys.dont_write_bytecode=True;sys.path.insert(0,str(source))
from sensitivity_common import verify_self
identity=verify_self(E/'packages/SENSITIVITY_V1_SOURCE.json')
data_path=E/'sensitivity/RESULTS_v1/PAPER_DATA.json';data=json.loads(data_path.read_bytes())
assert data['status']=='PASS_FROZEN_D2_POSITIVE_CONTROL_AND_SOURCE_PAIRED_SENSITIVITY'
full_path=E/'sensitivity/RESULTS_v1/BANK_FULL_CDF.csv'
with full_path.open(encoding='utf-8') as f:
    full=list(csv.DictReader(f))
for row in full:
    for key in ['tau_d_seconds','duration_weighted_fraction','source_min_fraction','source_max_fraction']:
        row[key]=float(row[key])
target=E/'sensitivity/FIGURES_v1';assert not target.exists()
os.environ['MPLCONFIGDIR']=str(E/'paper_qa/plot_config')
from plot_sensitivity import render
exports=render(data['bank_curves'],full,data['source_paired_D2'],data['repeat_paired_D2'],target)
rows=[]
for path in exports['exports']:
    p=Path(path);rows.append(dict(path=p.relative_to(E).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
record=dict(gate='PLOT_EXPORT_COMPLETE_VISUAL_QA_PENDING',source=identity,python=sys.version,platform=platform.platform(),
            matplotlib=importlib.metadata.version('matplotlib'),data_sha256=hashlib.sha256(data_path.read_bytes()).hexdigest(),
            full_curve_sha256=hashlib.sha256(full_path.read_bytes()).hexdigest(),rows=rows,new_measurements=0,exports=exports)
p=E/'sensitivity/FIGURE_EXPORT_v1.json';assert not p.exists();p.write_bytes((json.dumps(record,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in record.items() if k not in {'rows','exports'}}))
