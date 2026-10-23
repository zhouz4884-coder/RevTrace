set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P=$B/projects/revtrace_ces_20261023
O=$B/results/revtrace/ces_20261023
"$B/envs/revbatch-cu128/bin/python" "$P/ces_wal_crash_cpu.py" "$P/runtime_v4" "$O/CPU_SIGKILL_v4"
"$B/envs/revbatch-cu128/bin/python" "$P/runtime_v4/scripts/test_row_wal_sigkill.py" "$O/ROW_WAL_CPU_v4"
"$B/envs/revbatch-cu128/bin/python" - "$P" "$O" <<'PY'
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
P,O=map(Path,sys.argv[1:]);B=P.parents[1]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert read(O/'pilot_v4_independent_audit_final/SUMMARY.json')['cells']==6
assert read(O/'CPU_SIGKILL_v4/SUMMARY.json')['status']=='PASS_CES_CPU_SIGKILL_WAL'
assert read(O/'ROW_WAL_CPU_v4/SUMMARY.json')['status']=='PASS_LINUX_ROW_WAL_SIGKILL_CPU_FIXTURE'
assert not (O/'FORMAL_RELEASE.json').exists() and not (O/'formal_v1').exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
weights=read(O/'pilot_v4/ENVIRONMENT.json')['model_weights']
assert weights=={'model-00001-of-00002.safetensors':'a4cd1f1a04d90b757dc7f7dd26254e69a013b19e80efe590a83c6a3bde8608d6','model-00002-of-00002.safetensors':'6e0b9d9e09e2e0238e7ef3cc8a484ab387e91b90f1900bedf88bc92d7929ccfc'}
core=B/'datasets/revtrace/phaseD_20261021/manifest.json';val=B/'results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json'
c,v=read(core)['sessions'],read(val)['sessions'];assert len(c)==len(v)==16
assert not {x['source_id'] for x in c}&{x['source_id'] for x in v}
assert len({x['source_id'].split('-')[0] for x in c+v})==32
old=read(B/'results/revtrace/row_completion_20261023/FORMAL_ROW_FREEZE_v1.json')
assert sha(core)==old['core_manifest_sha256'] and sha(val)==old['validation_manifest_sha256']
source=read(P/'runtime_v4/SOURCE_MANIFEST.json');assert source['code_commit']=='e0aeae1b418644c378dde331c59b55fc5948b40f'
for r in source['files']:assert sha(P/'runtime_v4'/r['path'])==r['sha256']
record={'status':'GO_FORMAL_EXECUTION_NOT_CONTRIBUTION_GO','authorized_formal_cells':180,
 'time_unix':time.time(),'source_commit':source['code_commit'],'formal_design_sha256':sha(P/'FORMAL_FREEZE.md'),
 'controller_sha256':sha(P/'run_formal.py'),'auditor_sha256':sha(P/'audit_ces_final.py'),
 'statistics_sha256':sha(P/'row_stats_core.py'),'analysis_sha256':sha(P/'summarize_formal.py'),
 'development_and_validation_manifests':[sha(core),sha(val)],'calibration_sha256':sha(O/'calibration_v5/CALIBRATION.json'),
 'no_independent_CES_outcomes_seen_before_freeze':True,'all_prototype_negative_results_preserved':True}
(O/'FORMAL_RELEASE.json').write_text(json.dumps(record,indent=2)+'\n')
with (O/'FORMAL_CONTROLLER.log').open('w') as f:q=subprocess.Popen([sys.executable,'-u',str(P/'run_formal.py'),str(B)],cwd=P,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
(O/'FORMAL_PID.json').write_text(json.dumps({'pid':q.pid,'source_commit':source['code_commit'],'controller_sha256':record['controller_sha256'],'started_unix':time.time()},indent=2)+'\n');print(q.pid)
PY
