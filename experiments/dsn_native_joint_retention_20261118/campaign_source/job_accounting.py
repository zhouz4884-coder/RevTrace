"""Independent per-job accounting; no model execution or performance inference."""
from collections import Counter
import argparse,json,pathlib,sys

TERMINALS=('selected_installed','selected_durable_replayed','fully_discarded',
           'pre_C_skipped','fenced_terminal','worker_lifecycle_terminated','owner_lifecycle_terminated')
PENDING=('still_ready','still_inflight','still_durable_selected_unapplied')

def audit_records(*,dispatches,installed=(),durable_jobs=None,replayed_transition_ids=(),
                  discarded=None,skipped=None,fenced=(),worker_lost=(),owner_dead_epochs=(),
                  ready=(),promotions=(),full_results=None,hints=(),closed=False,uir=False):
    """Classify unique jobs, retaining conflicts instead of silently prioritizing.

    Owner death is an explicit fallback for unfinished jobs from that incarnation.
    A durable fact surviving before Owner install is selected/replayed or pending,
    not falsely called lost computation. Promotion counts are annotations only.
    """
    errors=[];dispatches=list(dispatches);jobs={j['job_id']:j for j in dispatches}
    if len(jobs)!=len(dispatches):errors.append('duplicate dispatch job identity')
    durable_jobs=durable_jobs or {};discarded=discarded or {};skipped=skipped or {};full_results=full_results or {}
    installed=list(installed);fenced=list(fenced);worker_lost=list(worker_lost)
    for label,items in [('install',installed),('fenced terminal',fenced),('worker-loss terminal',worker_lost)]:
        if len(items)!=len(set(items)):errors.append('duplicate '+label+' outcome')
    categories={name:set() for name in TERMINALS+PENDING}
    categories['selected_installed']=set(installed)
    for jid in installed:
        if jid not in durable_jobs:errors.append('install lacks durable selected fact: '+jid)
    for jid,fact in durable_jobs.items():
        if jid in categories['selected_installed']:continue
        name='selected_durable_replayed' if fact.get('transition_id') in set(replayed_transition_ids) else 'still_durable_selected_unapplied'
        categories[name].add(jid)
    categories['fully_discarded']=set(discarded)
    categories['pre_C_skipped']=set(skipped)
    categories['fenced_terminal']=set(fenced)
    categories['worker_lifecycle_terminated']=set(worker_lost)
    assignments=Counter(j for values in categories.values() for j in values)
    for jid,n in assignments.items():
        if n>1:errors.append('overlapping outcomes for '+jid)
        if jid not in jobs:errors.append('outcome lacks original dispatch: '+jid)
    assigned=set(assignments)
    for jid,job in jobs.items():
        if jid not in assigned and job.get('owner_epoch') in set(owner_dead_epochs):
            categories['owner_lifecycle_terminated'].add(jid)
    assigned.update(categories['owner_lifecycle_terminated'])
    categories['still_ready']=set(ready)-assigned
    for jid in categories['still_ready']:
        if jid not in jobs:errors.append('ready result lacks dispatch: '+jid)
    assigned.update(categories['still_ready'])
    categories['still_inflight']=set(jobs)-assigned
    for jid,item in skipped.items():
        terminal=item.get('worker_terminal_event',{})
        if (terminal.get('learned_C_executed') is not False or terminal.get('C_U_completed') is not False
                or terminal.get('feedback_cut_emitted') is not False):
            errors.append('pre-C skip lacks original partial-execution terminal: '+jid)
    promoted=list(promotions);promoted_unique=set(promoted)
    selected=categories['selected_installed']|categories['selected_durable_replayed']
    for jid in promoted_unique & selected:
        record=durable_jobs.get(jid,{}).get('record',{})
        if record.get('native_model_evaluated') is not True:
            errors.append('selected promoted full job lacks actual model-evaluated record: '+jid)
    actual_mismatch='actual_canonical_disagrees_with_complete_start'
    mismatched=set(j for j,item in discarded.items() if item.get('proof',{}).get('kind')==actual_mismatch)
    mismatched.update(h['job_id'] for h in hints if h.get('proof',{}).get('kind')==actual_mismatch)
    sent=[h for h in hints if h.get('c_entry_skip_hint_sent') is True or h.get('kind') in ('known_invalid_C_skip_hint','policy_C_entry_skip_hint')]
    if uir:
        if sent:errors.append('UIR forwarded cooperative C-entry skip hints')
        if categories['pre_C_skipped']:errors.append('UIR has pre-C cooperative abandonment')
        if mismatched & selected:errors.append('UIR selected a known-mismatched complete input')
        returned_mismatched=mismatched & set(full_results)
        unresolved=returned_mismatched-(categories['fully_discarded']|categories['fenced_terminal']|categories['worker_lifecycle_terminated']|categories['owner_lifecycle_terminated'])
        if unresolved:errors.append('UIR returned mismatched full result lacks refusal/lifecycle outcome')
    counts={k:len(v) for k,v in categories.items()}
    pending=sum(counts[k] for k in PENDING)
    if closed and pending:errors.append('claimed closed drain has pending jobs')
    partition_count=sum(counts.values())
    if partition_count!=len(jobs):errors.append('dispatch/outcome partition does not close')
    ready_reuse=selected & set(ready)
    return dict(status='PASS_DISJOINT_JOB_ACCOUNTING' if not errors else 'FAIL_JOB_ACCOUNTING_PRESERVED',
        errors=errors,dispatches=len(jobs),counts=counts,partition_count=partition_count,
        disjoint=not any('overlap' in e for e in errors),closed_drain_requested=closed,
        closed_drain_terminal_sum=sum(counts[k] for k in TERMINALS),pending_jobs=pending,
        promotion_events=len(promoted),unique_promoted_jobs=len(promoted_unique),
        selected_promoted_jobs=len(promoted_unique & selected),promotions_are_not_terminal_category=True,
        Owner_admitted_ready_reuse=len(ready_reuse),ready_reuse_positive_is_hard_gate=False,
        zero_ready_reuse_requires_timing_audit=not ready_reuse,
        zero_ready_reuse_establishes_policy_equivalence=False,
        UIR=dict(enabled=uir,C_entry_skip_hints_sent=len(sent),known_mismatched_jobs=len(mismatched),
                 known_mismatched_selected=len(mismatched & selected),
                 known_mismatched_full_results_returned=len(mismatched & set(full_results)),
                 known_mismatched_full_results_discarded=len(mismatched & categories['fully_discarded'])),
        jobs={k:sorted(v) for k,v in categories.items()},
        scope='actual recorded protocol outcomes only; zero reuse is not equivalence; promotions are not terminals')

