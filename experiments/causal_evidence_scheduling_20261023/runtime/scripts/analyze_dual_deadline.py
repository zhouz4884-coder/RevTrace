"""Read-only historical event reanalysis; not a new GPU run or capacity sweep."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values, q=.99):
    if not values:
        return None
    data = sorted(math.inf if x is None else x for x in values)
    index = (len(data)-1)*q
    lo = math.floor(index)
    frac = index-lo
    value = data[lo] if not frac else data[lo]*(1-frac)+data[min(lo+1,len(data)-1)]*frac
    return None if math.isinf(value) else value


def frontiers(duration, rate, step):
    terminal = round(duration*rate)
    chunk = round(step*rate)
    return list(range(chunk, terminal, chunk)) + [terminal]


def analyze(cell, display_deadlines=(2.,5.,8.), commit_deadlines=(4.,8.,12.,16.)):
    cfg = json.loads((cell/'config.json').read_text())
    result = json.loads((cell/'result.json').read_text())
    sessions = json.loads((cell/'sessions.json').read_text())
    events = [json.loads(line) for line in (cell/'events.jsonl').read_text().splitlines() if line.strip()]
    rate = cfg.get('sample_rate',16000)
    t0 = next(e['t0_perf'] for e in events if e['kind']=='run-start')
    jobs, frontier, checkpoint = {}, defaultdict(int), defaultdict(int)
    generation = defaultdict(int)
    published, valid, commits = defaultdict(list), defaultdict(list), defaultdict(list)
    counters = Counter()
    details, service = [], []
    for sequence,e in enumerate(events):
        sid = e.get('session_id')
        kind = e['kind']
        if kind=='segment-parent' and cfg.get('proposal_barrier','segment')=='segment':
            generation[sid] += 1
        elif kind=='proposal-rebase':
            generation[sid] += 1
        elif kind=='enqueue':
            jobs[e['job_id']] = e
            if e['role']=='proposal':
                counters['proposal_dispatches'] += 1
                counters['obsolete_target_at_dispatch'] += e['audio_end_sample']<=frontier[sid]
                counters['future_parent_at_dispatch'] += e['audio_start_sample']>=e['audio_end_sample']
        elif kind=='executor-complete':
            service.append({'role':e['role'], 'queue':e['started']-e['enqueue'],
                            'execution':e['completed']-e['started'],
                            'audio_ready_to_enqueue':e['enqueue']-e['audio_ready'],
                            'job_id':e['job_id']})
        elif kind=='commit':
            assert e['certificate_consumed']
            assert e['audio_start_sample']==frontier[sid]
            assert e['audio_end_sample']>frontier[sid]
            assert e['parent']==checkpoint[sid]
            frontier[sid] = e['audio_end_sample']
            checkpoint[sid] = e['version']
            commits[sid].append((frontier[sid],e['installed']))
        elif kind=='canonical-display':
            target=e['audio_end_sample']
            assert target<=frontier[sid]
            published[sid].append((target,e['displayed']))
            valid[sid].append((target,e['displayed']))
            counters['canonical_display_events'] += 1
        elif kind=='display':
            j = jobs[e['job_id']]
            target = j['audio_end_sample']
            superseded = j['parent']!=checkpoint[sid]
            obsolete = target<=frontier[sid]
            invalid = j.get('branch_generation',generation[sid])!=generation[sid]
            assert e.get('parent_superseded',superseded)==superseded
            counters['display_events'] += 1
            counters['superseded_parent_at_display'] += superseded
            counters['obsolete_target_at_display'] += obsolete
            counters['invalid_generation_at_display'] += invalid
            published[sid].append((target,e['displayed']))
            if not obsolete and not invalid:
                valid[sid].append((target,e['displayed']))
            if obsolete or invalid:
                details.append({'sequence':sequence,'sid':sid,'job_id':e['job_id'],
                                'target':target,'committed_frontier':frontier[sid],
                                'superseded_parent':superseded,'invalid_generation':invalid,
                                'time':e['displayed']})
    wall = result['wall_seconds_including_arrival_and_drain']
    points=[]
    for spec in sessions:
        sid=spec['session_id']
        previous=0
        for q in frontiers(spec['duration'],rate,2.):
            release=spec['offset']+q/rate
            def first(rows):
                selected=[t for b,t in rows if b>=q]
                return min(selected) if selected else None
            td=first(valid[sid]); tc=first(commits[sid]); raw=first(published[sid])
            # Sensitivity only: the historical trace does not log commits as display.
            both=first(valid[sid]+commits[sid])
            points.append({'sid':sid,'source_id':spec.get('source_id'), 'frontier_sample':q,
                           'audio_seconds':(q-previous)/rate,'release':release,
                           'display_latency':None if td is None else td-release,
                           'commit_latency':None if tc is None else tc-release,
                           'raw_first_cover_latency':None if raw is None else raw-release,
                           'commit_visible_sensitivity_latency':None if both is None else both-release})
            previous=q
    assert abs(sum(p['audio_seconds'] for p in points)-result['audio_seconds'])<1e-6
    grid=[]
    for dd in display_deadlines:
        for dc in commit_deadlines:
            ok=lambda p,key:(p[key] is not None and p[key]<=dd and
                             p['commit_latency'] is not None and p['commit_latency']<=dc)
            good=sum(p['audio_seconds'] for p in points if ok(p,'display_latency'))
            sensitivity=sum(p['audio_seconds'] for p in points if ok(p,'commit_visible_sensitivity_latency'))
            pd=percentile([p['display_latency'] for p in points])
            pc=percentile([p['commit_latency'] for p in points])
            grid.append({'display_deadline':dd,'commit_deadline':dc,
                         'logged_valid_display_goodput':good/wall,
                         'commit_visible_sensitivity_goodput':sensitivity/wall,
                         'joint_deadline_audio_fraction':good/result['audio_seconds'],
                         'dual_p99_pass':pd is not None and pc is not None and pd<=dd and pc<=dc})
    decomposition={}
    for role in ['proposal','authority']:
        rows=[r for r in service if r['role']==role]
        decomposition[role]={key:{'median':statistics.median([r[key] for r in rows]),
                                 'p99':percentile([r[key] for r in rows])}
                             for key in ['queue','execution','audio_ready_to_enqueue']}
    final_projection={str(row['session_id']):row['state']['prompt_tokens'] for row in result['final_states']}
    return {'cell':cell.name,'policy':cfg['policy'],'barrier':cfg.get('proposal_barrier'),
            'evidence':'offline_reanalysis_of_retained_real_GPU_trace',
            'independent_sources':len({s.get('source_id') for s in sessions}),
            'load_slots':len(sessions),'frontier_points':len(points),'counters':dict(counters),
            'valid_display_missing_points':sum(p['display_latency'] is None for p in points),
            'valid_display_frontier_p99':percentile([p['display_latency'] for p in points]),
            'commit_frontier_p99':percentile([p['commit_latency'] for p in points]),
            'reported_display_event_p99_preserved':result['display_p99_seconds'],
            'reported_commit_event_p99_preserved':result['commit_p99_seconds'],
            'audio_xrt_preserved':result['audio_seconds_per_wall_second'],
            'grid':grid,'decomposition':decomposition,'obsolete_examples':details[:12],
            'points':points,'final_projection':final_projection,
            'scope':'Common-frontier timing is not WER, semantic completeness or a capacity maximum. '
                    'Commit-visible view is a labeled publication-policy sensitivity, not a logged display.'}


def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    cells=sorted(x for x in a.input.iterdir() if (x/'events.jsonl').is_file())
    reports=[]; fingerprints={}
    for cell in cells:
        files=[cell/x for x in ['config.json','result.json','sessions.json','events.jsonl']]
        before={str(f):sha(f) for f in files}
        report=analyze(cell); reports.append(report)
        (a.output/(cell.name+'.json')).write_text(json.dumps(report,indent=2,allow_nan=False))
        assert before=={str(f):sha(f) for f in files}
        fingerprints.update(before)
        print(json.dumps({k:report[k] for k in ['cell','frontier_points','counters',
                   'valid_display_missing_points','valid_display_frontier_p99','commit_frontier_p99']}))
    summary={'cells':len(reports),'status':'READ_ONLY_HISTORICAL_REANALYSIS',
             'counts':dict(sum((Counter(r['counters']) for r in reports),Counter())),
             'all_original_files_unchanged':True,'input_sha256':fingerprints,
             'new_gpu_experiments':0,
             'conditions':[{k:r[k] for k in ['cell','counters','valid_display_missing_points',
                           'valid_display_frontier_p99','commit_frontier_p99','grid']} for r in reports]}
    (a.output/'SUMMARY.json').write_text(json.dumps(summary,indent=2,allow_nan=False))

if __name__=='__main__': main()
