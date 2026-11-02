"""Current-protocol CPU footprint on complete real NN4f trace objects.

Replays original durable transitions and FIFO whole-view publications through
the unchanged FactStore and SurvivorConsumer, including actual fsync. Independent
complete-input / owned-call binding probes are reported separately. No scheduler,
model, arrival process, recovery speed or serving deadline is simulated here.
"""
from __future__ import annotations
import argparse
import copy
import os
import pathlib
from cost_common import bind_base, read, put, jsonl, sha, NN4F, verify_observer
from cost_probe import CostProbe

def semantic(row):
    return {k: v for k, v in row.items() if k != 'observed'}

def run(args):
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('CPU replay requires explicitly empty CUDA_VISIBLE_DEVICES')
    identity = bind_base(args.base_source, args.base_manifest)
    observation_identity=verify_observer(args.observer_manifest)
    from feedback_contract import FeedbackCut
    from resilience_storage import FactStore, scan
    from resilience_consumer import SurvivorConsumer
    from stage_policy import StageCoordinator
    raw, out = pathlib.Path(args.raw), pathlib.Path(args.out)
    config = read(raw/'CONFIG.json')
    if config['settings']['source_commit'] != NN4F or config.get('fault', {}).get('kind') != 'none':
        raise ValueError('only complete normal NN4f traces in the frozen CPU matrix')
    if any(p.name.startswith('owner_e') and p.name != 'owner_e0' for p in raw.iterdir() if p.is_dir()):
        raise ValueError('this normal trace replay does not model recovery epochs')
    names = ['CONFIG.json', 'GENESIS.json', 'facts.wal', 'publications.jsonl', 'consumer.jsonl',
             'consumer_rejections.jsonl', 'owner_e0/dispatch.jsonl', 'owner_e0/worker_results.jsonl']
    before = {name: dict(bytes=(raw/name).stat().st_size, sha256=sha(raw/name)) for name in names}
    out.mkdir(exist_ok=False, parents=True)
    originals = list(scan(raw/'facts.wal'))
    if originals[0][0]['kind'] != 'genesis':
        raise ValueError('real trace missing original durable genesis')
    genesis = originals[0][0]['body']
    initials = read(raw/'GENESIS.json')
    if genesis['initials'] != initials:
        raise ValueError('trace genesis mismatch')
    # Full original objects are loaded before timing. CPU/file access to the
    # original trace is not confused with protocol cost or fresh model work.
    pubs = list(jsonl(raw/'publications.jsonl'))
    expected = list(jsonl(raw/'consumer.jsonl'))
    rejected = list(jsonl(raw/'consumer_rejections.jsonl'))
    if rejected:
        raise ValueError('normal cost scope requires no rejected publication')
    dispatch = list(jsonl(raw/'owner_e0/dispatch.jsonl'))
    messages = list(jsonl(raw/'owner_e0/worker_results.jsonl'))
    probe = CostProbe(out/'cost_spans', 'cpu_real_trace', True).install()
    store = consumer = None
    try:
        store = FactStore(out/'facts.wal', initials, genesis['metadata'])
        receipts = {1: store.last_receipt}
        for obj, oldreceipt in originals[1:]:
            receipt = store.commit(copy.deepcopy(obj['body']))
            if any(receipt[k] != oldreceipt[k] for k in ('sequence', 'record_sha256', 'offset', 'end_offset')):
                raise ValueError('real transition replay changed durable bytes or order')
            receipts[receipt['sequence']] = receipt
        store.close()
        store = None
        if sha(out/'facts.wal') != before['facts.wal']['sha256']:
            raise ValueError('whole original journal differs after complete-object replay')
        consumer = SurvivorConsumer(initials, out/'consumer.jsonl', out/'consumer_rejections.jsonl', out/'facts.wal')
        consumer.begin_owner(0)
        applied = []
        for row in pubs:
            if row['bound_owner_epoch'] != 0:
                raise ValueError('unexpected publication namespace')
            result = consumer.apply(copy.deepcopy(row['event']), row['bound_owner_epoch'])
            if not result['applied']:
                raise ValueError('recorded normal publication rejected on replay')
            applied.append(result['row'])
        consumer.close()
        consumer = None
        if len(applied) != len(expected) or [semantic(x) for x in applied] != [semantic(x) for x in expected]:
            raise ValueError('complete actual Consumer semantic snapshots changed')
        # These probes use full frozen jobs and events but do not pretend to
        # reconstruct the original live Owner's scheduling/history occupancy.
        jobs = {}
        for row in dispatch:
            job = copy.deepcopy(row['job'])
            job['start'] = FeedbackCut(job['start'])
            jobs[job['job_id']] = job
        identity_context = StageCoordinator.__new__(StageCoordinator)
        identity_context.jobs = jobs
        bindings = 0
        for row in messages:
            event = row['event']
            if event.get('kind') in ('asr_early', 'completed', 'abandoned'):
                identity_context.bind(row['physical_slot'], event)
                bindings += 1
        pairs = []
        def complete_input_pair(left, right):
            return FeedbackCut(left).same(FeedbackCut(right))
        class Probes:
            compare = staticmethod(complete_input_pair)
        probe.wrap(Probes, 'compare', 'REPLAY_COMPONENT.full_input_materialize_and_equal')
        for obj, _ in originals[1:]:
            b = obj['body']
            pairs.append(Probes.compare(b['job']['start'], b['parent_state']))
        if not all(pairs):
            raise ValueError('original installed job lacks actual selected full input')
    finally:
        if consumer is not None:
            consumer.close()
        if store is not None:
            store.close()
        probe.close()
    after = {name: dict(bytes=(raw/name).stat().st_size, sha256=sha(raw/name)) for name in names}
    if after != before:
        raise ValueError('immutable real trace bytes changed during CPU replay')
    put(out/'SUMMARY.json', dict(**identity, **observation_identity, raw=str(raw),
        original_config_sha256=before['CONFIG.json']['sha256'], input_files=before,
        original_and_replayed_facts_sha256=sha(out/'facts.wal'),
        original_selected_transitions=len(originals)-1, actual_publications=len(pubs),
        actual_consumer_rows=len(expected), owned_binding_probes=bindings,
        complete_input_pair_probes=len(pairs), original_inputs_unchanged=True,
        actual_fsync_enabled=True, filesystem_cache_state='uncontrolled; fresh output files, not cold filesystem',
        no_neural_calls=True, no_model_initialization=True,
        scope='real complete-object CPU footprint; not live Owner scheduling or serving results',
        original_C_U='recorded complete original result validated; neural C/U computation not executed',
        components_not_added_to_derive_end_to_end_cost=True))
    put(out/'GATE.json', dict(decision='PASS_REAL_COMPLETE_OBJECT_FACT_AND_CONSUMER_REPLAY',
        protocol_removal_counterfactual=False, serving_claim=False))

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base-source', required=True)
    p.add_argument('--base-manifest', required=True)
    p.add_argument('--observer-manifest', required=True)
    p.add_argument('--raw', required=True)
    p.add_argument('--out', required=True)
    run(p.parse_args())

if __name__ == '__main__':
    main()
