"""Whole-episode recovery summaries, keeping all three RTO clocks distinct."""
from pathlib import Path
import argparse,csv,hashlib,json,statistics
def read(p):return json.loads(p.read_text())
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 a.output.mkdir(exist_ok=False);primary=read(a.root/'postfault_cpu_v2/PRIMARY_v1.json');freeze=read(a.root/'formal_fault/FREEZE.json')
 assert len(primary['episodes'])==len(freeze['cells'])==21
 rows={r['episode']:r for r in primary['episodes']};groups={}
 for c in freeze['cells']:
  name=f"{c['method']}-{c['workload']}-r{c['repeat']}";r=rows[name]
  assert r['method']==c['method'] and r['acknowledged_input_loss_samples']==0
  groups.setdefault(c['method'],{})[c['repeat']]=r
 assert len(groups)==7;out=[]
 metrics=['original_episode_wall_seconds','kill_to_all_previous_certified_consumed_seconds',
  'restart_process_launch_to_all_previous_certified_consumed_seconds','canonical_journal_recovery_seconds',
  'all_offered_audio_goodput_2_8','GPU_J_per_offered_audio_second','display_P99','commit_P99','all_offered_WER_percent',
  'accepted_debt_peak_audio_seconds','reserved_debt_peak_audio_seconds','abandoned_or_no_receipt_rows','total_unique_commits','prekill_durable_commits']
 for method,rs in sorted(groups.items()):
  assert set(rs)=={0,1,2};entries=[rs[i] for i in range(3)]
  r=dict(method=method,repeats=3,whole_dual_P99_passes=sum(e['whole_run_dual_P99_pass'] for e in entries),
   accepted_loss_samples=sum(e['acknowledged_input_loss_samples'] for e in entries),
   all_original_deadlines_retained=all(e['original_deadlines_retained'] for e in entries))
  for key in metrics:
   values=[e[key] for e in entries];r[key+'_each']=values
   r[key+'_median']=None if any(v is None for v in values) else statistics.median(values)
  out.append(r)
 result=dict(status='PASS21_ALL7_WHOLE_EPISODE_RECOVERY_GROUPS',groups=out,
  scope='same offered input and process-group fault rule, but per-method precrash selected frontiers/work can differ; no same-state warm-adoption or cross-fault-domain RTO claim',
  clocks='ledger replay, restart launch to actual view, kill to actual view kept separate; full episode includes cold reload; abandoned work billed',
  source_sha256=hashlib.sha256((a.root/'postfault_cpu_v2/PRIMARY_v1.json').read_bytes()).hexdigest(),checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 (a.output/'SUMMARY.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 with (a.output/'GROUPS.csv').open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(out[0]));writer.writeheader();writer.writerows([{k:json.dumps(v) if isinstance(v,list) else v for k,v in r.items()} for r in out])
 print(json.dumps(dict(groups=7,formal_episodes=21)))
if __name__=='__main__':main()
