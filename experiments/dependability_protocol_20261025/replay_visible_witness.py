"""CPU policy counterfactual over an unchanged real GPU publication trace.

This is not another GPU run, timing measurement or unchanged full deployment
contract: only the Consumer interpretation is replayed under a stronger rule.
"""
from pathlib import Path
import hashlib,json,sys
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime/src'))
from revtrace.certified_display import ContinuityView
C=W/'formal_collected/formal/standard-snapshot-ahead-authority_first-0'
events=[json.loads(x) for x in (C/'events.jsonl').read_text().splitlines()]
actual=[json.loads(x) for x in (C/'consumer.jsonl').read_text().splitlines()]
witness=json.loads((W/'N1_VISIBLE_WITNESS_FORWARD_v1.json').read_text())['witnesses'][0]
job=witness['frozen_job']['job_id'];at=witness['publication']['displayed'];sid=witness['frozen_job']['session_id']
views={k:ContinuityView(k,strict_bound=True) for k in ['snapshot','two_lane']};target={}
for e in events:
    for policy,v in views.items():
        r=v.consume(e)
        if e.get('job_id')==job and e['kind']=='display':target[policy]=r
snapshot=target['snapshot'];guarded=target['two_lane']
assert snapshot['valid_visible_frontier']==128000 and snapshot['certified_frontier']==96000
assert guarded['valid_visible_frontier']==guarded['certified_frontier']==96000 and guarded['tentative_invalidated']
live=next(r for r in actual if r['source_kind']=='display' and r['session_id']==sid and r['server_time']==at)
for k in ['valid_visible_frontier','visible_text','certified_frontier','certified_text','canonical_version']:
    assert live[k]==snapshot[k],k
out={'status':'PASS_ACTUAL_SNAPSHOT_REPRODUCTION_AND_EXACT_CHAIN_RULE_CPU_COUNTERFACTUAL',
 'cell':C.name,'job_id':job,'actual_snapshot_record':live,'CPU_snapshot':snapshot,'CPU_full_chain':guarded,
 'source_events_sha256':hashlib.sha256((C/'events.jsonl').read_bytes()).hexdigest(),
 'scope':'real measured GPU/actual Snapshot Consumer witness; exact same trace replay under two_lane is CPU-only and makes no new SLO/GPU/cost claim',
 'selected_IPC_intervention_causal_attribution':False,
 'why':'witness precedes the selected authority12/proposal14 IPC hold; demonstrates asynchronous reachability in the shared prefix, not causal effect of that later target'}
(W/'N1_VISIBLE_WITNESS_POLICY_REPLAY_v1.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'job':job,'actual_visible_seconds':live['valid_visible_frontier']/16000,
 'actual_certified_seconds':live['certified_frontier']/16000,'CPU_guarded_visible_seconds':guarded['valid_visible_frontier']/16000,'new_GPU_calls':0}))
