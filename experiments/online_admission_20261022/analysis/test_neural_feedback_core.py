"""CPU fixtures: processing-only, pre-issued and real post-install work differ."""
import copy
import os
import sys
from pathlib import Path
from neural_feedback_core import actually_ran_neural_model, canonical_root_chain, token_digest


def example():
    root = {'session_id': 0, 'version': 2, 'frontier': 160000, 'P': [1, 2], 'installed_perf': 10.}
    j = {'job_id': 'p1', 'role': 'proposal', 'session_id': 0, 'parent': 2,
         'parent_prompt_digest': token_digest(root['P']), 'audio_start_sample': 160000,
         'audio_end_sample': 192000, 'enqueue_perf': 11., 'prompt_tokens': [1, 2],
         'chunk_id': 5, 'end_window': 6, 'branch_generation': 3}
    return root, {'job': j, 'result': {'state_tokens': [3, 4], 'model_started_perf': 11.1,
                                      'model_completed_perf': 11.8, 'received_perf': 12.}}


def test_digest_matches_frozen_primitive():
    sys.path.insert(0, str(Path(os.environ.get('NEURAL_AUDIT_RUNTIME', str(Path(__file__).with_name('runtime')))) / 'src'))
    from revtrace.dgft import digest_tokens
    for tokens in [[], [1], [1, 2, 151645]]:
        assert token_digest(tokens) == digest_tokens(tokens)


def test_prepared_target_is_not_neural_generation():
    root, r = example(); r['job']['role'] = 'authority'
    r['result'].update(model_started_perf=None, model_completed_perf=None,
                       online_verification={'mode': 'unprotected', 'phases': []})
    assert not actually_ran_neural_model(r)
    assert canonical_root_chain(r, root, [r])[0] is None


def test_direct_post_install_consumption():
    root, r = example()
    assert canonical_root_chain(r, root, [r]) == (['p1'], 'direct_root')


def test_preissued_private_equality_is_not_canonical_consumption():
    root, r = example(); r['job']['enqueue_perf'] = 9.
    assert canonical_root_chain(r, root, [r])[1] == 'issued_before_installation'


def test_equal_bytes_under_wrong_parent_are_not_root_identity():
    root, r = example(); r['job']['parent'] = 1
    assert canonical_root_chain(r, root, [r])[1] == 'different_committed_root'


def test_full_private_causal_chain_required():
    root, a = example(); b = copy.deepcopy(a)
    b['job'].update(job_id='p2', prompt_tokens=[3, 4], chunk_id=6, end_window=7,
                    audio_end_sample=224000, enqueue_perf=13.)
    b['result'].update(model_started_perf=13.1, model_completed_perf=13.8, received_perf=14., state_tokens=[5, 6])
    assert canonical_root_chain(b, root, [a, b]) == (['p1', 'p2'], 'witnessed_private_descendant')
    a['job']['branch_generation'] = 9
    assert canonical_root_chain(b, root, [a, b])[0] is None
