"""Read-only admission replay and honest physical cost of prepared operators."""
from pathlib import Path
import argparse,hashlib,json,sys
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime_n5_v3/scripts'))
from audit_dsn_journal import audit as wal_audit
from audit_n5 import read,lines,quantile
def audit(D):
 result=read(D/'result.json');events=lines(D/'events.jsonl');records=lines(D/'worker_records.jsonl');power=read(D/'POWER.json')
 before=hashlib.sha256((D/'canonical.wal').read_bytes()).hexdigest();wal=wal_audit(D/'canonical.wal')
 assert hashlib.sha256((D/'canonical.wal').read_bytes()).hexdigest()==before
 assert wal['final_frontier_samples']['0']==result['final_frontier'] and wal['commits']==result['final_state']['checkpoint_id']
 assert wal['restart_epochs']==0
 original=[]
 for p in D.glob('worker-*-receipts.jsonl'):
  original.extend(x['physical_accounting'] for x in lines(p) if x['kind']=='batch-drained')
 phases=[p for b in original for p in b['phases']]
 assert len(original)==result['actual_operator_requests']
 starts=power['start_perf'];ends=power['end_perf'];energy=0.;coverage={}
 for gpu in [0,1]:
  xs=sorted((x for x in power['samples'] if x['gpu']==gpu),key=lambda x:x['t']);covered=0.
  for a,b in zip(xs,xs[1:]):
   lo=max(starts,a['t']);hi=min(ends,b['t'])
   if hi<=lo:continue
   slope=(b['power_w']-a['power_w'])/(b['t']-a['t']);p0=a['power_w']+slope*(lo-a['t']);p1=a['power_w']+slope*(hi-a['t'])
   energy+=(p0+p1)*(hi-lo)/2;covered+=hi-lo
  coverage[str(gpu)]=covered/(ends-starts);assert coverage[str(gpu)]>.95
 calls=read(D/'PHYSICAL_CALLS.json')['calls'];selected=next(c for c in calls if c['purpose']=='selected-at-6s-held-before-install')
 actual_batches={b['job_ids'][0]:b for b in original};sp=actual_batches[selected['job']['job_id']]['phases']
 sync=[e for e in events if e['kind']=='wal-physical-timing' and e['phase']=='fsync']
 writes=[e for e in events if e['kind']=='wal-physical-timing' and e['phase']=='write']
 assert len(sync)==len(writes)==wal['commits']
 latency=[x['result']['received_perf']-x['result']['_row_receipt']['emitted_perf'] for x in records]
 assert all(x>=0 for x in latency)
 return dict(case=D.name,read_only_WAL=wal,operator_window_seconds=ends-starts,worker_init_seconds=result['worker_initialization_seconds'],
  observed_support_GPU_joules_NOT_full_window_if_coverage_below1=energy,power_coverage=coverage,
  full_operator_window_energy_measured=all(abs(v-1)<1e-9 for v in coverage.values()),
  actual_physical_batches=len(original),actual_neural_phases=len(phases),
  selected_at6_verification_seconds=sum(p['completed_perf']-p['started_perf'] for p in sp if p['phase']=='correct-context-strict'),
  selected_at6_actual_generation_seconds=sum(p['completed_perf']-p['started_perf'] for p in sp if p['phase']=='fresh-FP32-fallback'),
  selected_at6_neural_calls=len(sp),all_neural_phase_seconds=sum(p['completed_perf']-p['started_perf'] for p in phases),
  canonical_commit_fsync_calls=len(sync),canonical_commit_fsync_seconds=sum(e['completed']-e['started'] for e in sync),
  trusted_render_host_wall_seconds=sum(e['host_cpu_wall_seconds'] for e in events if e['kind']=='render-checked'),
  consumer_CPU_seconds=result['consumer']['consumer_cpu_seconds'],row_to_owner_P99=quantile(latency,.99),
  scope='prepared operator, no online SLO/goodput; observed power support only, uncovered edge energy unknown; diagnostics and physical work included; WAL predicate PASS does NOT supply missing trusted selection in weak negative')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--stage',choices=['pilot','formal'],default='pilot');p.add_argument('--require-full-power',action='store_true')
 a=p.parse_args();assert not a.output.exists()
 names=read(a.root/a.stage/'SUMMARY.json')['completed'];assert len(names)==(8 if a.stage=='pilot' else 64)
 rows=[audit(a.root/a.stage/n) for n in names]
 if a.require_full_power:assert all(r['full_operator_window_energy_measured'] for r in rows),'full power support still missing'
 a.output.write_text(json.dumps(dict(status='PASS_WAL_MODEL_TIMES_AND_POWER_SCOPE_DISCLOSED',stage=a.stage,cases=rows,new_neural_GPU_calls=0,
  checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
 print(json.dumps([{k:r[k] for k in ['case','selected_at6_verification_seconds','selected_at6_actual_generation_seconds','selected_at6_neural_calls']} for r in rows]))
