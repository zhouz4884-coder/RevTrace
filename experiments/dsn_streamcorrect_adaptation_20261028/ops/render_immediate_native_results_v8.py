import pathlib,json
T=pathlib.Path(__file__).resolve().parents[1];out=T/'final_native_v8_evidence'
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
records=read(out/'IMMEDIATE_COLLECTION_MANIFEST.json')['files'];primary=read(out/'native_postanalyses_v8/primary_quantiles/SUMMARY.json');feedback=read(out/'native_postanalyses_v8/feedback_characterization/SUMMARY.json');ready=read(out/'ready_opportunity_v1/SUMMARY.json');groups=[]
for arm in ['sequential','drop','joint']:
 rows=[x for x in primary['cells'] if x['stage']=='formal' and x['arm']==arm];groups.append(dict(arm=arm,cells=len(rows),slo_pass=sum(x['original_quantile_test_pass'] for x in rows),credit_seconds=sum(x['dual_deadline_audio_credit_seconds'] for x in rows),offered_audio_seconds=sum(x['offered_audio_seconds'] for x in rows),D99=[x['primary_linear_all_offered_D99'] for x in rows],C99=[x['primary_linear_all_offered_C99'] for x in rows]))
fc=[x for x in feedback['cells'] if x.get('stage')=='formal' and x.get('status')=='CHARACTERIZED_ACTUAL_COMPLETIONS'];counts={}
for x in fc:
 for k,v in x['surface_counts'].items():counts[k]=counts.get(k,0)+v
result=dict(decisions=records[:3],primary_by_arm=groups,formal_feedback_surface_counts=counts,formal_empty_selected_continuations=sum(x['empty_selected_continuations'] for x in fc),ready=dict(model_pairs=ready['model_evaluated_pairs'],full_end_equal=ready['full_end_state_equal_among_model_pairs'],controller_ready_pairs=ready['controller_ready_pairs'],unique_authority_ready=ready['unique_authority_jobs_with_controller_ready_private'],nonempty_controller_ready_pairs=sum(x['both_native_model_evaluated'] and x['controller_received_before_authority_dispatch'] and x['private_nonempty_text'] for x in ready['pairs']),whole_infer_timings=ready['matched_same_input_total_timings']))
(out/'IMMEDIATE_RESULT_TABLE.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
