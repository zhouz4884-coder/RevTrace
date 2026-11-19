"""Frozen three-condition source-paired reversal; no model/GPU imports."""
import random
from confirmation_common import need

WORKLOAD_SEED = 20261119
CONDITIONS = ('conservative_s1', 'r1s0', 'r1s1')
CONDITION_SETTINGS = {
    'conservative_s1': ('conservative', True),
    'r1s0': ('fullcall', False),
    'r1s1': ('fullcall', True),
}

def workload_blocks(sources):
    ordered = sorted(sources, key=lambda s: (s['speaker_id'], s['source_id']))
    rng = random.Random(WORKLOAD_SEED)
    rng.shuffle(ordered)
    orders = {}
    for source in ordered:
        order = list(CONDITIONS)
        rng.shuffle(order)
        orders[source['speaker_id']] = order
    blocks = []
    for repeat in (0, 1):
        for source in (ordered if repeat == 0 else list(reversed(ordered))):
            order = orders[source['speaker_id']]
            blocks.append(dict(source=source, repeat=repeat, primary_gpu=repeat,
                               conditions=order if repeat == 0 else list(reversed(order))))
    return blocks, orders

def validate_matrix(cells, sources):
    need(0 < len(sources) <= 4, 'workload extension requires one to four actual eligible sources')
    need(len({s['source_id'] for s in sources}) == len(sources) ==
         len({s['speaker_id'] for s in sources}), 'duplicate acoustic source or speaker')
    need(len(cells) == 6 * len(sources), 'complete three-condition two-repeat matrix required')
    need(len({c['cell_id'] for c in cells}) == len(cells), 'duplicate cell identity')
    need([c['position'] for c in cells] == list(range(len(cells))), 'frozen positions differ')
    blocks, _ = workload_blocks(sources)
    expected = [(b['source']['source_id'], condition, b['repeat'], b['primary_gpu'])
                for b in blocks for condition in b['conditions']]
    actual = [(c['source_id'], c['condition'], c['repeat'], c['primary_gpu']) for c in cells]
    need(actual == expected, 'seeded source/policy reversal order or GPU rotation differs')
    by_source = {s['source_id']: s for s in sources}
    for cell in cells:
        need(cell['speaker_id'] == by_source[cell['source_id']]['speaker_id'], 'speaker identity differs')
        need(type(cell['consumer_retain_views']) is bool and
             (cell['strategy'], cell['consumer_retain_views']) == CONDITION_SETTINGS[cell['condition']],
             'condition must map to original arm and explicit Boolean S')
    for key in ('config', 'out', 'log', 'external_power'):
        need(len({c[key] for c in cells}) == len(cells), 'duplicate cell '+key+' path')
    return True
