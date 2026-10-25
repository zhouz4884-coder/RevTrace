"""Paid frozen-target operator feasibility test. No live serving result."""
from pathlib import Path
import argparse,copy,hashlib,json,os,subprocess,sys,time
ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);a=ap.parse_args();B=a.base
P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025';S=P/'runtime'
sys.path[:0]=[str(S/'src'),str(S/'scripts')]
from tc_live_worker import GPUExecutor

def save(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 assert not (O/'B_GPU_STARTED.json').exists()
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
 cases=json.loads((O/'B_CASES.json').read_text())['cases'];assert cases
 output=O/'B_operator_v1';assert not output.exists();output.mkdir()
 save(O/'B_GPU_STARTED.json',{'pid':os.getpid(),'time_unix':time.time(),'source_manifest_sha256':sha(S/'SOURCE_MANIFEST.json'),
  'cases_sha256':sha(O/'B_CASES.json'),'scope':'paid operator diagnostic; not serving','repeats':3})
 first=cases[0];rt=dict(first['cfg']['authority_runtime']);rt.update(model=str(B/'models/Qwen3-ASR-1.7B'),gpu=1,
  manifest=str(B/'results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json'),
  runtime_digest='v6-operator-'+sha(S/'SOURCE_MANIFEST.json'),row_delivery='batch',capture_model_inputs=True,
  online_selection_mode='strict',online_oracle_diagnostic=False,fallback_layout='selective',fallback_operator_probe=True)
 worker=GPUExecutor('authority-B-operator',rt);allrows=[]
 try:
  worker.wait_ready();pid=worker.process.pid;proc=Path('/proc')/str(pid)
  save(output/'OWNED_WORKER_HANDLES.json',[{'pid':pid,'name':worker.name,'linux_start_ticks':proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]}])
  for repeat in range(3):
   for ci,case in enumerate(cases):
    jobs=copy.deepcopy(case['jobs'])
    for i,j in enumerate(jobs):
     j.pop('_delivery',None);j['job_id']=f'B-r{repeat}-case{ci}-row{i}';j['runtime_digest']=rt['runtime_digest']
    begin=time.perf_counter();worker.submit(jobs);rows=None
    while rows is None:
     rows=worker.poll()
     if time.perf_counter()-begin>180:raise TimeoutError('bounded operator call exceeded180s')
     time.sleep(.001)
    duration=time.perf_counter()-begin;proof=next((r['online_verification']['fallback_operator_probe'] for r in rows if r['online_verification'].get('fallback_operator_probe')),None)
    record={'case':ci,'repeat':repeat,'source_cell':case['source_cell'],'source_batch':case['batch_id'],
      'operator_host_submit_to_return_seconds':duration,'jobs':jobs,'rows':rows,'operator':proof,
      'new_GPU_evidence':True,'scope':'physical operator; paid original/repeat/reprocess/repeat, not deployed speedup'}
    save(output/f'case{ci}-r{repeat}.json',record);allrows.append(record)
    print('B_COMPLETE',len(allrows),flush=True)
 finally:worker.close()
 probes=[r['operator'] for r in allrows if r['operator']]
 assert len(allrows)==len(cases)*3
 equiv=all(p['baseline_repeat_equal'] and p['reprocessed_repeat_equal'] and p['baseline_reprocessed_equal'] for p in probes)
 ratios=[(p['reprocess_CPU_and_copy_seconds']+p['reprocessed_model_seconds'])/p['baseline_seconds'] for p in probes]
 import statistics
 raw=json.loads((O/'B_FIRST_MISMATCHES.json').read_text())['rows'];positions=[r['first_mismatch'] for r in raw if r['first_mismatch'] is not None]
 long=sum(k>=16 for k in positions)
 report={'status':'COMPLETE_PAID_OPERATOR_FEASIBILITY','calls':len(allrows),'probes_with_actual_failures':len(probes),
   'equivalence_gate':'PASS_TESTED_LAYOUTS' if equiv and probes else 'NO-GO',
   'median_reprocess_total_over_original_model_time':statistics.median(ratios) if ratios else None,
   'trim_integration_GO':bool(equiv and ratios and statistics.median(ratios)<.95),
   'first_mismatch_rows':len(positions),'first_mismatch_median_zero_based':statistics.median(positions) if positions else None,
   'long_verified_prefix_16plus':long,'suffix_only_decision':'NO-GO_SHORT_OR_UNCERTIFIED_PREFIX_OPPORTUNITY' if not positions or long/len(positions)<.25 else 'CONDITIONAL_OPPORTUNITY_REQUIRES_SEPARATE_CERTIFICATION',
   'GPU_queue_closed':True,'worker_exited':not worker.process.is_alive(),'scope':'operator measurements; full sequence/EOS/P/text equivalence and serving cost remain separate',
   'source_manifest_sha256':sha(S/'SOURCE_MANIFEST.json')}
 save(O/'B_SUMMARY.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':run()
