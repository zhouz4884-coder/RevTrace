"""Verbatim frozen v7 presentation arithmetic; no new measurement."""
ARMS=('R0_S0','R0_S1','R1_S0','R1_S1')
def core_rows(j):
 rows=[r for r in j['core_runs'] if r['phase']=='primary' and r['adapter']=='qwen' and r['rho']==1 and r['arrival']=='staggered']
 assert len(rows)==15 and all(not r['whole_run_dual_P99_pass'] for r in rows)
 totals=[]
 for arm,withdraw,credit in zip(ARMS,(12,1,17,0),(654.115,628.435,664.150,680.760)):
  group=sorted([r for r in rows if r['arm']==arm],key=lambda x:x['cohort']);assert [r['cohort'] for r in group]==['A','B','C']
  vals=dict(arm=arm,withdrawals=sum(r['audio_rollback_events'] for r in group),credit=sum(r['dual_credited_audio_seconds'] for r in group),
    offered=sum(r['offered_audio_seconds'] for r in group),cohorts=[dict(cohort=r['cohort'],cell_id=r['cell_id'],withdrawals=r['audio_rollback_events'],
      credit=r['dual_credited_audio_seconds'],offered=r['offered_audio_seconds']) for r in group])
  assert vals['withdrawals']==withdraw and abs(vals['credit']-credit)<1e-9 and abs(vals['offered']-714.110)<1e-9
  table=next(r for r in j['core_tables']['tables'] if all(r[k]==v for k,v in dict(phase='primary',adapter='qwen',rho=1,arrival='staggered',arm=arm).items()))
  assert table['audio_rollback_events_sum']==withdraw and abs(table['dual_credited_audio_seconds_sum']-credit)<1e-9
  totals.append(vals)
 return totals

def native_rows(j):
 rows=[]
 for proposed in j['proposed_values']['rows']:
  key=('paired' if proposed['bank']=='matched' else 'resident')+'/'+proposed['policy'];g=j['native_content']['groups'][key]
  p=g['posterior_whole_text_support']['raw'];assert p['original_credit_unknown_seconds']==0
  vals=dict(bank=proposed['bank'],policy=proposed['policy'],offered=g['offered_audio_seconds'],timely=g['original_dual_credit_audio_seconds'],
   matching=p['original_credit_supported_seconds'],unmatched=p['original_credit_mismatching_seconds'],passes=g['original_request_gate_passes'],requests=g['request_instances'])
  vals['untimely']=vals['offered']-vals['timely']
  counts=p['all_offered_frontier_counts'];assert sum(counts.values())==136
  assert g['content']['raw']['introduced_code_point_occurrences']==180 and g['content']['raw']['retracted_occurrence_code_points']==14
  for actual,field in [('offered','offered_s'),('timely','timely_s'),('matching','timely_same_frontier_selected_text_s'),
    ('unmatched','timely_without_same_frontier_text_agreement_s'),('untimely','not_timely_s')]:assert abs(vals[actual]-proposed[field])<1e-9
  assert vals['passes']==proposed['pass_count'] and vals['requests']==8 and abs(sum(vals[k] for k in ('matching','unmatched','untimely'))-vals['offered'])<1e-9
  rows.append(vals)
 return rows

