"""Independent corrected-layout fallback gates; no new model execution."""
from pathlib import Path
import argparse,csv,hashlib,json,statistics
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();O=a.root
assert (O/'B_SORTED_SUMMARY.json').exists()
cases=json.loads((O/'B_CASES_SORTED_v2.json').read_text())['cases'];rows=[]
for path in sorted((O/'B_operator_sorted_v2').glob('case*-r*.json')):
 r=json.loads(path.read_text());c=cases[r['case']];op=r['operator']
 oldZ=all(v['token_ids']==z for v,z in zip(r['rows'],c['old_Z']))
 oracle=all(v['online_verification'].get('pilot_oracle',{}).get('same_input_repeat_equal',False) for v in r['rows'])
 warm_original=statistics.mean([op['baseline_seconds'],op['baseline_repeat_seconds']])
 warm_new=op['reprocess_CPU_and_copy_seconds']+statistics.mean([op['reprocessed_model_seconds'],op['reprocessed_repeat_seconds']])
 rows.append({'case':r['case'],'repeat':r['repeat'],'original_batch_rows':len(c['jobs']),'failed_rows':len(op['failed_indices']),'prompt_padding_gap':c['prompt_padding_gap'],'historical_full_tensor_equal':r['historical_full_batch_tensors_equal'],'historical_Z_equal':oldZ,'full_repeat_Z_P_text_stop_equal':all(all(x[k] for k in ['complete_Z_equal','P_text_equal','stop_budget_equal']) for x in r['render_and_stop_checks']),'paid_oracle_repeat_equal':oracle,'original_model_s':op['baseline_seconds'],'original_repeat_s':op['baseline_repeat_seconds'],'reprocess_CPU_copy_s':op['reprocess_CPU_and_copy_seconds'],'new_model_s':op['reprocessed_model_seconds'],'new_repeat_s':op['reprocessed_repeat_seconds'],'mean_paired_original_s':warm_original,'mean_paired_new_total_s':warm_new,'paired_total_ratio':warm_new/warm_original})
assert len(rows)==18
equiv=all(all(r[k] for k in ['historical_full_tensor_equal','historical_Z_equal','full_repeat_Z_P_text_stop_equal','paid_oracle_repeat_equal']) for r in rows)
ratios=[r['paired_total_ratio'] for r in rows];bycase=[statistics.median(r['paired_total_ratio'] for r in rows if r['case']==c) for c in range(6)]
# Integration needs material typical savings, not an outlier or original cold-call artifact.
go=equiv and statistics.median(ratios)<.95 and sum(x<1 for x in bycase)>=4
A=O/'B_independent_analysis';A.mkdir()
with (A/'B_OPERATOR_PAIRS.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
report={'status':'COMPLETE_CORRECTED_LAYOUT_OPERATOR_REVIEW','calls':len(rows),'unique_target_batches':6,'repeats':3,'all_equivalence_checks_pass':equiv,'median_paired_total_ratio':statistics.median(ratios),'case_median_ratios':bycase,'integration_GO':go,'decision':'GO_SHARED_OPERATOR_CONDITIONAL_TESTED_LAYOUTS' if go else 'NO_GO_INSUFFICIENT_PHYSICAL_SAVING_OR_EQUIVALENCE','additional_robustness':'Means of paid original/repeat and new/repeat; reprocessing CPU/copy charged. Fixed operator order and six selected padding cases limit generalization.','v1_rebatch_evidence_preserved_not_historical_layout_reproduction':True,'not_serving_speed_or_energy_gain':True,'new_model_calls':0,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(A/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
