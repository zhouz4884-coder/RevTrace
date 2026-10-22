"""Exact adapter-state ancestry, not string/token-audio alignment or KV reuse."""
def eligible_chain(s,jobs,results):
    root_window=s.segment_end;P=tuple(s.state.prompt_tokens);generation=s.branch_generation
    first=results.get((s.sid,root_window))
    if first is None:return False,'no-private-node-at-certified-boundary'
    j0=jobs[first['job_id']]
    if j0['session_id']!=s.sid or j0['audio_end_sample']!=s.state.audio_frontier_window or j0['audio_start_sample']>s.state.audio_frontier_window:return False,'wrong-certified-boundary'
    if tuple(first['state_tokens'])!=P:return False,'boundary-projection-mismatch'
    if j0.get('branch_generation')!=generation:return False,'boundary-generation-mismatch'
    if s.branch_chunk<root_window:return False,'branch-not-at-boundary'
    cursor=root_window;path=[j0['job_id']]
    for (sid,w),r in sorted(results.items()):
        if sid!=s.sid or not (root_window<w<=s.branch_chunk):continue
        j=jobs[r['job_id']]
        if j.get('branch_generation')!=generation:continue
        if j['chunk_id']!=cursor or tuple(j['prompt_tokens'])!=P:return False,'broken-private-state-edge'
        cursor=w;P=tuple(r['state_tokens']);path.append(j['job_id'])
    if cursor!=s.branch_chunk or P!=tuple(s.branch_tokens):return False,'branch-tip-not-reached'
    pending=[j for j in jobs.values() if j['role']=='proposal' and j['session_id']==s.sid and j.get('branch_generation')==generation and j['end_window']==s.fine_window]
    if s.fine_busy:
        if len(pending)!=1:return False,'inflight-not-unique'
        j=pending[0]
        if j['chunk_id']!=cursor or tuple(j['prompt_tokens'])!=P:return False,'frozen-inflight-input-not-descendant'
        if j['audio_end_sample']<=s.state.audio_frontier_window:return False,'inflight-target-already-covered'
    return True,tuple(path)
