"""Independent recorded operator equality/lease checks, zero model calls."""
from pathlib import Path
import hashlib,json,sys
B=Path(sys.argv[1]);O=B/'results/revtrace/row_completion_20261023';D=O/'row_operator_v1';A=O/'row_operator_independent_v1';A.mkdir(exist_ok=False)
def read(p):return json.loads(p.read_text())
try:
 summary=read(D/'SUMMARY.json');assert summary['invocations']==36 and not (D/'STOP.json').exists()
 ops=read(D/'RUN.json')['operations'];checks=[]
 for i,o in enumerate(ops):
  records=[read(D/f'op{i}-batch-r0.json'),read(D/f'op{i}-row-r0.json'),read(D/f'op{i}-row-r1.json')]
  states=lambda x:[{k:r[k] for k in ['token_ids','state_tokens','text','terminated_by_eos','hit_token_limit']} for r in x['results']]
  assert states(records[0])==states(records[1])==states(records[2])
  for rset in zip(*(x['results'] for x in records)):
   assert rset[0]['model_input_audit']['batch_tensors']==rset[1]['model_input_audit']['batch_tensors']==rset[2]['model_input_audit']['batch_tensors']
  for x in records:
   assert len(x['results'])==o['rows'] and len({r['job_id'] for r in x['results']})==o['rows']
   if x['results'][0].get('row_delivery_protocol'):
    account=[t for t in x['telemetry'] if t['kind']=='batch-accounting'];assert len(account)==1
    assert set(account[0]['job_ids'])=={r['job_id'] for r in x['results']}
    assert x['physical_drained_observed_perf']>=account[0]['batch_drained_perf']
  checks.append({'operation':i,'selected_outputs_and_recorded_inputs_equal':True,'rows':o['rows']})
 out={'status':'PASS_INDEPENDENT_PRODUCTION_ROW_OPERATOR_AUDIT','invocations':36,'physical_operations':12,
  'checks':checks,'new_model_calls':0,'scope':'real GPU operators, no state installation or serving claim',
  'GO_bounded_live_pilot':True,'no_independent_algorithm_claim':True,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (A/'SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='checks'}))
except BaseException as e:
 (A/'STOP.json').write_text(json.dumps({'error':repr(e),'raw_preserved':True})+'\n');raise
