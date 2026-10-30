"""Read-only, no-model export of completed native service evidence.

All actual observations are retained, not a sample of visually pleasing points.
Full text, tokens, and complete cuts remain on the experiment disk.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys

MAX_OUTPUT_ROWS = 250_000


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def lines(path):
    with Path(path).open('rb') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def put(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False) + '\n', encoding='utf8')


def epoch(path, row):
    if type(row.get('owner_epoch')) is int:
        return row['owner_epoch']
    match = re.search(r'owner_e(\d+)', str(path))
    if match is None:
        raise ValueError('actual owner namespace missing')
    return int(match[1])


class Writer:
    def __init__(self, path):
        self.stream = Path(path).open('x', encoding='utf8')
        self.rows = 0

    def write(self, row):
        self.rows += 1
        if self.rows > MAX_OUTPUT_ROWS:
            raise ValueError('bounded export row cap exceeded; no truncation allowed')
        self.stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')

    def close(self):
        self.stream.close()


def export(trial, runtime_source, out):
    trial, runtime_source, out = map(lambda p: Path(p).resolve(),
                                     (trial, runtime_source, out))
    if out == trial or out.is_relative_to(trial):
        raise ValueError('output must be separate from the read-only raw trial')
    config = read(trial / 'CONFIG.json')
    metrics_path = trial / 'METRICS_SUMMARY.json'
    if not metrics_path.exists():
        metrics_path = trial / 'SUMMARY.json'
    summary = read(metrics_path)
    if summary.get('analysis_phase') != 'offline_after_trial':
        raise ValueError('offline completed-trial metrics required')
    if not (trial / 'SERVICE_END.json').is_file():
        raise ValueError('completed service interval marker required')
    origin_record = read(trial / 'ORIGIN.json')
    if origin_record.get('original_D', 2.) != 2. or origin_record.get('original_C', 8.) != 8.:
        raise ValueError('original D2/C8 identity differs')
    origin = origin_record['origin_perf']
    out.mkdir(parents=True, exist_ok=False)
    # The explicit frozen runtime checkout remains byte-for-byte read only,
    # including when this exporter is invoked without Python's -B option.
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(runtime_source))
    storage = importlib.import_module('resilience_storage')
    if Path(storage.__file__).resolve().parent != runtime_source:
        raise ValueError('wrong checksum-validating scanner imported')
    writers = {name: Writer(out / (name + '.jsonl')) for name in
               ('history', 'native_boundaries', 'canonical_edges', 'frontiers', 'gpu_memory')}
    input_paths = {trial / 'CONFIG.json', trial / 'ORIGIN.json',
                   trial / 'SERVICE_END.json', metrics_path,
                   runtime_source / 'resilience_storage.py'}
    input_paths.add(trial / 'consumer.jsonl')
    predictions, canonical_text = {}, {}
    posterior_counts = {mode: dict(supported=0, mismatching=0, unknown=0,
                                   original_credit_supported_seconds=0.,
                                   original_credit_mismatching_seconds=0.,
                                   original_credit_unknown_seconds=0.)
                        for mode in ('raw', 'whitespace_stripped')}
    try:
        for path in sorted(trial.glob('owner_e*/worker_results.jsonl')):
            input_paths.add(path)
            for wrapper in lines(path):
                event = wrapper.get('event', wrapper)
                if event.get('kind') == 'asr_early':
                    cut = event['projection']['end']
                    key = (epoch(path, wrapper), event['job_id'])
                    digest = hashlib.sha256(storage.canonical(cut)).hexdigest()
                    if key in predictions and predictions[key] != digest:
                        raise ValueError('contradictory own-prediction observations')
                    predictions[key] = digest
        for path in sorted(trial.glob('owner_e*/state_sizes.jsonl')):
            input_paths.add(path)
            for row in lines(path):
                row['t_since_origin'] = row['observed'] - origin
                row['owner_epoch'] = epoch(path, row)
                history = row['history']
                inbox = history['inbox']
                unpinned = inbox['terminal'] - inbox['pinned_terminals']
                if not (0 <= unpinned <= inbox['terminal_limit']):
                    raise ValueError('observed unpinned terminal bound violated')
                if any(v > history['history_limit'] or v < 0
                       for v in history['audit_retained'].values()):
                    raise ValueError('observed individual retained-audit bound violated')
                row['derived_unpinned_terminals'] = unpinned
                writers['history'].write(row)
        for path in sorted(trial.glob('owner_e*/policy_audit.jsonl')):
            input_paths.add(path)
            for row in lines(path):
                if row.get('kind') != 'native_state':
                    continue
                keep = {key: row[key] for key in ('boundary', 'physical_slot',
                        'physical_incarnation', 'job_id', 'source_id',
                        'start_frontier', 'end_frontier', 'observed_perf') if key in row}
                keep['owner_epoch'] = epoch(path, row)
                keep['t_since_origin'] = row['observed_perf'] - origin
                # These are the original bounded counts/hashes, not model cuts.
                # Preserve every observer field so count definitions stay auditable.
                keep['before'] = row['before']
                keep['after'] = row['after']
                for key in ('buffer_shift', 'context_changed', 'bound_still_exceeded',
                            'added_samples', 'removed_samples'):
                    if key in row:
                        keep[key] = row[key]
                writers['native_boundaries'].write(keep)
        wal = trial / 'facts.wal'
        input_paths.add(wal)
        for obj, receipt in storage.scan(wal, repair_tail=False):
            if obj['kind'] != 'canonical':
                continue
            body = obj['body']
            canonical_text[(body['source_id'], body['next_state']['frontier'])] = body['next_state']['transcript']
            prediction = predictions.get((body['owner_epoch'], body['job']['job_id']))
            next_sha = hashlib.sha256(storage.canonical(body['next_state'])).hexdigest()
            writers['canonical_edges'].write(dict(
                source_id=body['source_id'], frontier=body['next_state']['frontier'],
                owner_epoch=body['owner_epoch'], job_id=body['job']['job_id'],
                journal_sequence=receipt['sequence'],
                own_prediction_changed=None if prediction is None else prediction != next_sha,
                selection_changed=body['record'].get('selection_changed'),
                returned_token_ids_count=len(body['record']['token_ids']),
                canonical_transcript_utf8_bytes=len(body['next_state']['transcript'].encode('utf8')),
                top1_full_text_utf8_bytes=None if not isinstance(body['record'].get('top1_full_text'), str) else len(body['record']['top1_full_text'].encode('utf8')),
                selected_full_text_utf8_bytes=None if not isinstance(body['record'].get('selected_full_text'), str) else len(body['record']['selected_full_text'].encode('utf8')),
                model_end=body['record']['model_end'],
                next_state_sha256=next_sha))
        consumer = list(lines(trial / 'consumer.jsonl'))
        credit = 0.
        offered_count = missing_d = missing_c = 0
        for source in config['settings']['sources']:
            rows = [row for row in consumer if row['source_id'] == source['source_id']]
            if not rows:
                raise ValueError('missing actual Consumer source')
            if any(b['observed'] < a['observed'] for a, b in zip(rows, rows[1:])):
                raise ValueError('Consumer clock order changed')
            previous = 0
            for frontier in list(range(8000, source['frames'], 8000)) + [source['frames']]:
                ready = origin + frontier / 16000
                first_visible = next((row for row in rows if row['observed'] >= ready and row['visible_frontier'] >= frontier), None)
                first_certified = next((row for row in rows if row['observed'] >= ready and row['certified_frontier'] >= frontier), None)
                d = first_visible['observed'] - ready if first_visible else None
                c = first_certified['observed'] - ready if first_certified else None
                actual_g = first_visible['visible_frontier'] if first_visible else None
                expected_text = canonical_text.get((source['source_id'], actual_g)) if first_visible else None
                support = {}
                weight = (frontier-previous)/16000
                original_credit = d is not None and c is not None and d <= 2. and c <= 8.
                credit += weight if original_credit else 0.
                offered_count += 1
                missing_d += d is None
                missing_c += c is None
                for mode in ('raw', 'whitespace_stripped'):
                    transform = (lambda text: text) if mode == 'raw' else (lambda text: ''.join(ch for ch in text if not ch.isspace()))
                    match = None if expected_text is None else transform(first_visible['text']) == transform(expected_text)
                    status = 'unknown' if match is None else 'supported' if match else 'mismatching'
                    support[mode] = status
                    posterior_counts[mode][status] += 1
                    if original_credit:
                        posterior_counts[mode]['original_credit_' + status + '_seconds'] += weight
                writers['frontiers'].write(dict(source_id=source['source_id'],
                    frontier=frontier, audio_seconds=weight,
                    D=d, C=c, D_minus_C=None if d is None or c is None else d-c,
                    original_dual_credit=original_credit,
                    first_visible_actual_G=actual_g,
                    actual_G_fact_found=expected_text is not None,
                    actual_G_whole_text_posterior_support=support,
                    is_EOS=frontier == source['frames']))
                previous = frontier
        primary = summary['primary']
        if (abs(credit - primary['dual_deadline_audio_credit_seconds']) > 1e-8
                or offered_count != primary['offered_frontiers']
                or missing_d != primary['missing_D_frontiers']
                or missing_c != primary['missing_C_frontiers']):
            raise ValueError('actual offered/credit/missing recount differs from frozen metrics')
        for mode in posterior_counts:
            expected = summary['posterior_whole_text_support'][mode]
            for status in ('supported', 'mismatching', 'unknown'):
                if posterior_counts[mode][status] != expected['all_offered_frontier_counts'].get(status, 0):
                    raise ValueError('ActualG posterior frontier recount differs')
                key = 'original_credit_' + status + '_seconds'
                if abs(posterior_counts[mode][key] - expected[key]) > 1e-8:
                    raise ValueError('ActualG posterior credit recount differs')
        power = trial / 'power.jsonl'
        if power.exists():
            input_paths.add(power)
            for row in lines(power):
                writers['gpu_memory'].write(dict(t_since_origin=row['time']-origin,
                                                gpu_memory_MiB=row.get('gpu_memory_MiB')))
    finally:
        for writer in writers.values():
            writer.close()
    put(out / 'METRICS_SUMMARY.json', summary)
    put(out / 'CONFIG.json', config)
    counts = {key: writer.rows for key, writer in writers.items()}
    if any(counts[key] == 0 for key in ('history', 'canonical_edges', 'frontiers')):
        raise ValueError('required observed series absent; partial output preserved')
    metadata = dict(schema='revtrace-bounded-service-evidence-v1',
        phase='offline_after_completed_trial', new_model_calls=0,
        cell_id=config['cell_id'], source_commit=config['source_commit'],
        raw_config_sha256=sha(trial/'CONFIG.json'),
        origin_perf=origin, raw_trial=str(trial), all_observed_rows_retained=True,
        counts=counts, inputs=[dict(path=str(p), sha256=sha(p)) for p in sorted(input_paths)],
        actual_G_posterior_recount=posterior_counts,
        original_offered_credit_recount_seconds=credit,
        returned_token_scope='Returned original IDs count is not new/correct ASR character volume.',
        outputs={p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()},
        worker_torch_allocator_memory='UNKNOWN_NOT_RECORDED_IN_FROZEN_FORMAL_PLAN',
        scope='Serving observations only; offline allocation excluded. No total-RSS-constant claim.')
    put(out / 'COLLECTION_METADATA.json', metadata)
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--trial', '--case-root', dest='trial', type=Path, required=True)
    parser.add_argument('--runtime-source', '--runtime-source-root', dest='runtime_source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = export(args.trial, args.runtime_source, args.out)
    print(json.dumps(dict(cell_id=result['cell_id'], counts=result['counts'],
                          new_model_calls=0)))
