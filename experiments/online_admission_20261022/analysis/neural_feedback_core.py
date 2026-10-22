"""Read-only provenance classification; never regenerates any model output."""
import hashlib


def token_digest(tokens):
    # Must match frozen revtrace.dgft.digest_tokens, independently tested below.
    return hashlib.sha256(','.join(str(int(x)) for x in tokens).encode('ascii')).hexdigest()


def actually_ran_neural_model(record):
    r = record['result']
    a, b = r.get('model_started_perf'), r.get('model_completed_perf')
    proof = r.get('online_verification')
    if proof:
        return any(p['completed_perf'] > p['started_perf'] for p in proof.get('phases', []))
    return a is not None and b is not None and b > a


def canonical_root_chain(record, root, records):
    """Return witnessed proposal IDs, or reason it is not post-install root use.

    root: session_id/version/frontier/P/installed_perf. Excludes merely equal
    strings under a different logical parent and jobs issued before installation.
    Does not claim the root P is erroneous or that output differences are harmful.
    """
    job = record['job']
    if job['role'] != 'proposal' or not actually_ran_neural_model(record):
        return None, 'not_a_real_proposer_generation'
    if job['session_id'] != root['session_id']:
        return None, 'different_session'
    if job['enqueue_perf'] < root['installed_perf']:
        return None, 'issued_before_installation'
    if job['parent'] != root['version'] or job['parent_prompt_digest'] != token_digest(root['P']):
        return None, 'different_committed_root'
    if job['audio_start_sample'] != root['frontier'] or job['audio_end_sample'] <= root['frontier']:
        return None, 'different_or_covered_root_frontier'
    current = record; seen = set(); witness = []
    while current['job']['job_id'] not in seen:
        j, r = current['job'], current['result']; seen.add(j['job_id']); witness.append(j['job_id'])
        if 'fault_actual_prompt_tokens' in j:
            return None, 'actual_context_override_in_descendant'
        if j['prompt_tokens'] == root['P']:
            return list(reversed(witness)), 'direct_root' if len(witness) == 1 else 'witnessed_private_descendant'
        predecessors = [p for p in records if p['job']['role'] == 'proposal'
            and p['job']['session_id'] == root['session_id']
            and p['job']['parent'] == root['version']
            and p['job']['parent_prompt_digest'] == token_digest(root['P'])
            and p['job']['audio_start_sample'] == root['frontier']
            and p['job'].get('branch_generation') == j.get('branch_generation')
            and p['job']['end_window'] == j['chunk_id']
            and p['job']['audio_end_sample'] < j['audio_end_sample']
            and p['result']['state_tokens'] == j['prompt_tokens']
            and p['result']['received_perf'] <= j['enqueue_perf']
            and p['job']['enqueue_perf'] >= root['installed_perf']
            and actually_ran_neural_model(p)]
        if len(predecessors) != 1:
            return None, 'ambiguous_or_missing_causal_predecessor'
        current = predecessors[0]
    return None, 'cycle'
