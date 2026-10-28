"""Recompute bounded opportunity evidence from completed, unmodified pilot logs.

No model, scheduler or production protocol code is imported or executed.
Input ACK is a readiness constraint here; deadlines always retain the original
episode origin + source offset + audio duration. No counterfactual saving is
reported as an observed result.
"""
from pathlib import Path
import hashlib,json,statistics

ROOT=Path(__file__).resolve().parent
INPUT_FIELDS=['source_id','language','prompt_tokens','fault_actual_prompt_tokens','chunk_id',
    'audio_start_sample','audio_end_sample','prefix_audio_sha256','interval_audio_sha256']
OUTPUT_FIELDS=['token_ids','state_tokens','text','terminated_by_eos','hit_token_limit','generated_tokens']


def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(line) for line in p.read_text().splitlines() if line]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def value_sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def projection(row,names):return {key:row[key] for key in names if key in row}


def load(name):
    d=ROOT/name;c=d/'attempt0'
    cfg=read(c/'config.json');events=lines(c/'events.jsonl');records=lines(c/'worker_records.jsonl')
    consumer=lines(c/'consumer.jsonl');costs=lines(c/'worker_batch_accounting.jsonl')
    cancel_path=c/'worker_cancelled_records.jsonl';cancelled=lines(cancel_path) if cancel_path.exists() else []
    jobs={(r['job']['session_id'],r['job']['end_window'],r['job']['role']):r for r in records}
    assert len(jobs)==len(records)
    origin=cfg['episode_origin_perf'];owner_start=next(e['t0_perf'] for e in events if e['kind']=='run-start')
    specs={s['session_id']:s for s in read(c/'sessions.json')}
    batches=read(d/'audit/BATCHES.json');frontiers=read(d/'audit/FRONTIERS.json')
    offered=sum(round(s['duration']*16000) for s in specs.values())
    accepted=sum(max(e['to_sample'] for e in events if e['kind']=='input-ack' and e['session_id']==sid) for sid in specs)
    assert offered==accepted
    assert abs(sum(f['audio_seconds'] for f in frontiers)-offered/16000)<1e-8
    for f in frontiers:
        assert abs(f['original_ready_perf']-(origin+specs[f['session_id']]['offset']+f['frontier']/16000))<1e-7
    return dict(name=name,d=d,cfg=cfg,events=events,records=records,jobs=jobs,consumer=consumer,
        costs=costs,cancelled=cancelled,origin=origin,owner_start=owner_start,specs=specs,batches=batches,
        frontiers=frontiers,summary=read(d/'audit/SUMMARY.json'),offered_samples=offered,accepted_samples=accepted)


def actual_time(arm,event):return arm['owner_start']+event['time']
def batch(arm,index):return next(b for b in arm['batches'] if b['worker']=='proposal-0' and int(b['batch_id'].rsplit(':',1)[1])==index)
def queue_evidence(arm,sid):
    current=arm['jobs'][sid,6,'proposal'];job=current['job']
    old=arm['jobs'].get((sid,5,'proposal'))
    if old:previous=old['result']['received_perf']
    else:previous=next(r['cancellation']['received_perf'] for r in arm['cancelled'] if r['job']['session_id']==sid and r['job']['end_window']==5)
    accepted=min(actual_time(arm,e) for e in arm['events'] if e['kind']=='input-ack' and e['session_id']==sid and e['to_sample']>=job['audio_end_sample'])
    ready=max(job['audio_ready_perf'],previous,accepted)
    first=next(f for f in arm['frontiers'] if f['session_id']==sid and f['frontier']==192000)
    view=next(c for c in arm['consumer'] if c['session_id']==sid and c['observed_perf']==first['first_actual_visible_perf'])
    outcomes=[e['kind'] for e in arm['events'] if e.get('job_id')==job['job_id'] and e['kind'] in ['display','proposal-obsolete']]
    assert len(outcomes)==1
    origin=arm['origin'];prior=batch(arm,5)
    return dict(job_id=job['job_id'],original_audio_ready_perf=job['audio_ready_perf'],
      original_display_deadline_perf=job['audio_ready_perf']+2.,
      original_certified_deadline_perf=job['audio_ready_perf']+8.,
      input_ACK_perf=accepted,previous_owner_terminal_perf=previous,
      conservative_ready_perf=ready,actual_enqueue_perf=job['enqueue_perf'],
      ready_to_actual_enqueue_seconds=job['enqueue_perf']-ready,
      prior_worker_lease_overlap_seconds=max(0.,min(prior['drained_perf'],job['enqueue_perf'])-ready),
      original_ready_relative_origin=job['audio_ready_perf']-origin,
      input_ACK_relative_origin=accepted-origin,actual_enqueue_relative_origin=job['enqueue_perf']-origin,
      owner_outcome=outcomes[0],first_actual_visible_perf=first['first_actual_visible_perf'],
      first_actual_visible_relative_origin=first['first_actual_visible_perf']-origin,
      first_actual_visible_source=view['source_kind'],display_latency=first['display_latency'])


