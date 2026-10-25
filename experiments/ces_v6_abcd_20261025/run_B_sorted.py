"""Paid fallback control in the original frozen physical Batch row order."""
from pathlib import Path
import argparse,copy,hashlib,json,os,statistics,subprocess,sys,time
p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);a=p.parse_args();B=a.base
P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025';S=P/'runtime'
sys.path[:0]=[str(S/'src'),str(S/'scripts'),str(S/'scripts/v100')]
from tc_live_worker import GPUExecutor
from run_v100_matrix import PowerSampler
from revtrace.certified_display import TrustedQwenRender
from transformers import AutoProcessor,GenerationConfig
from qwen_asr import parse_asr_output

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def main():
 assert (O/'ABC_SUMMARY.json').exists(),'Wait for existing A/C queue to close'
 assert not (O/'B_sorted_GPU_STARTED.json').exists()
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
 source=json.loads((S/'SOURCE_MANIFEST.json').read_text())
 for r in source['files']:assert sha(S/r['path'])==r['sha256']
 cases=json.loads((O/'B_CASES_SORTED_v2.json').read_text())['cases'];output=O/'B_operator_sorted_v2';output.mkdir()
 rt=dict(cases[0]['cfg']['authority_runtime']);rt.update(model=str(B/'models/Qwen3-ASR-1.7B'),gpu=1,
  manifest=str(B/'results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json'),
  runtime_digest='v6-sorted-operator-'+sha(S/'SOURCE_MANIFEST.json'),row_delivery='batch',capture_model_inputs=True,
  online_selection_mode='strict',online_oracle_diagnostic=True,fallback_layout='selective',fallback_operator_probe=True)
 tok=AutoProcessor.from_pretrained(rt['model'],local_files_only=True).tokenizer
 eos=GenerationConfig.from_pretrained(rt['model'],local_files_only=True).eos_token_id;eos=[eos] if isinstance(eos,int) else eos
 render=TrustedQwenRender(tok,parse_asr_output,eos,256)
 save(O/'B_sorted_GPU_STARTED.json',{'pid':os.getpid(),'time_unix':time.time(),'cases_sha256':sha(O/'B_CASES_SORTED_v2.json'),'source_manifest_sha256':sha(S/'SOURCE_MANIFEST.json'),'repeats':3,'operator_not_serving':True,'oracle_diagnostic_paid':True})
 sampler=PowerSampler([0,1],interval=.1);sampler.start();worker=GPUExecutor('authority-B-sorted',rt);allrows=[]
 try:
  worker.wait_ready();pid=worker.process.pid
  save(output/'OWNED_WORKER_HANDLES.json',[{'pid':pid,'name':worker.name,'linux_start_ticks':Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[19]}])
  for repeat in range(3):
   for ci,case in enumerate(cases):
    jobs=copy.deepcopy(case['jobs'])
    for i,j in enumerate(jobs):j.pop('_delivery',None);j['job_id']=f'B-sorted-r{repeat}-c{ci}-{i}';j['runtime_digest']=rt['runtime_digest']
    begin=time.perf_counter();worker.submit(jobs);rows=None
    while rows is None:
     rows=worker.poll()
     if time.perf_counter()-begin>180:raise TimeoutError('operator180s')
     time.sleep(.001)
    duration=time.perf_counter()-begin;proof=next(r['online_verification']['fallback_operator_probe'] for r in rows if r['online_verification'].get('fallback_operator_probe'))
    layout=all(r['model_input_audit']['batch_tensors']==old['batch_tensors'] for r,old in zip(rows,case['old_input_audits']))
    checks=[]
    for index,z,zr,zt,ztr in zip(proof['failed_indices'],proof['baseline_tokens'],proof['baseline_repeat_tokens'],proof['reprocessed_tokens'],proof['reprocessed_repeat_tokens']):
     values=[render(jobs[index],t) for t in [z,zr,zt,ztr]]
     checks.append({'row':index,'complete_Z_equal':z==zr==zt==ztr,'P_text_equal':all(v==values[0] for v in values),'stop_budget_equal':len({(t[-1] in eos,len(t)==256 and t[-1] not in eos,len(t)) for t in [z,zr,zt,ztr]})==1,'tokens':len(z)})
    record={'case':ci,'repeat':repeat,'source_cell':case['source_cell'],'source_batch':case['batch_id'],'jobs':jobs,'rows':rows,'operator':proof,'historical_full_batch_tensors_equal':layout,'render_and_stop_checks':checks,'operator_submit_to_return_seconds':duration,'new_GPU_evidence':True,'scope':'Paid original-layout operator+oracle; not deployed serving'}
    save(output/f'case{ci}-r{repeat}.json',record);allrows.append(record);print('B_SORTED_COMPLETE',len(allrows),flush=True)
 finally:
  worker.close();summary=sampler.stop();save(output/'POWER.json',{'samples':sampler.rows,'summary':summary,'includes_initialization_all_operator_and_oracle_calls':True})
 equivalent=all(r['historical_full_batch_tensors_equal'] and all(all(c[k] for k in ['complete_Z_equal','P_text_equal','stop_budget_equal']) for c in r['render_and_stop_checks']) for r in allrows)
 ratios=[(r['operator']['reprocess_CPU_and_copy_seconds']+r['operator']['reprocessed_model_seconds'])/r['operator']['baseline_seconds'] for r in allrows]
 # Repeated cases are a six-target diagnostic, not18 independent workloads.
 bycase=[statistics.median([ratios[i] for i,r in enumerate(allrows) if r['case']==c]) for c in range(len(cases))]
 save(O/'B_SORTED_SUMMARY.json',{'status':'COMPLETE_ORIGINAL_LAYOUT_PAID_OPERATOR_CONTROL','calls':len(allrows),'cases':len(cases),'repeats':3,'historical_full_batch_tensors_equal':all(r['historical_full_batch_tensors_equal'] for r in allrows),'full_Z_P_text_stop_repeat_equivalence':equivalent,'median_total_over_original':statistics.median(ratios),'case_median_ratios':bycase,'integration_GO':equivalent and statistics.median(ratios)<.95,'operator_not_serving':True,'worker_exited':not worker.process.is_alive(),'GPU_queue_closed':True,'script_sha256':sha(Path(__file__)),'source_manifest_sha256':sha(S/'SOURCE_MANIFEST.json')})
if __name__=='__main__':main()
