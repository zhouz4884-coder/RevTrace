"""CPU-only controller/schema/raw-book controls; no new model experiment."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import csv
import subprocess
import sys

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE/'runtime/src'), str(HERE/'runtime/tests')]

from run_closed_stage import validate_plan, cell_name, confined, save, STUDY
from audit_closed_helpers import audit_closed_events, distribution, finite_tree, same
from revtrace.ces_closed_loop import PlannerConfig
from revtrace.ces_runtime import CESScheduler
from revtrace.certified_display import ContinuityView, ConsumerAck
from revtrace.dgft import digest_tokens
from revtrace.live_qwen import fingerprint
from test_ces import CAL, EvidenceFake
from test_live_qwen import Clock


def plan_fixture():
    values = dict(study_id=STUDY, implementation_gates_complete=True,
        independent_confirmation=False, output_relative='results/revtrace/ces_v5_closed_loop_20261025',
        cpu_gate_files=[{'path': 'CPU.xml', 'sha256': 'a'*64}],
        runtime_commit='b'*40, runtime_manifest_sha256='a'*64,
        manifest_sha256='a'*64, calibration_sha256='a'*64,
        closed_config_sha256='a'*64, protocol_sha256='a'*64, donors_sha256='a'*64)
    cells = [{'label': method, 'method': method, 'arrival': arrival,
        'sessions': 8, 'repeat': 0, 'seed': 20261025, 'traffic': 'mixed',
        'proposer_policy': 'shared_progress'} for arrival in ('sync', 'staggered') for method in ('fine', 'causal')]
    oracles = [{'label': 'strict_oracle', 'method': 'strict', 'arrival': 'staggered',
        'sessions': 4, 'repeat': 0, 'seed': 20261025, 'traffic': traffic,
        'proposer_policy': 'ready', 'oracle': True} for traffic in ('clean', 'mixed')]
    values['stages'] = {'smoke': {'cells': cells, 'oracles': oracles, 'expected_repeats': 1}}
    return values


def cpu_trace(mode='causal'):
    clk = Clock()
    view = ContinuityView('two_lane', strict_bound=True)
    pending = []
    cfg = {'policy': 'fine_certified', 'rho': 1, 'fine_seconds': 2, 'sample_rate': 16000,
        'authority_runtime': {'dtype': 'float32', 'max_new_tokens': 1},
        'proposal_runtime': {'dtype': 'float16'}, 'microbatch': 2,
        'timeout_seconds': 20, 'proposal_barrier': 'decoupled', 'proposal_reconciliation': 'lazy',
        'verification_policy': 'causal_evidence_choice', 'journal_sync_mode': 'group_ready',
        'display_protocol': 'canonical-snapshot-v1', 'trusted_text_binding': True,
        'publish_canonical_display': True, 'capture_worker_records': True,
        'evidence_type': 'cpu_fixture_only',
        'ces_study': {'method': mode, 'calibration': deepcopy(CAL), 'fault_plan': {},
            'donors': [], 'display_slo': 2., 'commit_slo': 8., 'wait_cap': 0.,
            'closed_loop_config': asdict(PlannerConfig())}}

    def render(job, tokens):
        return list(tokens), str(tokens[0])

    class Worker(EvidenceFake):
        def poll(self):
            rows = super().poll()
            for result in rows or []:
                result.update(state_tokens=list(result['token_ids']), text=str(result['token_ids'][0]))
            return rows

    def emit(event):
        row = view.consume(event, clk())
        if row:
            pending.append(ConsumerAck(len(view.records), view.epoch, view.contract,
                row['session_id'], row['canonical_epoch'], row['canonical_version'],
                row['valid_visible_frontier'], row['certified_frontier'], clk()))

    def drain():
        rows = tuple(pending)
        pending.clear()
        return rows

    specs = [{'session_id': i, 'source_id': str(i), 'audio': np.zeros(96000, dtype='<f4').tobytes(),
        'offset': i*.05, 'language': 'English'} for i in range(2)]
    owner = CESScheduler(sessions=specs, contract=cfg,
        executors={'proposal': [Worker('p', clk)], 'authority': [Worker('a', clk)]},
        clock=clk, sleep=clk.sleep, emit=emit, trusted_render=render, consumer_ack_source=drain)
    initial = [{'session_id': s.sid, 'state': asdict(s.state)} for s in owner.sessions.values()]
    sessions = [{k: v for k, v in s.items() if k != 'audio'} | {'duration': len(s['audio'])/64000}
                for s in specs]
    result = owner.run()
    events = json.loads(json.dumps(owner.events))  # Exact JSONL tuple/list realization.
    records = [{'job': e['job'], 'result': e['result']} for e in events if e['kind'] == 'worker-record']
    actual_cfg = deepcopy(owner.contract)
    owner.close()
    return actual_cfg, events, records, sessions, initial, render, result


def audit_trace(trace):
    cfg, es, rs, ss, initial, render, _ = trace
    return audit_closed_events(cfg, es, rs, ss, initial, trusted_render=render,
        digest_tokens=digest_tokens, fingerprint=fingerprint)


def test_smoke_schema_freezes_six_separate_real_controls():
    spec = validate_plan(plan_fixture(), 'smoke')
    assert len(spec['cells']) == 4 and len(spec['oracles']) == 2
    assert len({cell_name(x) for x in spec['cells']+spec['oracles']}) == 6


def test_explicit_proposal_lists_48_ready_main_and_24_single_factor_side_cells():
    plan = json.loads((HERE/'PLAN.example.json').read_text(encoding='utf8'))
    cells = plan['stages']['formal']['cells']
    main = [x for x in cells if not x.get('side_arm')]
    side = [x for x in cells if x.get('side_arm')]
    assert len(main) == 48 and len(side) == 24 and len(cells) == 72
    assert all(x['proposer_policy'] == 'ready' for x in main)
    assert {x['label'] for x in side} == {'fine_shared_progress', 'standard_shared_progress', 'cost_joint', 'causal_joint'}
    assert not plan['implementation_gates_complete'] and not plan['formal_approved_after_smoke']
    # Schema-only enablement below does not verify hashes or run a model.
    plan['implementation_gates_complete'] = True
    plan['formal_approved_after_smoke'] = True
    assert len(validate_plan(plan, 'formal')['cells']) == 72


@pytest.mark.parametrize('mutation', ['wrongstudy', 'nofreeze', 'oldpath', 'missingoracle',
    'mismatchseed', 'undeclaredjoint', 'duplicate', 'smokebloat'])
def test_controller_rejects_invalid_or_unfair_frozen_scope(mutation):
    plan = plan_fixture()
    if mutation == 'wrongstudy': plan['study_id'] = 'old-v5'
    if mutation == 'nofreeze': plan['implementation_gates_complete'] = False
    if mutation == 'oldpath': plan['output_relative'] = 'results/revtrace/ces_v5_20261025'
    if mutation == 'missingoracle': plan['stages']['smoke']['oracles'].pop()
    if mutation == 'mismatchseed': plan['stages']['smoke']['cells'][0]['seed'] += 1
    if mutation == 'undeclaredjoint': plan['stages']['smoke']['cells'][0]['proposer_policy'] = 'causal_joint'
    if mutation == 'duplicate': plan['stages']['smoke']['cells'][1] = deepcopy(plan['stages']['smoke']['cells'][0])
    if mutation == 'smokebloat': plan['stages']['smoke']['cells'].append(deepcopy(plan['stages']['smoke']['cells'][0]))
    with pytest.raises(ValueError):
        validate_plan(plan, 'smoke')


def test_formal_requires_a_separate_explicit_post_smoke_freeze():
    plan = plan_fixture()
    plan['stages']['formal'] = {'cells': plan['stages']['smoke']['cells']}
    with pytest.raises(ValueError, match='explicit'):
        validate_plan(plan, 'formal')
    plan['formal_approved_after_smoke'] = True
    for row in plan['stages']['formal']['cells']:
        row['proposer_policy'] = 'ready'
    assert validate_plan(plan, 'formal')['cells']


def test_local_artifact_write_refuses_overwrite_and_escape(tmp_path):
    save(tmp_path/'freeze.json', {'fixture': True})
    with pytest.raises(FileExistsError):
        save(tmp_path/'freeze.json', {'fixture': False})
    with pytest.raises(ValueError):
        confined(tmp_path, '../old-study')


@pytest.mark.parametrize('mode', ['service_cost', 'reserved_progress', 'inherit', 'causal'])
def test_actual_cpu_owner_trace_replays_service_and_parent_identity(mode):
    trace = cpu_trace(mode)
    result = audit_trace(trace)
    assert result['closed_observations'] == result['physical_service_dispatches']
    assert result['actual_commit_retirements'] == 6
    assert result['residual_service_records'] == 0
    assert trace[-1]['fine_window_accounting_complete']


@pytest.mark.parametrize('mutation', ['parent', 'contract', 'unreleased', 'cdf', 'book', 'duplicate_dispatch'])
def test_raw_trace_tampering_is_not_a_planner_success(mutation):
    trace = list(cpu_trace('causal'))
    es = trace[1]
    observation = next(e for e in es if e['kind'] == 'closed-loop-observation')
    context = next(iter(observation['contexts'].values()))
    if mutation == 'parent':
        context['identity']['parent_digest'] = 'untrusted'
        context['target_context']['identity']['parent_digest'] = 'untrusted'
    if mutation == 'contract':
        context['identity']['contract_digest'] = 'wrong'
        context['target_context']['identity']['contract_digest'] = 'wrong'
    if mutation == 'unreleased':
        context['target_context']['successors'].append({'bad': 'unreleased-context-is-not-schema'})
    if mutation == 'cdf':
        context['target_context']['private_delay_distribution'] = [[1., float('nan')]]
    if mutation == 'book':
        observation['service_book']['actual_dispatches'] += 1
    if mutation == 'duplicate_dispatch':
        index = next(i for i, e in enumerate(es) if e['kind'] == 'closed-loop-service-dispatch')
        es.insert(index+1, deepcopy(es[index]))
    with pytest.raises((AssertionError, ValueError, TypeError)):
        audit_trace(trace)


def test_cdf_and_scheduler_features_reject_future_or_invalid_labels():
    with pytest.raises(AssertionError): distribution([[.5, .1]])
    with pytest.raises(AssertionError): finite_tree({'fault_label': 'F2'})


def test_token_limit_boundary_is_not_an_admission_failure_filter():
    trace = cpu_trace('causal')
    for rec in trace[2]:
        rec['result']['hit_token_limit'] = True
    result = audit_trace(trace)
    assert result['TOKEN_LIMIT_BOUNDARY_is_not_admission_failure']
    assert result['actual_commit_retirements'] == 6


def test_shared_gpu0_policy_is_not_silently_exclusive_to_causal():
    plan = plan_fixture()
    plan['stages']['smoke']['cells'][1]['proposer_policy'] = 'ready'
    with pytest.raises(ValueError, match='shared physical Proposer'):
        validate_plan(plan, 'smoke')


def test_joint_gpu0_capability_is_available_to_cost_reference_side_arm():
    plan = plan_fixture()
    plan['formal_approved_after_smoke'] = True
    common = {'sessions': 16, 'arrival': 'sync', 'traffic': 'mixed', 'repeat': 0, 'seed': 20261025}
    main = [{'label': method, 'method': method, 'proposer_policy': 'ready', **common}
        for method in ('fine', 'standard', 'cost', 'strict', 'service_cost', 'reserved_progress', 'inherit', 'causal')]
    side = {'label': 'cost_joint', 'method': 'cost', 'proposer_policy': 'causal_joint',
            'side_arm': True, **common}
    plan['stages']['formal'] = {'cells': main+[side]}
    assert len(validate_plan(plan, 'formal')['cells']) == 9
    plan['stages']['formal']['cells'][-1]['seed'] += 1
    with pytest.raises(ValueError):
        validate_plan(plan, 'formal')


@pytest.mark.parametrize('method,policy', [('fine', 'shared_progress'),
    ('standard', 'shared_progress'), ('cost', 'causal_joint'), ('causal', 'causal_joint')])
def test_each_new_gpu0_capability_has_a_matched_strong_reference_side_arm(method, policy):
    plan = plan_fixture()
    plan['formal_approved_after_smoke'] = True
    common = {'sessions': 16, 'arrival': 'sync', 'traffic': 'mixed', 'repeat': 0, 'seed': 20261025}
    main = {'label': method, 'method': method, 'proposer_policy': 'ready', **common}
    side = {'label': method+'_new_gpu0', 'method': method, 'proposer_policy': policy,
            'side_arm': True, **common}
    plan['stages']['formal'] = {'cells': [main, side]}
    assert len(validate_plan(plan, 'formal')['cells']) == 2
    plan['stages']['formal']['cells'][-1]['unshared_execution_option'] = True
    with pytest.raises(ValueError, match='only in label'):
        validate_plan(plan, 'formal')


def test_json_session_key_normalization_covers_sixteen_sessions():
    same({i: {'test': i} for i in range(16)}, {str(i): {'test': i} for i in range(16)},
         'JSON key realization differs')


def test_reference_cannot_secretly_use_closed_observation_book():
    cfg, es, rs, ss, initial, render, _ = cpu_trace('fine')
    assert audit_closed_events(cfg, es, rs, ss, initial, trusted_render=render,
        digest_tokens=digest_tokens, fingerprint=fingerprint)['closed_observations'] == 0
    es.append({'kind': 'closed-loop-observation'})
    with pytest.raises(AssertionError, match='Baseline secretly'):
        audit_closed_events(cfg, es, rs, ss, initial, trusted_render=render,
            digest_tokens=digest_tokens, fingerprint=fingerprint)


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_single_repeat_summary_does_not_turn_smoke_into_superiority(tmp_path):
    audit = tmp_path/'fixture_audit'
    audit.mkdir()
    (audit/'SUMMARY.json').write_text(json.dumps({'expected_cells': 2, 'failures': [],
        'source_scope': 'CPU summary fixture only; no GPU inference'}), encoding='utf8')
    rows = []
    fronts = []
    quality = []
    for method in ('fine', 'causal'):
        name = f'validation-sync-mixed-{method}-r0'
        rows.append({'cell': name, 'method': method, 'wall_seconds': 3.,
            'Audio_Goodput_2_8': 2/3, 'Audio_Goodput_certified_consumer_2_8': 2/3,
            'Audio_Goodput_stable_2_8': 2/3, 'display_P99': 1., 'commit_P99': 1.,
            'GPU_J_audio_s': 5., 'WER': 0., 'CER': 0., 'dual_P99_2_8_pass': True})
        fronts.append({'cell': name, 'source_id': 'cpu-fixture', 'audio_seconds': 2.,
            'display': 1., 'commit': 1., 'stable_display': 1., 'certified_consumer': 1.})
        quality.append({'cell': name, 'source_id': 'cpu-fixture', 'WER_errors': 0,
            'reference_words': 10, 'CER_errors': 0, 'reference_characters': 20})
    write_csv(audit/'SERVICE_CELLS.csv', rows)
    write_csv(audit/'COMMON_FRONTIERS.csv', fronts)
    write_csv(audit/'SOURCE_QUALITY.csv', quality)
    output = tmp_path/'fixture_summary'
    subprocess.run([sys.executable, str(HERE/'summarize_closed.py'), '--audit', str(audit),
        '--output', str(output), '--samples', '2', '--expected-repeats', '1'], check=True,
        capture_output=True, text=True)
    result = json.loads((output/'PAIRED_SUMMARY.json').read_text())
    assert not result['performance_decision_eligible']
    assert result['one_repeat_smoke_is_safety_feasibility_not_superiority']
    complete = [x for x in result['comparisons'] if 'metrics' in x]
    assert complete and all('NO_SUPERIORITY_CLAIM' in x['status'] for x in complete)
    assert (output/'GROUPS.csv').is_file()
