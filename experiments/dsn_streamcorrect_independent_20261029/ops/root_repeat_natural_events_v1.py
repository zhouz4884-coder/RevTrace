"""Repeat the frozen natural-event reconstruction after root no-argument source gating."""
import datetime,hashlib,json,subprocess,sys
from pathlib import Path
I=Path(__file__).resolve().parents[1];R=I.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
manifest=I/'packages/NATURAL_EVENT_ANALYSIS_SOURCE_v1.json';m=read(manifest)
assert m['source_commit']=='dd2cb7e7816fcfd7d6be5194f8f883c98dba1f78'
pointer=R/'experiments/repository_identity_20261027/CURRENT.json';backup=I/'CURRENT_BEFORE_NATURAL_ROOT_REPEAT_v1.json'
assert not backup.exists();backup.write_bytes(pointer.read_bytes());x=read(pointer)
x.update(source_worktree=str(I/'natural_event_analysis_source_v1'),source_manifest=str(manifest),source_manifest_sha256=sha(manifest),source_commit=m['source_commit'],GPU_queue='LOCAL_CPU_ONLY_NATURAL_EVENT_ROOT_REPEAT',scope='Separate frozen post-hoc natural-event CPU source; no new neural work or endpoint changes.',previous_pointer=str(backup))
pointer.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
r=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],check=True,capture_output=True)
assert json.loads(r.stdout)['code_commit']==m['source_commit'];(I/'NATURAL_ROOT_NOARG_PREFLIGHT_v1.json').write_bytes(r.stdout)
cfg=read(I/'NATURAL_EVENT_DIAGNOSTIC_v1_FROZEN.json');cfg.update(experiment_id=cfg['experiment_id']+'_ROOT_REPEAT',root_repeat_created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),repeat_scope='Same recorded natural events, code and inputs; source-gated CPU repeat, not additional acoustic observations.')
cp=I/'NATURAL_ROOT_REPEAT_CONFIG_v1_FROZEN.json';assert not cp.exists();cp.write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf8')
out=I/'NATURAL_EVENT_ROOT_REPEAT_RESULTS_v1'
record=dict(experiment_id=cfg['experiment_id'],code_commit=m['source_commit'],config_sha256=sha(cp),source_manifest_sha256=sha(manifest),raw_result_location=cfg['original_remote_raw_root'],summary=str(out/'SUMMARY.json'),gate=str(out/'GATE.json'),new_neural_calls=0,scope=cfg['repeat_scope'])
p=I/'NATURAL_ROOT_REPEAT_PRELAUNCH_v1.json';assert not p.exists();p.write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
subprocess.run([sys.executable,'-B',str(I/'natural_event_analysis_source_v1/check_events.py'),'--config',str(cp),'--manifest',str(manifest),'--out',str(out)],check=True)
assert read(out/'GATE.json')==read(I/'NATURAL_EVENT_RESULTS_v1/GATE.json')
print('PASS root noarg source gate and same-input CPU repeat; natural observations not counted twice.')

