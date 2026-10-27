"""Read actual V6 Private dispatches; no model call or simulated speedup.

Output is descriptive, ex-post opportunity accounting. Eventual Authority P
and installation clocks MUST NOT be supplied to an online waiting policy.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import hashlib
import json
import statistics


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--results', type=Path, required=True)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    groups = defaultdict(Counter)
    remaining = defaultdict(list)
    sources = defaultdict(set)
    hashes = []
    for stage in ['A_pilot', 'A', 'C', 'D_development', 'D_heldout']:
        summary_path = args.results / (stage + '_SUMMARY.json')
        summary = json.loads(summary_path.read_text())
        assert len(summary['completed']) == summary['cells']
        for name in summary['completed']:
            cell = args.results / stage / name
            data = {}
            for filename in ['events.jsonl', 'worker_records.jsonl']:
                path = cell / filename
                raw = path.read_bytes()
                hashes.append(dict(path=str(path.relative_to(args.results)),
                                   sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)))
                data[filename] = [json.loads(x) for x in raw.decode().splitlines() if x.strip()]
            events = data['events.jsonl']
            rows = data['worker_records.jsonl']
            t0 = next(x['t0_perf'] for x in events if x['kind'] == 'run-start')
            installs = {x['job_id']: t0+x['installed'] for x in events if x['kind'] == 'commit'}
            authorities = defaultdict(list)
            for row in rows:
                if row['job']['role'] == 'authority':
                    assert row['job']['job_id'] in installs
                    authorities[row['job']['session_id']].append(row)
            traffic = 'mixed' if '-mixed-' in name else 'clean'
            arrival = 'staggered' if '-staggered-' in name else 'sync'
            key = stage, traffic, arrival
            g = groups[key]
            g['runs'] += 1
            for row in rows:
                job, result = row['job'], row['result']
                if job['role'] != 'proposal':
                    continue
                sources[key].add(job['source_id'])
                g['private_jobs'] += 1
                g['private_caps'] += bool(result['hit_token_limit'])
                t = job['enqueue_perf']
                pending = [a for a in authorities[job['session_id']]
                           if a['job']['enqueue_perf'] <= t < installs[a['job']['job_id']]]
                g['any_pending_authority'] += bool(pending)
                prior = [a for a in pending if a['job']['audio_end_sample'] < job['audio_end_sample']]
                g['cover_pending'] += any(a['job']['audio_end_sample'] >= job['audio_end_sample']
                                          for a in pending)
                if not prior:
                    continue
                a = max(prior, key=lambda a: a['job']['audio_end_sample'])
                dt = installs[a['job']['job_id']] - t
                g['predecessor_pending'] += 1
                g['predecessor_already_received'] += a['result']['received_perf'] <= t
                g['logical_P_diff_expost'] += job['prompt_tokens'] != a['result']['state_tokens']
                g['cap_and_predecessor_pending'] += bool(result['hit_token_limit'])
                for bound in [.1, .25, .5, .75, 1., 1.5]:
                    g['install_within_' + str(bound)] += dt <= bound
                remaining[key].append(dt)
    report = []
    for k, g in sorted(groups.items()):
        row = dict(stage=k[0], traffic=k[1], arrival=k[2],
                   unique_sources=len(sources[k]), **g)
        if remaining[k]:
            row['remaining_install_expost_median_s'] = statistics.median(remaining[k])
        report.append(row)
    result = dict(status='COMPLETE_READ_ONLY_RAW_DISPATCH_CENSUS',
        groups=report, new_GPU_calls=0, independent_sources_not_repeats=True,
        scope='Realized executed jobs only; offered/retired windows require separate coverage table',
        limitations=['Ex-post remaining installation is not an online ETA.',
                     'Logical P difference does not establish realized-input difference after rollback/normalization.',
                     'No saved compute or legal Goodput follows without actual rerun.',
                     'C contains artificial holds and cannot estimate natural prevalence.'],
        inputs=hashes, script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if args.output:
        if args.output.exists():
            raise FileExistsError(args.output)
        args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='inputs'},indent=2))


if __name__ == '__main__':
    main()
