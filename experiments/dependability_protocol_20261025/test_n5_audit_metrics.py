"""Local recorded-input oracle checks, not new GPU experiments."""
from pathlib import Path
import csv,json,copy
import pytest
import audit_n5_formal_v1 as checker
W=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
OLD=read(W/'n5_development_audit_v1/SUMMARY.json')['episodes']
NEW=read(W/'n5_development_expanded_audit_v2/SUMMARY.json')['episodes']
def test_primary_metrics_unchanged_for_all12_same_input_recordings():
 assert len(OLD)==len(NEW)==12
 for a,b in zip(OLD,NEW):
  assert a['episode']==b['episode']
  for k,v in a.items():assert b[k]==v,(a['episode'],k)
def test_exact_backlog_and_frontier_denominators():
 rows=list(csv.DictReader((W/'n5_development_expanded_audit_v2/FRONTIERS.csv').open()))
 for s in NEW:
  subset=[r for r in rows if r['episode']==s['episode']]
  assert len(subset)==s['whole_offered_frontiers']
  assert 0<=s['valid_provisional_ahead_coverage_per_offered_audio']<=1
  assert s['exact_pending_unaccepted_peak_audio_seconds']>=s['unaccepted_offered_peak_audio_seconds']
  assert s['exact_unadmitted_offered_peak_audio_seconds']>=s['accepted_debt_peak_audio_seconds']
  assert s['final_accepted_audio_seconds']>=0 and s['final_accepted_uncertified_debt_audio_seconds']==0
def test_physical_group_fsync_not_per_commit_multiplication():
 for s in NEW:
  E=W/'n5_development_collected_v2/development'/s['episode'];r=read(E/'attempt0/result.json')
  assert 0<s['canonical_commit_group_fsync_calls']<=r['certified_commits']
  assert s['input_snapshot_syncs']+1==r['input_fsync_calls']
  assert s['actual_row_emission_to_owner_receive_P50']>=0
  assert s['actual_publication_to_Consumer_applied_P50']>=0
def test_recovery_clocks_are_not_conflated():
 for s in read(W/'N5_RECOVERY_INDEPENDENT_AUDIT_v3.json')['episodes']:
  assert s['canonical_journal_recovery_seconds']<s['kill_to_all_previous_certified_consumed_seconds']
  assert s['original_episode_wall_seconds']<s['resource_lifecycle_seconds_from_origin']
  assert s['original_deadlines_retained'] and not s['whole_run_dual_P99_pass']

def test_changed_granularity_contract_rejected(monkeypatch):
 E=W/'n5_development_collected_v2/development/fine_fair-c4-sync-r0';original=checker.read
 def altered(p):
  r=original(p)
  if p==E/'attempt0/config.json':r=copy.deepcopy(r);r['rho']=2
  return r
 monkeypatch.setattr(checker,'read',altered)
 with pytest.raises(AssertionError):checker.audit_episode(E,original(W/'n5_development_collected_v2/DEVELOPMENT_MANIFEST.json'))

def test_missing_issued_neural_row_rejected(monkeypatch):
 E=W/'n5_development_collected_v2/development/fine_fair-c4-sync-r0';original=checker.lines
 def altered(p):
  r=original(p)
  return r[:-1] if p==E/'attempt0/worker_records.jsonl' else r
 monkeypatch.setattr(checker,'lines',altered)
 with pytest.raises(AssertionError,match='cannot hide an unfinished issued job'):
  checker.audit_episode(E,checker.read(W/'n5_development_collected_v2/DEVELOPMENT_MANIFEST.json'))

def test_dropping_expired_frontier_from_denominator_rejected(monkeypatch):
 E=W/'n5_development_collected_v2/development/cde_full-c16-staggered-r0';original=checker.lines
 raw=original(E/'attempt0/events.jsonl');assert any(e['kind']=='private-deadline-retired' for e in raw)
 def altered(p):
  r=original(p)
  return [e for e in r if e['kind']!='private-deadline-retired'] if p==E/'attempt0/events.jsonl' else r
 monkeypatch.setattr(checker,'lines',altered)
 with pytest.raises(AssertionError):checker.audit_episode(E,checker.read(W/'n5_development_collected_v2/DEVELOPMENT_MANIFEST.json'))