def lines(path):
    if not path.exists():return []
    return [json.loads(line) for line in path.read_text(encoding='utf8').splitlines() if line.strip()]

def audit_trial(path,scan_facts,closed=True):
    """Read new native Owner raw logs and caller-supplied trusted WAL scanner."""
    path=pathlib.Path(path);cfg=json.loads((path/'CONFIG.json').read_bytes())
    dispatches=[];installed=[];discarded={};skipped={};fenced=[];worker_lost=[];ready=set();promotions=[];full={};hints=[];parse_errors=[]
    for attempt in sorted(path.glob('owner_e*')):
        for row in lines(attempt/'dispatch.jsonl'):
            dispatches.append(dict(row['job'],owner_epoch=row['owner_epoch']))
        for row in lines(attempt/'owner_events.jsonl'):
            kind=row['kind']
            if kind=='canonical_install':installed.append(row['job_id'])
            if kind=='validated_full_receipt' and row['outcome_kind']=='buffered_full':ready.add(row['job_id'])
            if kind in ('known_invalid_C_skip_hint','policy_C_entry_skip_hint','input_or_coverage_reason_observed_without_C_entry_skip'):hints.append(row)
        for row in lines(attempt/'policy_audit.jsonl'):
            kind=row['kind'];body=row.get('body',{})
            if kind=='promotion':promotions.append(body['job_id'])
            elif kind in ('discarded_full','abandoned_full'):
                target=discarded if kind=='discarded_full' else skipped;jid=body['job']['job_id']
                if jid in target:parse_errors.append('duplicate '+kind+' disposition: '+jid)
                target[jid]=body
            elif kind=='worker_lost':worker_lost.extend(body['retired_live_jobs'])
            elif kind=='inbound_disposition' and body.get('outcome',{}).get('kind')=='fenced_terminal':fenced.append(body['outcome']['job']['job_id'])
        for row in lines(attempt/'worker_results.jsonl'):
            event=row['event']
            if event.get('kind')=='completed':full.setdefault(event['job_id'],event)
    facts={}
    for obj,receipt in scan_facts(path/'facts.wal'):
        if obj['kind']!='canonical':continue
        jid=obj['body']['job']['job_id']
        if jid in facts:parse_errors.append('duplicate durable selected job: '+jid)
        facts[jid]=obj['body']
    replayed={r.get('transition_id') for r in lines(path/'consumer.jsonl') if r.get('kind')=='canonical'}
    dead={r['owner_epoch'] for r in lines(path/'supervisor.jsonl') if r['kind']=='owner_group_death_confirmed'}
    result=audit_records(dispatches=dispatches,installed=installed,durable_jobs=facts,replayed_transition_ids=replayed,
        discarded=discarded,skipped=skipped,fenced=fenced,worker_lost=worker_lost,owner_dead_epochs=dead,
        ready=ready,promotions=promotions,full_results=full,hints=hints,closed=closed,uir=cfg['arm']=='uir')
    result.update(cell_id=cfg['cell_id'],arm=cfg['arm'])
    if parse_errors:
        result['errors'].extend(parse_errors);result['status']='FAIL_JOB_ACCOUNTING_PRESERVED'
    return result

def resource_diagnostic(first,second,threshold=.02):
    """Resource drift requests diagnosis, never outcome rejection or retries."""
    values={}
    for key in sorted(set(first)&set(second)):
        a,b=first[key],second[key]
        if isinstance(a,(int,float)) and isinstance(b,(int,float)):
            scale=max(abs(a),abs(b));delta=abs(a-b)/scale if scale else 0.
            values[key]=dict(first=a,second=b,relative_difference=delta,diagnostic_required=delta>threshold)
    return dict(threshold=threshold,values=values,diagnostic_required=any(v['diagnostic_required'] for v in values.values()),
                reject_or_retry=False,exclude_or_drop_outcome=False,action='diagnose_and_retain_all_outcomes')

def main():
    p=argparse.ArgumentParser();p.add_argument('--cell',required=True);p.add_argument('--runtime-source',required=True);p.add_argument('--runtime-manifest',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    sys.path.insert(0,a.runtime_source)
    from native_service import verify_source
    from resilience_storage import scan
    identity=verify_source(pathlib.Path(a.runtime_manifest))
    result=audit_trial(a.cell,scan);result['runtime_identity']=identity
    out=pathlib.Path(a.out);assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='jobs'},indent=2))
    return 0 if result['status'].startswith('PASS') else 1
if __name__=='__main__':raise SystemExit(main())
