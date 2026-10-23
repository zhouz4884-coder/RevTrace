"""Compare local archived analysis/controller bytes against pre-outcome release."""
from pathlib import Path
import hashlib,json
W=Path(__file__).resolve().parent;x=json.loads((W/'FORMAL_RELEASE_REMOTE.json').read_text())
pairs={'formal_design_sha256':'FORMAL_FREEZE.md','controller_sha256':'run_formal.py',
 'auditor_sha256':'audit_ces_final.py','statistics_sha256':'row_stats_core.py','analysis_sha256':'summarize_formal.py'}
for k,p in pairs.items():assert hashlib.sha256((W/p).read_bytes()).hexdigest()==x[k],p
assert x['source_commit']=='e0aeae1b418644c378dde331c59b55fc5948b40f' and x['authorized_formal_cells']==180
(W/'FORMAL_RELEASE_BYTE_AUDIT.json').write_text(json.dumps({'status':'PASS_PRE_OUTCOME_RELEASE_IDENTICAL_TO_ARCHIVED_CODE',
 'source_commit':x['source_commit'],'verified_files':pairs,'no_measurement_or_parameter_changes':True},indent=2)+'\n')
print('PASS_PRE_OUTCOME_RELEASE_IDENTICAL_TO_ARCHIVED_CODE')
