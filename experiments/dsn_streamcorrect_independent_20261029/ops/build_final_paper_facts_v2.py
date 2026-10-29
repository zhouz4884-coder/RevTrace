"""Arithmetic/report formatting of the two already-complete frozen recounts."""
import hashlib,json,pathlib,statistics
F=pathlib.Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=read(F/'FINAL_PRIMARY_RESULTS_v2/SUMMARY.json');pp=read(F/'FINAL_PRIMARY_RESULTS_v2/PAIRS.json')
c=read(F/'FINAL_CONTENT_RESULTS_v2/AGGREGATES.json');cp=read(F/'FINAL_CONTENT_RESULTS_v2/PAIRS.json');cr=read(F/'FINAL_CONTENT_RESULTS_v2/RUNS.json');frontiers=read(F/'FINAL_CONTENT_RESULTS_v2/FIRST_COVERS_WITH_EXACT_F_SUPPORT.json')
by_content={(x['source_id'],x['repeat']):x for x in cp};rows=[]
for row in pp:
 x=by_content[row['source_id'],row['repeat']];r=dict(row)
 for label in ('conservative','fullspec'):
  r[label+'_C50']=x[label]['primary']['primary_linear_all_offered_C50'];r[label+'_D2_misses']=x[label]['primary']['D2_misses_all_offered'];r[label+'_C8_misses']=x[label]['primary']['C8_misses_all_offered']
  r[label+'_supported_credit']=x['contrast']['raw_same_actual_G_supported_credit'][label+'_seconds']
  r[label+'_EOS']=x[label]['EOS_and_complete_intervals']['EOS']
 r['same_actual_G_supported_credit_difference']=x['contrast']['raw_same_actual_G_supported_credit']['net_fullspec_minus_conservative_seconds']
 r['C50_reduction_fraction']=(r['conservative_C50']-r['fullspec_C50'])/r['conservative_C50']
 rows.append(r)
base=p['aggregates']['two_full_early'];full=p['aggregates']['two_full_spec_early']
median_base=statistics.median(base['C50_values']);median_full=statistics.median(full['C50_values'])
facts=dict(status='ARITHMETIC_REPORT_FROM_COMPLETE_FROZEN_PRIMARY_AND_CONTENT_RECOUNTS',
 primary_source_commit=p['analysis_source_commit'],acoustic_sources=4,fresh_repeats_per_arm_source=2,within_source_pairs=8,
 primary=p,content=c,pairs=rows,
 C50_summary=dict(median_of_run_C50_conservative=median_base,median_of_run_C50_fullspec=median_full,
   relative_reduction_of_run_medians=1-median_full/median_base,
   paired_absolute_reduction_range_seconds=[min(-r['C50_difference'] for r in rows),max(-r['C50_difference'] for r in rows)],
   paired_relative_reduction_range=[min(r['C50_reduction_fraction'] for r in rows),max(r['C50_reduction_fraction'] for r in rows)]),
 energy_summary=dict(conservative_service_joules=base['service_joules'],fullspec_service_joules=full['service_joules'],
   aggregate_reduction_fraction=1-full['service_joules']/base['service_joules'],
   paired_reduction_range=[min(r['energy_reduction_fraction'] for r in rows),max(r['energy_reduction_fraction'] for r in rows)]),
 unique_acoustic_CER=p['unique_acoustic_character_edits']/p['unique_acoustic_reference_characters'],
 all_eight_pairs_support_credit_positive=all(r['same_actual_G_supported_credit_difference']>0 for r in rows),
 strict_support_credit_gain_seconds=c['two_full_spec_early']['raw_same_actual_G_supported_credit']-c['two_full_early']['raw_same_actual_G_supported_credit'],
 strict_support_EOS_first_view_mismatch_count={arm:sum(f['EOS'] and f['support_at_actual_view_G']['raw_equal'] is False for f in frontiers if f['cell_id'] in {r['cell_id'] for r in cr if r['arm']==arm}) for arm in c},
 input_sha256={str(path.relative_to(F)):sha(path) for path in [F/'FINAL_PRIMARY_RESULTS_v2/SUMMARY.json',F/'FINAL_PRIMARY_RESULTS_v2/PAIRS.json',F/'FINAL_CONTENT_RESULTS_v2/AGGREGATES.json',F/'FINAL_CONTENT_RESULTS_v2/PAIRS.json']})
out=F/'FINAL_PAPER_FACTS_v2.json';assert not out.exists();out.write_text(json.dumps(facts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(C50_summary=facts['C50_summary'],energy_summary=facts['energy_summary'],unique_CER=facts['unique_acoustic_CER'],strict_support_gain=facts['strict_support_credit_gain_seconds'],all8supportpositive=facts['all_eight_pairs_support_credit_positive'],facts_sha256=sha(out))))
print('PAIRS')
for r in rows:
 print(json.dumps({k:r[k] for k in ['source_id','repeat','conservative_credit','fullspec_credit','conservative_supported_credit','fullspec_supported_credit','conservative_C50','fullspec_C50','conservative_D99','fullspec_D99','conservative_C99','fullspec_C99','conservative_joules','fullspec_joules','energy_reduction_fraction','conservative_D2_misses','fullspec_D2_misses','conservative_C8_misses','fullspec_C8_misses','conservative_EOS','fullspec_EOS']}))