def lane_evidence(arm):
    result={}
    for lane in ['proposal','authority']:
        bs=[b for b in arm['batches'] if lane in b['worker']]
        result[lane]=dict(physical_batches=len(bs),complete_rows=sum(b['full_rows'] for b in bs),
          model_phase_seconds=sum(b['model_seconds'] for b in bs),
          physical_lease_seconds=sum(b['physical_lease_seconds'] for b in bs),
          last_actual_drain_relative_origin=max(b['drained_perf'] for b in bs)-arm['origin'])
    return result


def pair(repeat):
    base=load(f'row_complete-F2-r{repeat}');covered=load(f'covered-F2-r{repeat}')
    assert base['specs']==covered['specs'] and base['offered_samples']==covered['offered_samples']
    assert len(base['frontiers'])==len(covered['frontiers'])==135
    rows=[]
    for sid in range(16):
        a=base['jobs'][sid,6,'proposal'];b=covered['jobs'][sid,6,'proposal']
        neural=projection(a['job'],INPUT_FIELDS);output=projection(a['result'],OUTPUT_FIELDS)
        checks=dict(neural_fields_equal=neural==projection(b['job'],INPUT_FIELDS),
          complete_model_input_audit_equal=a['result']['model_input_audit']==b['result']['model_input_audit'],
          actual_execution_context_equal=a['result']['execution_context_audit']==b['result']['execution_context_audit'],
          complete_output_equal=output==projection(b['result'],OUTPUT_FIELDS))
        assert all(checks.values()),(repeat,sid,checks)
        rows.append(dict(session_id=sid,relation='target-session' if sid==8 else 'other-legitimate-session',
          checks=checks,neural_input=neural,model_input_audit_sha256=value_sha(a['result']['model_input_audit']),
          selected_full_output=output,selected_full_output_sha256=value_sha(output),
          baseline=queue_evidence(base,sid),covered=queue_evidence(covered,sid)))
    # Peer order is part of the actual numerical operation, not merely a row set.
    ids=lambda a:[(r['job']['session_id'],r['job']['source_id']) for r in a['records'] if r['job']['_delivery']['batch_id']==batch(a,6)['batch_id']]
    a_cost=next(c for c in base['costs'] if c['batch_id']==batch(base,6)['batch_id'])
    b_cost=next(c for c in covered['costs'] if c['batch_id']==batch(covered,6)['batch_id'])
    a_order=[next(r['job']['session_id'] for r in base['records'] if r['job']['job_id']==jid) for jid in a_cost['job_ids']]
    b_order=[next(r['job']['session_id'] for r in covered['records'] if r['job']['job_id']==jid) for jid in b_cost['job_ids']]
    assert a_order==b_order==list(range(16))
    short=[]
    for sid in [0,2,6,10]:
        arms={}
        for name,arm in [('baseline',base),('covered',covered)]:
            F=round(arm['specs'][sid]['duration']*16000)
            f=next(q for q in arm['frontiers'] if q['session_id']==sid and q['frontier']==F)
            candidate=arm['jobs'].get((sid,7,'proposal'))
            retired=[e for e in arm['events'] if e['kind']=='private-deadline-retired' and e['session_id']==sid and e['window']==7]
            row=next(c for c in arm['consumer'] if c['session_id']==sid and c['observed_perf']==f['first_actual_visible_perf'])
            arms[name]=dict(frontier=F,original_audio_ready_relative_origin=f['original_ready_perf']-arm['origin'],
              original_display_deadline_relative_origin=f['original_ready_perf']+2.-arm['origin'],
              private_job_issued=candidate is not None,
              actual_private_enqueue_relative_origin=None if candidate is None else candidate['job']['enqueue_perf']-arm['origin'],
              unissued_deadline_retired=bool(retired),
              retired_relative_origin=None if not retired else actual_time(arm,retired[0])-arm['origin'],
              actual_visible_source=row['source_kind'],actual_visible_relative_origin=f['first_actual_visible_perf']-arm['origin'],
              actual_certified_relative_origin=f['first_actual_certified_perf']-arm['origin'],
              display_latency=f['display_latency'],commit_view_latency=f['commit_view_latency'])
        short.append(dict(session_id=sid,**arms))
    maps=lambda a:{(f['session_id'],f['frontier']):f for f in a['frontiers']}
    af,bf=maps(base),maps(covered)
    rescued=[dict(session_id=k[0],frontier=k[1],audio_seconds=bf[k]['audio_seconds']) for k in af if not af[k]['dual_credit'] and bf[k]['dual_credit']]
    lost=[dict(session_id=k[0],frontier=k[1],audio_seconds=af[k]['audio_seconds']) for k in af if af[k]['dual_credit'] and not bf[k]['dual_credit']]
    waiting=[r for r in rows if r['session_id']!=8]
    lanes={name:lane_evidence(arm) for name,arm in [('baseline',base),('covered',covered)]}
    metrics={name:dict(lifecycle=arm['summary']['lifecycle'],service=arm['summary']['service']) for name,arm in [('baseline',base),('covered',covered)]}
    compact=dict(all_16_exact_same_inputs_and_full_outputs=True,peer_order_equal=True,
      baseline_window6_outcomes={key:sum(r['baseline']['owner_outcome']==key for r in rows) for key in ['display','proposal-obsolete']},
      covered_window6_outcomes={key:sum(r['covered']['owner_outcome']==key for r in rows) for key in ['display','proposal-obsolete']},
      other_sessions=15,
      other_session_baseline_queue_range=[min(r['baseline']['ready_to_actual_enqueue_seconds'] for r in waiting),max(r['baseline']['ready_to_actual_enqueue_seconds'] for r in waiting)],
      other_session_covered_queue_range=[min(r['covered']['ready_to_actual_enqueue_seconds'] for r in waiting),max(r['covered']['ready_to_actual_enqueue_seconds'] for r in waiting)],
      batch6_actual_dispatch_relative_origin={name:batch(a,6)['dispatch_perf']-a['origin'] for name,a in [('baseline',base),('covered',covered)]},
      batch5_actual_model_seconds={name:batch(a,5)['model_seconds'] for name,a in [('baseline',base),('covered',covered)]},
      credited_audio_rescued_seconds=sum(x['audio_seconds'] for x in rescued),
      credited_audio_lost_seconds=sum(x['audio_seconds'] for x in lost))
    return dict(repeat=repeat,scope='two repeated actual pilot episodes; no new independent source cohort',
      sources=16,offered_frontiers=135,offered_audio_samples=base['offered_samples'],
      accepted_audio_samples_both_arms=base['accepted_samples'],offered_audio_seconds=base['offered_samples']/16000,
      original_deadline_rule='origin + session.offset + frontier/16000; then display +2s / certified +8s',
      input_ACK_role='readiness constraint only; never a new latency/deadline origin',
      original_origins={name:a['origin'] for name,a in [('baseline',base),('covered',covered)]},
      compact=compact,window6_exact_rows=rows,short_EOF_rows=short,lane_costs=lanes,
      rescued_dual_credit_frontiers=rescued,lost_dual_credit_frontiers=lost,metrics=metrics)


pairs=[pair(0),pair(1)]
inputs={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for cell in
    ['row_complete-F2-r0','covered-F2-r0','row_complete-F2-r1','covered-F2-r1']
    for p in sorted((ROOT/cell).rglob('*')) if p.is_file()}
output=dict(analysis_id='REVTRACE-PHYSRET-PILOT-R0R1-OBSERVED-OPPORTUNITY',
    analysis_script_sha256=sha(Path(__file__)),execution_code_commit='1d8c30804a945570429d85d934b3bfcba6171a43',
    evidence_tier='recorded actual pilot dispatch/input/Consumer/physical-clock analysis; no new GPU calls',
    inputs=inputs,pairs=pairs,
    interpretation='earlier physical release lets identical legitimate computation meet its usefulness window; total-model savings are not observed',
    limits=['controlled wrong-conditioning F2, not natural prevalence','two repeats on the same 16 sources, not independent cohorts',
      'both dual-P99 gates still fail','ordinary watchdog and parent-cancellation strong controls not evaluated here',
      'cross-arm scheduling/feedback changes after intervention; later input sequences need not remain equal'])
(ROOT/'OPPORTUNITY_EVIDENCE.json').write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
print(json.dumps([p['compact'] for p in pairs],indent=2))
