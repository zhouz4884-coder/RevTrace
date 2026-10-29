import pathlib,json,hashlib,datetime,sys
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028'
plan=json.loads((P/'NATIVE_CAMPAIGN_v8_FROZEN.json').read_text());rows=[]
for cell in plan['cells'][:2]:
 out=pathlib.Path(cell['out']);jobs={x['job_id']:x for x in [json.loads(s) for s in (out/'native_jobs.jsonl').read_text().splitlines()]};consumer=[json.loads(s) for s in (out/'consumer.jsonl').read_text().splitlines()]
 mismatches=[];unexpected=[];private=0
 for x in consumer:
  if x['private_job'] is None:continue
  private+=1;j=jobs[x['private_job']];end=j['end'];expected_F=end['frontier'] if end['transcript'] else 0
  if x['text']!=end['transcript'] or x['visible_frontier']!=end['frontier']:mismatches.append(dict(observed=x['observed'],source_id=x['source_id'],private_job=x['private_job'],display_text=x['text'],native_text=end['transcript'],display_F=x['visible_frontier'],native_F=end['frontier'],expected_Consumer_F=expected_F,canonical_sha=x['canonical_sha']))
  if x['text']!=end['transcript'] or x['visible_frontier']!=expected_F:unexpected.append(x)
 rows.append(dict(cell_id=cell['cell_id'],service_gate=json.loads((out/'GATE.json').read_text()),private_display_rows=private,old_audit_mismatches=mismatches,mismatches_outside_frozen_Consumer_empty_rule=unexpected,
  native_jobs_sha256=hashlib.sha256((out/'native_jobs.jsonl').read_bytes()).hexdigest(),consumer_sha256=hashlib.sha256((out/'consumer.jsonl').read_bytes()).hexdigest()))
r=dict(status='CPU_READONLY_EMPTY_DISPLAY_RULE_DIAGNOSTIC',observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),native_execution_source='61c9afac00561f7ff1351f3eba9fd95adb239e8c',all_old_mismatches_explained_by_frozen_Consumer_empty_text_rule=all(not x['mismatches_outside_frozen_Consumer_empty_rule'] for x in rows),cells=rows,scope='inspection only; does not change original controller gate or raw results')
p=O/'AUDIT_EMPTY_DISPLAY_DIAGNOSTIC_v8.json';assert not p.exists();p.write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
