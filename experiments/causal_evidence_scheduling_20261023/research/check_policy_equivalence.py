"""Replay *decisions*, not models: isolate stronger-control code changes."""
from pathlib import Path
import hashlib,json,subprocess,sys,types
W=Path(__file__).resolve().parent;S=W/'runtime';sys.path.insert(0,str(S/'src'))
from revtrace.ces_policy import Target,choose
old=types.ModuleType('frozen_v3_policy');sys.modules[old.__name__]=old
raw=subprocess.check_output(['git','-C',str(S),'show','8d5c5f4d81157b007eff86e93e252e3d12365c9b:src/revtrace/ces_policy.py']).decode()
exec(compile(raw,'frozen-source-v3','exec'),old.__dict__)
snap=json.loads((W/'POLICY_SNAPSHOTS_v3.json').read_text());cal=json.loads((W/'CALIBRATION_v5.json').read_text())
for x in snap:
 e=x['event'];c=x['config'];p=c['ces_study'];kw=dict(now=e['observed_perf'],mode='ces',cal=cal,limit=c['microbatch'],display_slo=p['display_slo'],wait_cap=p['wait_cap'])
 a=old.choose([old.Target(**t) for t in e['features']],**kw);b=choose([Target(**t) for t in e['features']],**kw)
 assert a==b,(x['cell'],a,b)
 for k in ['operation','sids','score','planned_seconds','wait_seconds']:
  assert a.get(k)==e.get(k),(k,a.get(k),e.get(k))
r={'status':'PASS_FULL_CES_POLICY_UNCHANGED_ON_ALL_V3_RECORDED_SNAPSHOTS','snapshots':len(snap),
 'old_source':'8d5c5f4d81157b007eff86e93e252e3d12365c9b','new_source':'e0aeae1b418644c378dde331c59b55fc5948b40f',
 'scope':'CPU decision replay only, no new model outputs or serving-performance inference',
 'new_changes':'stronger ablations/additional simple controls/per-run source provenance only',
 'snapshot_sha256':hashlib.sha256((W/'POLICY_SNAPSHOTS_v3.json').read_bytes()).hexdigest()}
(W/'FULL_CES_POLICY_EQUIVALENCE_v4.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
