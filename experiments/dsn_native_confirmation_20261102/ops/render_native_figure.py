from pathlib import Path
import hashlib,json,platform,subprocess,sys
import matplotlib
from remote import Remote,O
E=Path(__file__).resolve().parents[1];R=E.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=E/'figures/source_root_v2';manifest=E/'packages/NATIVE_FIGURE_V2_SOURCE.json';m=json.loads(manifest.read_bytes());inp=E/'figures/INPUTS_v11.json';out=E/'figures/FIGURES_v11_v2';d=E/'figures/launch_v11_r3';d.mkdir(exist_ok=False);archive=O+'/native_figure_exports_v2'
for row in json.loads(inp.read_bytes())['sources']:assert sha(R/row['path'])==row['sha256']
env=d/'ENVIRONMENT.json';env.write_text(json.dumps(dict(python=sys.version,executable=sys.executable,platform=platform.platform(),matplotlib=matplotlib.__version__,scope='Local rendering only, no new endpoint measurement or model call'),indent=2)+'\n')
record=dict(experiment_id='REVTRACE_NATIVE_CONTENT_FIGURE_RENDER_20261102_V3',code_commit=m['code_commit'],source_manifest_sha256=sha(manifest),frozen_config=str(inp),frozen_config_sha256=sha(inp),environment_record=str(env),environment_record_sha256=sha(env),raw_result_location=archive,aggregate_summary_location=archive+'/SUMMARY.json',gate_decision_location=archive+'/GATE.json',bounded_local_export_location=str(out),execution_scope='Windows figure rendering; byte-exact outputs archived on8TB; original scientific raw data remain8TB',new_model_calls=0,actual_reader_calls=0)
rec=d/'RUN_RECORD_PRELAUNCH.json';rec.write_text(json.dumps(record,indent=2)+'\n')
subprocess.run([sys.executable,'-B',str(E/'ops/activate_source.py'),'--source',str(source),'--manifest',str(manifest),'--tag','NATIVE_FIGURE_RENDER_V3','--run-record',str(rec)],check=True,cwd=R,capture_output=True)
command=[sys.executable,'-B',str(source/'render_native.py'),'--input',str(inp),'--out',str(out)]
r=subprocess.run(command,cwd=source,capture_output=True);(d/'OUTPUT.txt').write_bytes(r.stdout+r.stderr);assert r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')
record.update(command=command,root_noarg_gate_sha256=sha(E/'ROOT_NOARG_NATIVE_FIGURE_RENDER_V3.json'),summary_sha256=sha(out/'SUMMARY.json'),gate_sha256=sha(out/'GATE.json'))
(d/'RUN_RECORD_COMPLETE.json').write_text(json.dumps(record,indent=2)+'\n')
with Remote() as c:
 c.python('from pathlib import Path\np=Path('+repr(archive)+');p.mkdir(exist_ok=False)\n')
 for p in out.iterdir():c.put(p,archive+'/'+p.name)
 for p,n in [(inp,'CONFIG.json'),(env,'ENVIRONMENT.json'),(d/'RUN_RECORD_COMPLETE.json','RUN_RECORD.json'),(E/'ROOT_NOARG_NATIVE_FIGURE_RENDER_V3.json','ROOT_SOURCE_GATE.json'),(manifest,'SOURCE_MANIFEST.json')]:c.put(p,archive+'/'+n)
print(r.stdout.decode())
