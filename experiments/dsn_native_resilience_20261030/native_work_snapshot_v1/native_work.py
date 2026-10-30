"""Counts of selected Canonical records, never a kernel/decoder-forward meter."""
import math

def selected_record_counts(records):
 result=dict(canonical_selected_steps=0,native_model_evaluated_marker_true=0,native_model_evaluated_marker_false=0,native_model_evaluated_marker_unknown=0,model_seconds_sum=0.,model_seconds_unknown=0,returned_token_ids_total=0,zero_returned_id_steps=0,returned_ids_unknown=0,correction_key_present=0,correction_payload_non_null=0,correction_payload_none=0,correction_key_missing=0)
 for record in records:
  result['canonical_selected_steps']+=1;value=record.get('native_model_evaluated')
  result['native_model_evaluated_marker_'+('true' if value is True else 'false' if value is False else 'unknown')]+=1
  value=record.get('model_seconds')
  if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>=0:result['model_seconds_sum']+=value
  else:result['model_seconds_unknown']+=1
  value=record.get('token_ids')
  if isinstance(value,list):result['returned_token_ids_total']+=len(value);result['zero_returned_id_steps']+=not value
  else:result['returned_ids_unknown']+=1
  if 'selected_correction' not in record:result['correction_key_missing']+=1
  else:
   result['correction_key_present']+=1;result['correction_payload_none' if record['selected_correction'] is None else 'correction_payload_non_null']+=1
 result.update(marker_definition="record.native_model_evaluated is derived from 'starting_tokens' in original generation; this is not a count of actual decoder/CUDA/kernel forwards",scope='Selected unique Canonical original-full-program receipts only; excludes warmup, discarded/abandoned and killed-unreturned work. Returned IDs/characters need not be new/correct ASR text. Sum of selected-call model_seconds is not whole-service latency, total paid work or a serving replay.')
 return result

def post_fault_clock_audit(consumer_rows, facts_by_sequence, event):
 """Audit original chosen row and independently locate a strictly newer consume."""
 fault=event['fault_perf'];preseq=event['pre_fault_durable_sequence'];original=event.get('first_new_model_completed_after_fault_and_certified_consume_perf');baselines={}
 for row in consumer_rows:
  if row['observed']<=fault:baselines[row['source_id']]=row['certified_frontier']
 def assess(row):
  seq=row.get('journal_sequence');fact=facts_by_sequence.get(seq);record=fact.get('record',{}) if fact else {};end=record.get('model_end');baseline=baselines.get(row['source_id']);marker=record.get('native_model_evaluated')
  numeric_end=isinstance(end,(float,int)) and not isinstance(end,bool) and math.isfinite(end)
  checks=dict(canonical_actual_consume=row.get('kind')=='canonical',after_fault=row['observed']>fault,sequence_newer_than_prefault=None if seq is None else seq>preseq,not_recovery_replay=not row.get('recovery_replay',False),model_end_strictly_after_fault=None if not numeric_end else end>fault,native_model_evaluated_marker_true=None if type(marker) is not bool else marker,actual_certified_frontier_advanced=None if baseline is None else row['certified_frontier']>baseline)
  verified=False if any(value is False for value in checks.values()) else None if any(value is None for value in checks.values()) else True
  return dict(consumer_observed_perf=row['observed'],source_id=row['source_id'],journal_sequence=seq,prefault_durable_sequence=preseq,prefault_actual_certified_frontier=baseline,actual_certified_frontier=row['certified_frontier'],canonical_frontier=fact.get('next_state',{}).get('frontier') if fact else None,record_model_end_perf=end if numeric_end else None,model_end_minus_fault=None if not numeric_end else end-fault,native_model_evaluated_marker=marker,checks=checks,strict_verified=verified)
 matching=[assess(row) for row in consumer_rows if row.get('kind')=='canonical' and original is not None and row['observed']==original]
 strict=next((value for row in consumer_rows if row.get('kind')=='canonical' and (value:=assess(row))['strict_verified'] is True),None)
 return dict(fault_perf=fault,original_selected_consume_perf=original,original_selected_actual_rows=matching,original_selected_strict_verified=matching[0]['strict_verified'] if len(matching)==1 else None,strict_first_actual_consume=strict,strict_fault_to_new_certified_consume_seconds=None if strict is None else strict['consumer_observed_perf']-fault,prefault_actual_certified_baselines=baselines,scope='Literal original clock retained alongside a separate strict post-fault endpoint. starting_tokens-derived marker is not a decoder/kernel-forward probe. No missing clock is assigned zero.')
