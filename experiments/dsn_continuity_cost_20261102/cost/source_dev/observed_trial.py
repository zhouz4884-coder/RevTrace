"""Normal actual-NN off/on observation control, not a protocol-removal arm."""
from __future__ import annotations
import argparse
import hashlib
import os
import pathlib
import sys
from cost_common import bind_base, read, put, verify_observer
from cost_probe import CostProbe

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base-source', required=True)
    p.add_argument('--base-manifest', required=True)
    p.add_argument('--observer-manifest', required=True)
    p.add_argument('--config', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    identity = bind_base(args.base_source, args.base_manifest)
    config = read(args.config)
    if config.get('fault', {}).get('kind') != 'none':
        raise ValueError('frozen cost matrix is normal service, no fault injection')
    if config['settings']['source_commit'] != identity['actual_nn_source']:
        raise ValueError('observer cannot relabel the original NN4f source')
    observer = config['cost_observer']
    if type(observer['enabled']) is not bool or observer['scope'] != 'timing_only_same_safety_protocol':
        raise ValueError('invalid instrumentation control')
    observation_identity=verify_observer(args.observer_manifest,observer['observer_source_commit'])
    # Import the external clean original tree, not the archival vendor copy.
    import resilience_trial
    import cost_runtime
    resilience_trial.owner_main = cost_runtime.observed_owner
    probe = CostProbe(pathlib.Path(args.out)/'cost_spans', 'supervisor_consumer', observer['enabled']).install()
    try:
        result = resilience_trial.run_trial(args.config, args.base_manifest, args.out)
    finally:
        probe.close()
    owner_summaries=list((pathlib.Path(args.out)/'cost_spans').glob('owner_pid*_SUMMARY.json'))
    if len(owner_summaries)!=1:
        raise RuntimeError('normal cost trial must retain exactly one Owner observer export')
    owner_summary=read(owner_summaries[0])
    if owner_summary['enabled']!=observer['enabled'] or owner_summary['overflow']:
        raise RuntimeError('Owner observation mode/export invalid')
    if observer['enabled']:
        required={'OWNER.receive_validate_select','AU.durable_selected_commit',
                  'AU.validate_original_C_U_and_parent','WAL.complete_fact_commit','IO.actual_os_fsync'}
        if not required.issubset(owner_summary['families']):
            raise RuntimeError('actual Owner protocol timing coverage missing')
        if 'SUP.complete_consumer_apply' not in {r['label'] for r in probe.rows}:
            raise RuntimeError('actual complete Consumer timing missing')
    elif owner_summary['span_count'] or probe.rows:
        raise RuntimeError('off control unexpectedly captured spans')
    put(pathlib.Path(args.out)/'COST_OBSERVER_IDENTITY.json', dict(
        **identity, **observation_identity, observer_enabled=observer['enabled'],
        safety_predicates_unchanged=True, original_NN_C_U_executed=True,
        scope='off/on changes observation only; not counterfactual protocol net overhead',
        cost_export_after_original_trial_return=True))
    return result

if __name__ == '__main__':
    main()

