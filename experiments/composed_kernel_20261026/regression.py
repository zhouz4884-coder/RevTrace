"""Reproduce baseline's supported protocol suite, plus CK5 tests."""
from pathlib import Path
import subprocess,sys,json,hashlib
W=Path(__file__).resolve().parent;R=W/'runtime'
names=['crash_observation','certified_envelope','envelope_snapshot','envelope_event_driven',
 'envelope_failure_controls','post_compute_order','live_qwen','lazy_reconciliation','properties_abc',
 'certified_display','continuity_proof','standard_async','durable_journal','consumer_bound_identity',
 'row_lifecycle_transport','dgft','online_coordinator','row_executor_protocol','row_worker_provenance',
 'row_progress_integration','terminal_recovery_contract','localagreement_display','composed_kernel']
tag=sys.argv[1] if len(sys.argv)>1 else 'v3'
out=W/('CPU_'+sys.platform+'_'+tag+'.log');assert not out.exists()
cmd=[sys.executable,'-m','pytest',*[f'tests/test_{s}.py' for s in names],'-q',
 '--basetemp='+str(W/('cpu_scope_'+sys.platform+'_'+tag)),'--junitxml='+str(W/('CPU_'+sys.platform+'_'+tag+'.xml'))]
with out.open('wb') as f:r=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
print(out.read_text(errors='replace'));assert r.returncode==0
