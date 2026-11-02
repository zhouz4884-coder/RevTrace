"""Freeze the complete two-source cost matrix from an existing real plan.

Run after Root commits/freezes this observer source. This script does not launch
models, alter CURRENT or create a run record pretending an experiment occurred.
"""
from __future__ import annotations
import argparse
import copy
import pathlib
from cost_common import read, put, sha, NN4F

SOURCES = ('BAC009S0908W0369', 'BAC009S0916W0463')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--paired-plan', required=True)
    p.add_argument('--observer-commit', required=True)
    p.add_argument('--observer-manifest', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--raw-root', required=True)
    args = p.parse_args()
    if len(args.observer_commit) != 40:
        raise ValueError('full resolvable observer commit required')
    original = read(args.paired_plan)
    out, raw = pathlib.Path(args.out), pathlib.Path(args.raw_root)
    out.mkdir(parents=True, exist_ok=False)
    templates = {}
    cpu = []
    for sid in SOURCES:
        for arm in ('conservative', 'fullcall'):
            matched = [c for c in original['cells'] if c['version']=='final' and c['source_id']==sid
                       and c['strategy']==arm and c['repeat']==0]
            if len(matched) != 1:
                raise ValueError('existing complete current two-source stratum missing')
            old = matched[0]
            config = read(old['config'])
            if config['settings']['source_commit'] != NN4F:
                raise ValueError('template is not actual final4f')
            templates[(sid, arm)] = config
            for repeat in range(3):
                cid = f'COST_CPU_REALTRACE_{sid}_{arm}_r{repeat}'
                cpu.append(dict(cell_id=cid, source_id=sid, arm=arm, repeat=repeat,
                                input_raw=old['out'], output=str(raw/'cpu'/cid),
                                original_config_sha256=sha(old['config'])))
    cells = []
    # Every source/arm gets both off/on in each fresh repeat. Reverse the order
    # on repeat1 and rotate policy/source blocks; no result-dependent stopping.
    for repeat in range(2):
        blocks = [(sid, arm) for sid in SOURCES for arm in ('conservative','fullcall')]
        if repeat:
            blocks.reverse()
        for block, (sid, arm) in enumerate(blocks):
            modes = (False, True) if (block+repeat)%2 == 0 else (True, False)
            for enabled in modes:
                cid = f'COST_NN_{sid}_{arm}_{"on" if enabled else "off"}_r{repeat}'
                config = copy.deepcopy(templates[(sid, arm)])
                config.update(cell_id=cid, experiment_id='REVTRACE_CURRENT_PROTOCOL_COST_20261102',
                              repeat=repeat, position=len(cells))
                config['settings']['primary_gpu'] = repeat
                config['cost_observer'] = dict(enabled=enabled,
                    scope='timing_only_same_safety_protocol', observer_source_commit=args.observer_commit)
                path = out/(cid+'.json')
                put(path, config)
                cells.append(dict(cell_id=cid, source_id=sid, arm=arm, repeat=repeat,
                    observation=enabled, primary_gpu=repeat, config=str(path), config_sha256=sha(path),
                    out=str(raw/'normal'/cid)))
    dep = original['dependencies']['final']
    plan = dict(experiment_id='REVTRACE_CURRENT_PROTOCOL_COST_20261102',
        observer_source_commit=args.observer_commit,
        observer_manifest=str(pathlib.Path(args.observer_manifest)),
        observer_manifest_sha256=sha(args.observer_manifest),
        actual_nn_source_commit=NN4F, original_dependency=dep,
        environment_record=original['environment_record'], environment_sha256=original['environment_sha256'],
        environment_python=original['environment_python'], runtime_environment=original['runtime_environment'],
        fixed_sources=list(SOURCES), source_selection='first two original independent-selection records; frozen before cost outcomes',
        original_paired_plan=str(pathlib.Path(args.paired_plan)), original_paired_plan_sha256=sha(args.paired_plan),
        cpu_cases=cpu, expected_cpu_fresh_processes=12, cells=cells, expected_NN_trials=16,
        smoke_scope='first four trials cover two arms and off/on on source S0908; validity gate only, no performance pruning',
        continuation='complete all16 after validity gate; abort only for identity/safety/semantic/resource failure, preserve failures',
        scope='complete-object CPU footprint plus normal NN off/on observation impact; no removal-of-protocol counterfactual',
        original_D2_seconds=2., original_C8_seconds=8., all_offered_and_EOS=True,
        code_and_raw_mutation_forbidden=True)
    put(out/'PLAN.json', plan)
    print(str(out/'PLAN.json'))

if __name__ == '__main__':
    main()

