"""Secondary read-only analysis; original first-observation credit is unchanged."""
from __future__ import annotations
import argparse, hashlib, json, platform, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path

EPS = 1e-6

def need(x, message):
    if not x:
        raise AssertionError(message)

def digest(b):
    return hashlib.sha256(b).hexdigest()

def save(p, v):
    with Path(p).open('x', encoding='utf8', newline='\n') as f:
        json.dump(v, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')

def analyze_cell(meta, consumers, frontiers, updates):
    by_sid = defaultdict(list)
    for row in consumers:
        by_sid[row['session_id']].append(row)
    fs = defaultdict(list)
    for f in frontiers:
        fs[f['session_id']].append(f)
    for sid, rows in by_sid.items():
        need(rows == sorted(rows, key=lambda r:r['observed_perf']), 'Consumer time regressed')
        for f in fs[sid]:
            visible = next((r['observed_perf'] for r in rows if r['valid_visible_frontier'] >= f['frontier']), None)
            certified = next((r['observed_perf'] for r in rows if r['certified_frontier'] >= f['frontier']), None)
            for actual, expected in [(visible, f['first_actual_visible_perf']), (certified, f['first_actual_certified_perf'])]:
                need((actual is None and expected is None) or
                     (actual is not None and expected is not None and abs(actual-expected) < EPS), 'first observation mismatch')
            dpass = visible is not None and visible-f['original_ready_perf'] <= 2
            cpass = certified is not None and certified-f['original_ready_perf'] <= 8
            need(bool(f['dual_credit']) == (dpass and cpass), 'original first credit changed')
    idx = {(u['session_id'], u['version']):u for u in updates}
    need(len(idx) == len(updates), 'duplicate consumer-apply witness')
    losses = []
    boundaries = drops = 0
    noncanonical_drops = 0
    event_records = []
    for sid, rows in by_sid.items():
        previous = None
        for n, row in enumerate(rows):
            if row['source_kind'] != 'canonical-display':
                if previous is not None and row['valid_visible_frontier'] < previous['valid_visible_frontier']:
                    noncanonical_drops += 1
                previous = row
                continue
            boundaries += 1
            u = idx.get((sid, row['canonical_version']))
            need(u is not None, 'missing Canonical compatibility witness')
            before = previous['valid_visible_frontier'] if previous else 0
            after = row['valid_visible_frontier']
            need(abs(u['observed_perf']-row['observed_perf']) < EPS and
                 u['before_visible_F'] == before and u['after_visible_F'] == after,
                 'compatibility witness is not actual adjacent Consumer boundary')
            need(u['consumer_matched'] and u['complete_selected_root_matched'], 'unmatched full selected root')
            if before > after:
                drops += 1
                classification = 'compatible' if u['compatible'] is True else 'incompatible' if u['compatible'] is False else 'UNKNOWN'
                ev = dict(cell_id=meta['cell_id'], session_id=sid, version=row['canonical_version'],
                          observed_perf=row['observed_perf'], before_F=before, after_F=after,
                          classification=classification, compatibility_reason=u['compatibility_reason'],
                          chain=u['chain'], visible_job_id=u['visible_job_id'],
                          selected_job_id=u['selected_job_id'], selected_P_sha256=u['selected_P_sha256'],
                          removed_offered_audio_seconds=0., timely_removed_audio_seconds=0.,
                          timely_deficit_area=0., timely_windows=0)
                for f in fs[sid]:
                    if not (after < f['frontier'] <= before):
                        continue
                    ev['removed_offered_audio_seconds'] += f['audio_seconds']
                    if not f['dual_credit']:
                        continue
                    need(f['first_actual_visible_perf'] <= row['observed_perf']+EPS, 'loss before first display')
                    recovery = stop = None
                    censored = False
                    for later in rows[n+1:]:
                        if later['valid_visible_frontier'] >= f['frontier']:
                            recovery = stop = later['observed_perf']
                            break
                        if later['source_kind'] == 'canonical-display':
                            stop = later['observed_perf']
                            censored = True
                            break
                    need(stop is not None, 'timely C8 frontier has no subsequent covering or Canonical observation')
                    duration = stop-row['observed_perf']
                    need(duration >= 0, 'negative deficit window')
                    deadline = f['original_ready_perf']+2
                    loss = dict(cell_id=meta['cell_id'], session_id=sid, frontier=f['frontier'],
                                audio_seconds=f['audio_seconds'], version=row['canonical_version'],
                                classification=classification, original_ready_perf=f['original_ready_perf'],
                                first_visible_perf=f['first_actual_visible_perf'],
                                first_certified_perf=f['first_actual_certified_perf'],
                                original_display_latency=f['display_latency'], original_commit_latency=f['commit_view_latency'],
                                start_perf=row['observed_perf'], stop_perf=stop, recovery_perf=recovery,
                                duration_seconds=duration, deficit_area=f['audio_seconds']*duration,
                                right_censored_at_next_canonical=censored,
                                original_D2_read_in_deficit=row['observed_perf'] <= deadline < stop)
                    losses.append(loss)
                    ev['timely_removed_audio_seconds'] += f['audio_seconds']
                    ev['timely_deficit_area'] += loss['deficit_area']
                    ev['timely_windows'] += 1
                event_records.append(ev)
            previous = row
    need(boundaries == len(updates), 'Canonical boundary coverage mismatch')
    summary = dict(meta, offered_audio_seconds=sum(f['audio_seconds'] for f in frontiers),
                   original_dual_credited_audio_seconds=sum(f['audio_seconds'] for f in frontiers if f['dual_credit']),
                   offered_frontiers=len(frontiers), canonical_boundaries=boundaries,
                   actual_canonical_rollback_events=drops, actual_noncanonical_rollback_events=noncanonical_drops)
    for classification in ['compatible','incompatible','UNKNOWN']:
        rr = [r for r in losses if r['classification'] == classification]
        ee = [e for e in event_records if e['classification'] == classification]
        unique = {(r['session_id'],r['frontier']):r['audio_seconds'] for r in rr}
        at_deadline = {(r['session_id'],r['frontier']):r['audio_seconds'] for r in rr if r['original_D2_read_in_deficit']}
        summary[classification] = dict(rollback_events=len(ee), timely_rollback_events=sum(e['timely_windows']>0 for e in ee),
            timely_interval_loss_windows=len(rr), unique_timely_withdrawn_audio_seconds=sum(unique.values()),
            event_sum_timely_withdrawn_audio_seconds=sum(r['audio_seconds'] for r in rr),
            timely_deficit_area=sum(r['deficit_area'] for r in rr),
            longest_timely_deficit_seconds=max((r['duration_seconds'] for r in rr), default=0.),
            right_censored_windows=sum(r['right_censored_at_next_canonical'] for r in rr),
            original_D2_read_in_deficit_audio_seconds=sum(at_deadline.values()))
    return summary, losses, event_records

def main():
    a = argparse.ArgumentParser()
    a.add_argument('--config', type=Path, required=True)
    a.add_argument('--manifest', type=Path, required=True)
    args = a.parse_args()
    config_bytes = args.config.read_bytes()
    config = json.loads(config_bytes)
    root = Path(__file__).resolve().parent
    manifest_bytes = args.manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    commit = subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip()
    need(commit == manifest['code_commit'], 'analysis source commit mismatch')
    need(not subprocess.check_output(['git','status','--porcelain','--untracked-files=all'], cwd=root, text=True).strip(), 'analysis source dirty')
    for f in manifest['files']:
        data = (root/f['path']).read_bytes()
        need(len(data) == f['bytes'] and digest(data) == f['sha256'], 'analysis source bytes differ')
    out = Path(config['output']); out.mkdir(parents=True, exist_ok=False)
    env = dict(python=sys.version, platform=platform.platform(), new_GPU_calls=0, scope='read-only CPU analysis')
    save(out/'CONFIG.json', config); save(out/'ENVIRONMENT.json', env)
    save(out/'RUN_RECORD.json', dict(experiment_id=config['experiment_id'], code_commit=commit,
        source_manifest_sha256=digest(manifest_bytes), frozen_config_sha256=digest(config_bytes),
        environment_sha256=digest((out/'ENVIRONMENT.json').read_bytes()), measured_neural_commit=config['measured_neural_commit'],
        raw_result_location=[c['raw_path'] for c in config['cells']],
        aggregate_summary_location=str(out/'SUMMARY.json'), gate_decision_location=str(out/'GATE.json')))
    inputs = {}
    def read(path, lines=False):
        path = str(path); data = Path(path).read_bytes()
        proof = dict(bytes=len(data), sha256=digest(data))
        need(config['input_files'].get(path) == proof, 'input identity mismatch: '+path)
        inputs[path] = proof
        return [json.loads(x) for x in data.decode('utf8').splitlines() if x] if lines else json.loads(data)
    try:
        all_updates = read(config['opportunities'])
        groups = defaultdict(list)
        for u in all_updates:
            if u['clock_scope'] == 'consumer_apply':
                groups[u['cell_id']].append(u)
        runs=[]; losses=[]; events=[]
        for c in config['cells']:
            p=Path(c['raw_path'])
            rr,ll,ee=analyze_cell(c['meta'],read(p/'attempt0/consumer.jsonl', True),read(p/'audit/FRONTIERS.json'),groups[c['meta']['cell_id']])
            runs.append(rr);losses.extend(ll);events.extend(ee)
        need(len(runs) == 36, 'not all 36 original runs')
        need(sum(r['canonical_boundaries'] for r in runs) == 3204, 'not all 3204 original updates')
        paired=[]
        for block in sorted({r['paired_block'] for r in runs}):
            g={r['arm']:r for r in runs if r['paired_block']==block}
            need(set(g)=={'R0_S0','R0_S1','R1_S0','R1_S1'}, 'incomplete four-arm block')
            paired.append(dict(paired_block=block,
                joint_minus_compute_only_original_first_credit=g['R1_S1']['original_dual_credited_audio_seconds']-g['R1_S0']['original_dual_credited_audio_seconds'],
                joint_minus_compute_only_compatible_timely_area=g['R1_S1']['compatible']['timely_deficit_area']-g['R1_S0']['compatible']['timely_deficit_area'],
                joint_minus_compute_only_deadline_read_deficit_audio=g['R1_S1']['compatible']['original_D2_read_in_deficit_audio_seconds']-g['R1_S0']['compatible']['original_D2_read_in_deficit_audio_seconds']))
        save(out/'RUNS.json',runs);save(out/'TIMELY_LOSS_WINDOWS.json',losses);save(out/'ALL_ROLLBACK_EVENTS.json',events);save(out/'PAIRED.json',paired)
        summary=dict(experiment_id=config['experiment_id'], status='COMPLETE_READ_ONLY_SECONDARY_ANALYSIS',
                     cells=len(runs), canonical_updates=sum(r['canonical_boundaries'] for r in runs),
                     total_actual_canonical_rollbacks=sum(r['actual_canonical_rollback_events'] for r in runs),
                     total_actual_noncanonical_rollbacks=sum(r['actual_noncanonical_rollback_events'] for r in runs),
                     all_original_offered_frontiers=sum(r['offered_frontiers'] for r in runs), new_GPU_calls=0,
                     interpretation='Subsequent continuity of originally timely delivered intervals; not replacement deployed credit or online content certification',
                     full_stop='Analyze all 36 once; zero effect is a complete result; no deadline/source/phase changes')
        save(out/'SUMMARY.json',summary)
        save(out/'INPUT_VERIFICATION.json',inputs)
        save(out/'GATE.json',dict(gate='PASS_ALL_36_READ_ONLY_CONTINUITY_RECOUNT', cells=36, effect_gate='NO_POSITIVE_EFFECT_REQUIREMENT'))
        print(json.dumps(summary))
    except BaseException as e:
        save(out/'GATE.json',dict(gate='FAIL_READ_ONLY_ANALYSIS', exception_type=type(e).__name__, reason=str(e)))
        raise

if __name__ == '__main__':
    main()
