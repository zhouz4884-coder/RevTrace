"""Explicit protocol regression entrypoint, not the entire historical repository."""
from pathlib import Path
import argparse,json,os,subprocess,sys,uuid
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
S=a.source.resolve();out=a.output.resolve();assert S.is_dir() and not out.exists();out.parent.mkdir(parents=True,exist_ok=True)
names=['dgft','online_admission','live_qwen','lazy_reconciliation','certified_display','consumer_bound_identity','continuity_proof','contract_manifest','terminal_recovery_contract','ces','ces_v5_policy','ces_v5_integration','row_executor_protocol','row_lifecycle_transport','row_progress_integration','durable_journal','ces_closed_loop','closed_loop_independent','v6_planner_cache','v6_anchor']
if (S/'tests/test_v6_credit_wiring.py').exists():names.append('v6_credit_wiring')
paths=['tests/test_'+n+'.py' for n in names];assert all((S/n).is_file() for n in paths)
temp=out.parent/('cpu_fixture_'+uuid.uuid4().hex);assert not temp.exists();temp.mkdir()
argv=[sys.executable,'-m','pytest',*paths,'-q','--basetemp',str(temp),'--junitxml',str(out)]
print(json.dumps({'scope':'Focused A/B/C/D/D1/WAL/row/evidence-choice regression; legacy report tools excluded','argv':argv,'GPU_calls':0}),flush=True)
raise SystemExit(subprocess.call(argv,cwd=S,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')))
