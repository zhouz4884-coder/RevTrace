"""Read only completed bounded metadata; no raw replay or model execution.

This is a writing audit, not a frozen experiment runner. It conserves already
computed SUMMARY fields and checks their links to the original byte inventory.
"""
from __future__ import annotations
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
E = ROOT / 'experiments/dsn_strengthening_20261031'
OUT = Path(__file__).resolve().parent
FINAL = '4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'

def read(path):
    return json.loads(path.read_bytes())

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    result = dict(operation='LOCAL_WRITING_AUDIT_OF_COMPLETED_BOUNDED_METADATA',
                  new_model_calls=0, raw_replay_performed=False,
                  actual_NN_source_commit=FINAL, inputs={}, groups={}, cells=[])
    phases = {}
    for phase in ('PAIRED32_V2_RESULTS', 'RESIDENT4_V2_RESULTS'):
        folder = E / phase
        index = read(folder / 'RAW_INDEX.json')
        lookup = {x['path']: x for x in index['files']}
        assert len(lookup) == index['file_count']
        assert sum(x['bytes'] for x in lookup.values()) == index['total_bytes']
        bounded = read(folder / 'BOUNDED_INDEX.json')
        assert digest(folder / 'RAW_INDEX.json') == bounded['raw_manifest_sha256']
        for row in bounded['bounded_files']:
            path = folder / row['relative']
            assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256']
        result['inputs'][phase] = dict(raw_manifest_sha256=digest(folder / 'RAW_INDEX.json'),
            bounded_index_sha256=digest(folder / 'BOUNDED_INDEX.json'),
            summary_sha256=digest(folder / 'SUMMARY.json'),
            raw_files=index['file_count'], raw_bytes=index['total_bytes'],
            raw_root=index['raw_root'], all_bounded_file_bytes_verified=True,
            remote_raw_rehashed=False)
        phases[phase] = folder, index, lookup
    folder, index, lookup = phases['PAIRED32_V2_RESULTS']
    campaign = read(folder / 'SUMMARY.json')
    final_rows = [r for r in campaign['cells'] if r['version'] == 'final']
    assert len(final_rows) == 16
    for arm in ('conservative', 'fullcall'):
        aggregate = dict(runs=0, independent_sources=4, offered_frontiers=0,
            offered_audio_seconds=0.0, original_dual_credit_audio_seconds=0.0,
            content={}, posterior_whole_text_support={})
        for mode in ('raw', 'whitespace_stripped'):
            aggregate['content'][mode] = Counter()
            aggregate['posterior_whole_text_support'][mode] = dict(
                original_credit_supported_seconds=0.0,
                original_credit_mismatching_seconds=0.0,
                original_credit_unknown_seconds=0.0,
                all_offered_frontier_counts=Counter())
        for row in final_rows:
            if row['strategy'] != arm:
                continue
            relative = f"cells/{row['cell_id']}/SUMMARY.json"
            path = folder / relative
            assert digest(path) == lookup[relative]['sha256'] == row['summary_sha256']
            summary = read(path)
            assert summary['source_commit'] == FINAL
            content, support = summary['content'], summary['posterior_whole_text_support']
            aggregate['runs'] += 1
            for key in ('offered_frontiers', 'offered_audio_seconds', 'original_dual_credit_audio_seconds'):
                aggregate[key] += content[key]
            for mode in ('raw', 'whitespace_stripped'):
                keep = ('introduced_code_point_occurrences', 'LCP_erased_code_point_occurrences',
                    'retracted_occurrence_code_points', 'still_visible_occurrence_code_points',
                    'closed_occurrence_code_point_seconds', 'observed_text_changes',
                    'positive_F_advance_with_unchanged_text_rows',
                    'positive_certified_F_advance_with_unchanged_text_rows',
                    'final_observed_text_code_points')
                aggregate['content'][mode].update({k: content[mode][k] for k in keep})
                dest = aggregate['posterior_whole_text_support'][mode]
                for key in ('original_credit_supported_seconds', 'original_credit_mismatching_seconds', 'original_credit_unknown_seconds'):
                    dest[key] += support[mode][key]
                dest['all_offered_frontier_counts'].update(support[mode]['all_offered_frontier_counts'])
                assert abs(sum(support[mode][k] for k in ('original_credit_supported_seconds', 'original_credit_mismatching_seconds', 'original_credit_unknown_seconds')) - content['original_dual_credit_audio_seconds']) < 1e-7
            result['cells'].append(dict(cell_id=row['cell_id'], source_id=row['source_id'],
                arm=arm, repeat=row['repeat'], summary_sha256=digest(path),
                raw_result_location=row['raw_result_location'], content=content,
                posterior_whole_text_support=support))
        assert aggregate['runs'] == 8
        result['groups']['final/' + arm] = aggregate
    resident = read(E / 'RESIDENT4_V2_RESULTS/SUMMARY.json')
    assert len(resident['cells']) == 4
    result['resident_existing_content'] = []
    for row in resident['cells']:
        summary = row['summary']
        assert summary['actual_NN_source_commit'] == FINAL
        result['resident_existing_content'].append(dict(cell_id=row['cell_id'], requests=summary['requests'],
            content_present='content' in summary, posterior_whole_text_support_present='posterior_whole_text_support' in summary,
            request_contract=summary['request_contract']))
    # Input candidate list for one future, separately frozen CPU-only recount.
    # Merely selecting inventory records here does not read their remote bytes.
    candidates=[]
    selected = {r['cell_id'] for r in final_rows}
    for phase, (folder, index, lookup) in phases.items():
        for item in index['files']:
            parts=item['path'].split('/')
            if len(parts)<3 or parts[0]!='cells':
                continue
            if phase.startswith('PAIRED') and parts[1] not in selected:
                continue
            name=parts[-1]
            if name not in {'CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','ORIGIN.json','REQUEST_ORIGINS.json','SERVICE_END.json','GENESIS.json','SUMMARY.json','GATE.json','consumer.jsonl','consumer_rejections.jsonl','facts.wal','ingress.jsonl','request_ledger.jsonl','publications.jsonl','dispatch.jsonl','worker_results.jsonl','owner_events.jsonl'}:
                continue
            candidates.append(dict(phase=phase,path=index['raw_root']+'/'+item['path'],**{k:item[k] for k in ('bytes','sha256')}))
    result['future_CPU_recount_input_candidates'] = candidates
    result['future_CPU_recount_candidate_bytes'] = sum(x['bytes'] for x in candidates)
    result['future_CPU_recount_candidate_files'] = len(candidates)
    target=OUT/'COMPLETED_METADATA_CONTENT_INDEX.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(output=str(target),groups=result['groups'],
        future_candidate_bytes=result['future_CPU_recount_candidate_bytes'],
        future_candidate_files=len(candidates)),ensure_ascii=False))

if __name__ == '__main__':
    main()
