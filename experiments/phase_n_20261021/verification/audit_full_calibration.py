"""Independent minimal-trace audit of telemetry enabled/disabled pairs."""
import argparse,hashlib,json,math,statistics,sys
from collections import defaultdict
from pathlib import Path
import numpy as np
def audit(cell,sdk):
    sys.path[:0]=[str(sdk/'src'),str(sdk/'scripts')]
    from audit_tc_live_qwen import audit as certificate_audit
    from audit_dsn_journal import audit as journal_audit
    config=json.loads((cell/'config.json').read_text());result=json.loads((cell/'result.json').read_text())
    certificate_audit(cell)
    path=Path(json.loads((cell/'provenance.json').read_text())['durable_journal_path']);journal_audit(path,cell)
    events=[json.loads(l) for l in (cell/'events.jsonl').read_text().splitlines()]
    specs={r['session_id']:r for r in json.loads((cell/'sessions.json').read_text())}
    F=defaultdict(int);gen=defaultdict(int);pub=defaultdict(list);commits=defaultdict(list);history=defaultdict(list);jobs={};versions=set();published=set()
    for e in events:
        k=e['kind'];sid=e.get('session_id')
        if k=='proposal-rebase':gen[sid]+=1
        elif k=='enqueue':jobs[e['job_id']]=e
        elif k=='commit':
            assert e['audio_start_sample']==F[sid];F[sid]=e['audio_end_sample'];versions.add((sid,e['version']))
            commits[sid].append((F[sid],e['installed']))
            history[sid].append({key:e[key] for key in ['parent','version','audio_start_sample','audio_end_sample','segment_id','segment_tokens','next_prompt_tokens']})
        elif k=='display':
            j=jobs[e['job_id']];assert j['audio_end_sample']>F[sid] and j['branch_generation']==gen[sid]
            pub[sid].append((j['audio_end_sample'],e['displayed']))
        elif k=='canonical-display':
            assert e['audio_end_sample']==F[sid];published.add((sid,e['version']));pub[sid].append((F[sid],e['displayed']))
    assert versions==published
    if not config['diagnostic_lifecycle']:
        assert not any(e['kind'] in ['worker-status','wal-physical-timing','authority-wait-interval'] for e in events)
        assert all(e.get('gpu_model_started') is None for e in events if e['kind']=='executor-complete')
    pd=[];pc=[]
    for sid,s in specs.items():
        end=round(s['duration']*16000)
        for q in list(range(32000,end,32000))+[end]:
            ready=s['offset']+q/16000
            pd.append(min(t for b,t in pub[sid] if b>=q)-ready)
            pc.append(min(t for b,t in commits[sid] if b>=q)-ready)
    samples=defaultdict(list)
    for r in json.loads((cell/'power_samples.json').read_text())['samples']:samples[r['gpu']].append(r)
    energy=0.
    for rows in samples.values():
        rows.sort(key=lambda r:r['t']);energy+=sum((r['t']-l['t'])*(r['power_w']+l['power_w'])/2 for l,r in zip(rows,rows[1:]))
    assert abs(energy-result['power']['energy_joules'])<1e-5
    digest=hashlib.sha256(json.dumps(dict(history),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'cell':cell.name,'xrt':result['audio_seconds_per_wall_second'],'display_p99':float(np.quantile(pd,.99)),
        'commit_p99':float(np.quantile(pc,.99)),'gpu_j_per_audio_second':energy/result['audio_seconds'],
        'canonical_history_sha256':digest,'events_sha256':hashlib.sha256((cell/'events.jsonl').read_bytes()).hexdigest(),
        'wal_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'complete_hook_off_verified':not config['diagnostic_lifecycle']}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--sdk',type=Path,required=True);a=p.parse_args()
    assert json.loads((a.root/'SUMMARY.json').read_text())['status']=='COMPLETE'
    rows=[audit(c,a.sdk) for c in sorted(a.root.iterdir()) if (c/'result.json').exists()];assert len(rows)==12
    by={r['cell']:r for r in rows};pairs=[]
    for mode in ['fine_certified','coarse']:
        matching=[r for r in rows if r['cell'].startswith(mode+'-')]
        assert len({r['canonical_history_sha256'] for r in matching})==1
        for repeat in range(3):
            on=by[f'{mode}-hooks1-r{repeat}'];off=by[f'{mode}-hooks0-r{repeat}']
            pairs.append({'mode':mode,'repeat':repeat,**{key+'_on_over_off':on[key]/off[key] for key in ['xrt','display_p99','commit_p99','gpu_j_per_audio_second']}})
    result={'decision':'PASS_FULL_HOOK_CONTROL_AND_SAME_CANONICAL_HISTORY','cells':rows,'pairs':pairs,
        'scope':'All diagnostic clock/status/wait/rich-capture switches off versus on; A/B/C required publications remain in BOTH. Not an optimizer.'}
    (a.root/'INDEPENDENT_CALIBRATION_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'decision':result['decision'],'pairs':pairs},indent=2))
