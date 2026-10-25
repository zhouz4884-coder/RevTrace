"""Second, forward-graph witness check; no production or primary audit import."""
from pathlib import Path
import hashlib,json
W=Path(__file__).resolve().parent;C=W/'formal_collected/formal/standard-snapshot-ahead-authority_first-0'
load=lambda p:[json.loads(x) for x in p.read_text().splitlines() if x]
events=load(C/'events.jsonl');records=load(C/'worker_records.jsonl')
jobs={r['job']['job_id']:r['job'] for r in records};results={r['job']['job_id']:r['result'] for r in records}
consumer=load(C/'consumer.jsonl');canon={sid:dict(F=0,P=(),version=0) for sid in range(4)}
nodes={sid:[] for sid in range(4)};witnesses=[]
for e in events:
    sid=e.get('session_id')
    if e['kind']=='commit':canon[sid]=dict(F=e['audio_end_sample'],P=tuple(e['next_prompt_tokens']),version=e['version'])
    if e['kind']!='display':continue
    nodes[sid].append(e['job_id']);j=jobs[e['job_id']];s=canon[sid]
    if e['audio_end_sample']<=s['F']:continue
    # Forward reachable token states from the current certified boundary.
    reached={(round(s['F']/32000),s['P'],g) for g in range(20)};legal_jobs=set()
    changed=True
    while changed:
        changed=False
        for jid in nodes[sid]:
            q=jobs[jid];key=(q['chunk_id'],tuple(q['prompt_tokens']),q['branch_generation'])
            if key in reached:
                legal_jobs.add(jid);out=(q['end_window'],tuple(results[jid]['state_tokens']),q['branch_generation'])
                if out not in reached:reached.add(out);changed=True
            if q['audio_end_sample']==s['F'] and tuple(results[jid]['state_tokens'])==s['P']:
                out=(q['end_window'],s['P'],q['branch_generation'])
                if out not in reached:reached.add(out);changed=True
    if e['job_id'] in legal_jobs:continue
    r=next((r for r in consumer if r['source_kind']=='display' and r['session_id']==sid and r['server_time']==e['displayed']),None)
    if not r or r['valid_visible_frontier']<=r['certified_frontier']:continue
    prev=[x for x in nodes[sid] if jobs[x]['end_window']==j['chunk_id'] and jobs[x]['branch_generation']==j['branch_generation']]
    boundary=[x for x in nodes[sid] if jobs[x]['audio_end_sample']==s['F']]
    w=dict(cell=C.name,publication=e,actual_consumer=r,frozen_job=j,actual_result=results[e['job_id']],
        current_canonical=dict(F=s['F'],version=s['version'],P=list(s['P'])),
        actual_predecessors=[dict(job=jobs[x],result=results[x]) for x in prev],
        boundary_nodes=[dict(job=jobs[x],result=results[x]) for x in boundary],
        forward_reachable_job_ids=sorted(legal_jobs),
        adjacent_events=[x for x in events if x.get('session_id')==sid and abs(x['time']-e['time'])<3])
    witnesses.append(w)
assert len(witnesses)==1
out=W/'N1_VISIBLE_WITNESS_FORWARD_v1.json';out.write_text(json.dumps({'status':'PASS_SECOND_FORWARD_GRAPH_CONFIRMATION','witnesses':witnesses},indent=2)+'\n')
for w in witnesses:
    j=w['frozen_job'];e=w['publication'];s=w['current_canonical'];r=w['actual_consumer']
    print(json.dumps({'job':j['job_id'],'source':j['source_id'],'window':j['end_window'],'chunk':j['chunk_id'],
        'birth_parent':j['parent'],'current_parent':s['version'],'F_seconds':s['F']/16000,
        'target_seconds':j['audio_end_sample']/16000,'display_time':e['displayed'],
        'actual_consumer_observed':r['observed'],'visible_frontier':r['valid_visible_frontier']/16000,
        'canonical_frontier':r['certified_frontier']/16000,'input_token_count':len(j['prompt_tokens']),
        'canonical_token_count':len(s['P']),'frozen_input_equals_canonical':j['prompt_tokens']==s['P'],
        'predecessor_text':[x['result']['text'] for x in w['actual_predecessors']],
        'display_text':e['text'],'certified_text':r['certified_text']}))
