"""Keep scouts out of formal medians; audit actual sparse batch collateral."""
import argparse,csv,json,statistics
from collections import defaultdict
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    summary=json.loads((a.root/'SUMMARY.json').read_text());assert summary['status']=='COMPLETE' and len(summary['completed'])==54
    rows=[]
    for name in summary['completed']:
        cell=a.root/name;proof=json.loads((cell/'INDEPENDENT_AUDIT.json').read_text());config=json.loads((cell/'config.json').read_text())
        phase,condition,policy,repeat=name.split('-');events=[json.loads(l) for l in (cell/'events.jsonl').read_text().splitlines()]
        jobs={e['job_id']:e for e in events if e['kind']=='enqueue'};batches=affected=held_rows=selected_rows=0
        for e in events:
            if e['kind']!='worker-status' or e['status']!='batch-started':continue
            ids=e['job_ids']
            if jobs[ids[0]]['role']!='proposal':continue
            batches+=1
            selected=[jid for jid in ids if (jobs[jid]['end_window']-config['delay_offset'])%config['delay_every']==0]
            if config['proposal_result_delay_seconds']>0 and selected:
                affected+=1;held_rows+=len(ids);selected_rows+=len(selected)
        rows.append({'cell':name,'phase':phase,'condition':condition,'policy':policy,'repeat':int(repeat[1:]),
            **{k:proof[k] for k in ['xrt','display_p99','commit_p99','gpu_j_per_audio_second','display_missing','invalid_visible_slot_seconds']},
            'obsolete_publication':proof['counts'].get('obsolete_publication',0),
            'retired':proof['counts'].get('proposal-obsolete',0),'skipped':proof['counts'].get('proposal-skip',0),
            'actual_proposal_batches':batches,'held_response_batches':affected,'window_selected_rows':selected_rows,
            'held_rows_including_collateral':held_rows,'collateral_held_rows':held_rows-selected_rows,
            'canonical_history_inputs':len(proof['authority_lifecycles'])})
    groups=defaultdict(list)
    for r in rows:
        if r['phase']=='formal':groups[r['condition'],r['policy']].append(r)
    agg=[]
    for (condition,policy),rs in sorted(groups.items()):
        assert len(rs)==3;entry={'condition':condition,'policy':policy,'repeats':3}
        for key in ['xrt','display_p99','commit_p99','gpu_j_per_audio_second','obsolete_publication','retired','skipped','invalid_visible_slot_seconds']:
            vs=[r[key] for r in rs];entry[key+'_median']=statistics.median(vs);entry[key+'_min']=min(vs);entry[key+'_max']=max(vs)
        agg.append(entry)
    pairs=[];lookup={(r['condition'],r['policy'],r['repeat']):r for r in rows if r['phase']=='formal'}
    for condition in ['anchor0','anchor6','hold1p5','hold3','sparse6']:
        for repeat in range(3):
            lazy=lookup[condition,'lazy',repeat]
            for baseline in ['legacy','barrier']:
                base=lookup[condition,baseline,repeat]
                pairs.append({'condition':condition,'baseline':baseline,'repeat':repeat,'xrt_ratio':lazy['xrt']/base['xrt'],
                    'energy_ratio':lazy['gpu_j_per_audio_second']/base['gpu_j_per_audio_second'],
                    'display_p99_ratio':lazy['display_p99']/base['display_p99'],'commit_p99_ratio':lazy['commit_p99']/base['commit_p99']})
    a.out.mkdir(exist_ok=False)
    for name,items in [('T3_CELLS.csv',rows),('T3_GROUPS.csv',agg),('T3_PAIRED.csv',pairs)]:
        with (a.out/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(items[0]));w.writeheader();w.writerows(items)
    (a.out/'T3_AGGREGATE.json').write_text(json.dumps({'formal_groups':agg,'pairs':pairs,'cells':rows,
        'scouts_not_pooled':9,'formal_cells':45,'scope':'artificial post-completion delivery hold, not kernel slowdown or natural fault prevalence'},indent=2)+'\n')
    print(json.dumps(agg,indent=2))
if __name__=='__main__':main()
