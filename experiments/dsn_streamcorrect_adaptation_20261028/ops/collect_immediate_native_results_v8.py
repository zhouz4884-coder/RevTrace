import pathlib,json,hashlib,sys,statistics
T=pathlib.Path(__file__).resolve().parents[1];out=T/'final_native_v8_evidence';out.mkdir(exist_ok=True)
O='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_20261028'
names=['native_campaign_v8_continuation_auditfix_v1/GATE.json','native_campaign_v8_continuation_auditfix_v1/SUMMARY.json','native_postanalyses_v8/SUMMARY.json','native_postanalyses_v8/primary_quantiles/GATE.json','native_postanalyses_v8/primary_quantiles/SUMMARY.json','native_postanalyses_v8/feedback_characterization/GATE.json','native_postanalyses_v8/feedback_characterization/SUMMARY.json','ready_opportunity_v1/GATE.json','ready_opportunity_v1/SUMMARY.json']
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client();records=[]
try:
 s=c.open_sftp()
 for name in names:
  p=out/name;p.parent.mkdir(parents=True,exist_ok=True)
  with s.open(O+'/'+name,'rb') as f:b=f.read(2500001)
  assert len(b)<=2500000
  if p.exists():assert p.read_bytes()==b
  else:p.write_bytes(b)
  records.append(dict(path=name,remote=O+'/'+name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
 s.close()
finally:c.close()
(out/'IMMEDIATE_COLLECTION_MANIFEST.json').write_text(json.dumps(dict(files=records,total_bytes=sum(x['bytes'] for x in records)),indent=2))
primary=json.loads((out/'native_postanalyses_v8/primary_quantiles/SUMMARY.json').read_text());feedback=json.loads((out/'native_postanalyses_v8/feedback_characterization/SUMMARY.json').read_text());ready=json.loads((out/'ready_opportunity_v1/SUMMARY.json').read_text());groups=[]
for arm in ['sequential','drop','joint']:
 rows=[x for x in primary['cells'] if x['stage']=='formal' and x['arm']==arm];groups.append(dict(arm=arm,cells=len(rows),slo_pass=sum(x['original_quantile_test_pass'] for x in rows),credit_seconds=sum(x['dual_deadline_audio_credit_seconds'] for x in rows),offered_audio_seconds=sum(x['offered_audio_seconds'] for x in rows),D99=[x['primary_linear_all_offered_D99'] for x in rows],C99=[x['primary_linear_all_offered_C99'] for x in rows]))
fc=[x for x in feedback['cells'] if x.get('stage')=='formal' and x.get('status')=='CHARACTERIZED_ACTUAL_COMPLETIONS'];counts={}
for x in fc:
 for k,v in x['surface_counts'].items():counts[k]=counts.get(k,0)+v
result=dict(decisions=records[:3],primary_by_arm=groups,formal_feedback_surface_counts=counts,formal_empty_selected_continuations=sum(x['empty_selected_continuations'] for x in fc),ready=dict(model_pairs=ready['model_evaluated_pairs'],full_end_equal=ready['full_end_state_equal_among_model_pairs'],controller_ready_pairs=ready['controller_ready_pairs'],unique_authority_ready=ready['unique_authority_jobs_with_controller_ready_private'],nonempty_controller_ready_pairs=sum(x['both_native_model_evaluated'] and x['controller_received_before_authority_dispatch'] and x['private_nonempty_text'] for x in ready['pairs']),whole_infer_timings=ready['matched_same_input_total_timings']))
(out/'IMMEDIATE_RESULT_TABLE.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
