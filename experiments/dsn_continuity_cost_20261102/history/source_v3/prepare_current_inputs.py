"""Prepare latecore references and current-bank raw identity map, no raw scan."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from prepare_inputs import extracted


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    if (source / '.git').exists():
        raise RuntimeError('Prepare before freezing; refusing to rewrite an execution checkout')
    late = args.repo/'experiments/physical_retirement_20261028/source_v3/runtime/src/revtrace'
    header = ('"""Verbatim latecore CPU reference definitions; see LATECORE_PROVENANCE.json."""\n'
              'from __future__ import annotations\n'
              'import hashlib, json, time, queue, threading, re, heapq\n'
              'from hashlib import sha256\nfrom typing import Sequence\n')
    pieces, provenance = [], []
    for filename, names in [('dgft.py',['digest_tokens']),
                            ('certified_display.py',['text_sha','ContinuityView']),
                            ('envelope_display.py',['EnvelopeView'])]:
        path = late/filename
        pieces.append(extracted(path.read_text(encoding='utf-8'), names))
        provenance.append(dict(path=str(path.relative_to(args.repo)), sha256=sha(path),
                               extracted_definitions=names))
    (source/'reference_latecore_view.py').write_text(header+'\n\n'.join(pieces)+'\n', encoding='utf-8')
    (source/'reference_latecore_kernel.py').write_bytes((late/'composed_kernel.py').read_bytes())
    provenance.append(dict(path=str((late/'composed_kernel.py').relative_to(args.repo)),
                           sha256=sha(late/'composed_kernel.py'), copied_verbatim='reference_latecore_kernel.py'))
    (source/'LATECORE_PROVENANCE.json').write_text(json.dumps(dict(entries=provenance,
        scope='Current f0 execution carrier definitions; raw source identity is independently checked per config'),indent=2)+'\n')
    banks = [
        ('current_confirm','experiments/physical_retirement_20261028/H3_RESULTS_v2/aggregate',110),
        ('current_stability','experiments/dsn_service_stability_20261028/RESULTS_v1/aggregate',36),
        ('current_midpoint','experiments/dsn_midpoint_continuity_20261029/RESULTS_v1/core/aggregate',12),
    ]
    entries, input_banks = [], []
    for bank, relative, expected in banks:
        root = args.repo/relative
        coverage = json.loads((root/'COVERAGE.json').read_text())
        metrics = {row['cell_id']:row for row in json.loads((root/'RUNS.json').read_text())}
        record = json.loads((root/'ANALYSIS_RECORD.json').read_text())
        if len(coverage) != expected:
            raise RuntimeError('Current frozen bank denominator changed')
        input_banks.append(dict(bank=bank, expected_cells=expected,
            metadata=[dict(path=str((root/name).relative_to(args.repo)),sha256=sha(root/name))
                      for name in ['COVERAGE.json','RUNS.json','ANALYSIS_RECORD.json']]))
        for ordinal, row in enumerate(coverage):
            data = metrics[row['cell_id']]
            base = row['path']+'/attempt0/'
            identities = []
            for role in ['events.jsonl','consumer.jsonl','worker_records.jsonl','config.json','sessions.json','result.json']:
                path = base+role
                identity = record['inputs'].get(path)
                if identity is None:
                    raise RuntimeError('Missing frozen original raw identity: '+path)
                identities.append(dict(path=path,**identity))
            policy = data['confirmation_consumer']
            s_on = policy == 'two_lane'
            if policy not in ('two_lane','checked_snapshot'):
                raise RuntimeError('Unmodeled current Consumer contract')
            entries.append(dict(bank=bank, ordinal=ordinal, attempt=base.rstrip('/'),
                cell_id=row['cell_id'], arm=row['arm'], stage=row['phase'], controlled=False,
                cell={key:row.get(key) for key in ['adapter','rho','arrival','cohort','repeat','paired_block']},
                original_status=row['status'], original_point_opportunities=None,
                expected_execution_commit=row['source_commit'], reference_family='latecore', reference_policy=policy,
                actual_S_on=s_on, actual_R_on=data['retain_verified_private_prefix'],
                trace_identity=identities))
    manifest = dict(schema=1, input_banks=input_banks, attempts=entries,
        expected_attempts=158, expected_S_on_attempts=90,
        primary_denominator='90 actual S-on cells: confirm66+stability18+midpoint6; S-off68 are explicitly separate controls',
        raw_root='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/physical_retirement_20261028',
        source_alias_rule='Use accepted COVERAGE.path and original argv-resolved attempt0, never old frozen out alias',
        independent_source_scope='The banks reuse development/confirmation sources; cells/windows are not new independent speakers')
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'CURRENT_BANK_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    config = json.loads((args.out/'CONFIG.json').read_text())
    config.update(experiment_id='REVTRACE-H3-CURRENT-S-RESIDUAL-CONTINUITY-20261102-V1',
        expected_attempts=dict(current_confirm=110,current_stability=36,current_midpoint=12),
        expected_S_on_attempts=90, expected_original_point_cuts='UNKNOWN_NOT_PREASSUMED_ZERO',
        primary='Residual max-registered-view opportunities AFTER actual S-on; R1_S1, R0_S1 and full positive controls separate',
        reference_family='Actual latecore f0; baseline policy is copied from each original checked_snapshot/two_lane config')
    (args.out/'CURRENT_CONFIG.json').write_text(json.dumps(config,indent=2)+'\n')
    print(json.dumps(dict(status='PREPARED_METADATA_NOT_RAW_ANALYSIS', attempts=len(entries),
                          S_on=sum(entry['actual_S_on'] for entry in entries),source=str(source))))


if __name__=='__main__':
    main()
