"""Local read-only existing admission predicate replay, no neural inference."""
from pathlib import Path
import hashlib,json,sys
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime_n5_v3/scripts'))
from audit_dsn_journal import audit
R=W/'n5_recovery_development_collected_v1';out=W/'N5_RECOVERY_CANONICAL_WAL_REPLAY_v1.json';assert not out.exists();checks=[]
for name in json.loads((R/'recovery_development/SUMMARY.json').read_text())['completed']:
 E=R/'recovery_development'/name;wal=E/'canonical.wal';before=hashlib.sha256(wal.read_bytes()).hexdigest()
 r=audit(wal);assert r['restart_epochs']==1
 r=audit(wal,E/'attempt1',expected_prior_commits=r['commits_before_latest_restart'])
 assert hashlib.sha256(wal.read_bytes()).hexdigest()==before;checks.append(dict(episode=name,audit=r))
out.write_text(json.dumps(dict(status='PASS_READ_ONLY_EXISTING_CANONICAL_ADMISSION_PREDICATES',checks=checks,new_neural_GPU_calls=0),indent=2)+'\n')
print(json.dumps([dict(episode=x['episode'],commits=x['audit']['commits'],pre=x['audit']['commits_before_latest_restart']) for x in checks]))
