"""Create point-specific paper figure data from accepted original36 and fixed midpoint12 offline recounters.

No plotting/style dependency, no model call, no selection of best repetitions.
Every figure row is keyed by the frozen workload point, arm and fresh-process
repeat. Quantiles are computed within a real run; they are never averaged into
a new pooled P99. Point summaries show the three values and their range.
"""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,csv,hashlib,json,math,platform,statistics,subprocess,sys

INPUTS={}
ARMS=('R0_S0','R0_S1','R1_S0','R1_S1')
ENDPOINTS=('display_P99','commit_view_P99','dual_credited_audio_seconds','dual_audio_fraction',
    'all_offered_audio_goodput_2_8','audio_rollback_events','audio_rollback_seconds',
    'rollback_area_audio_seconds_x_wall_seconds','all_offered_WER_percent',
    'GPU_joules','GPU_J_per_offered_audio_second','input_fsync_seconds','physical_model_seconds',
    'physical_lease_seconds','original_episode_wall_seconds','compatible_timely_deficit_area',
    'compatible_timely_loss_windows','compatible_unique_timely_withdrawn_audio_seconds',
    'compatible_D2_read_deficit_audio_seconds','incompatible_timely_deficit_area','UNKNOWN_timely_deficit_area')
COUNTS=('canonical_updates','ahead_updates','compatible_opportunities','incompatible_ahead_updates',
    'unresolved_ahead_updates','compatible_retained','compatible_cleared','compatible_changed',
    'compatible_unmatched','incompatible_cleared','incompatible_still_visible','ahead_observation_missing')

def read(p):
    p=Path(p);b=p.read_bytes();INPUTS[str(p.resolve())]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest());return json.loads(b)
def finite(x):return type(x) in (float,int) and math.isfinite(x)
def ratio(a,b):return a/b if b else None
def quantile(xs,q):
    xs=sorted(xs)
    if not xs:return None
    z=(len(xs)-1)*q;i=int(z);j=min(i+1,len(xs)-1);return xs[i]+(xs[j]-xs[i])*(z-i)
def put(out,name,rows):
    with (out/(name+'.json')).open('x',encoding='utf8') as f:json.dump(rows,f,indent=2,allow_nan=False);f.write('\n')
    if isinstance(rows,list) and rows:
        keys=list(dict.fromkeys(k for r in rows for k in r))
        with (out/(name+'.csv')).open('x',encoding='utf8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
            w.writerows({k:json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--old-plan',type=Path,required=True);p.add_argument('--new-plan',type=Path,required=True);p.add_argument('--old-root',type=Path,required=True);p.add_argument('--new-root',type=Path,required=True);p.add_argument('--old-secondary',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--source-manifest',type=Path,required=True)
    a=p.parse_args();source=read(a.source_manifest);here=Path(__file__).resolve().parent
    def git(*args):return subprocess.check_output(['git','-C',str(here),*args],text=True).strip()
    assert Path(git('rev-parse','--show-toplevel')).resolve()==here
    assert git('rev-parse','HEAD')==source['code_commit'] and not git('status','--porcelain','--untracked-files=all')
    assert set(git('ls-files').splitlines())=={r['path'] for r in source['files']}
    for r in source['files']:
        assert (here/r['path']).stat().st_size==r['bytes']
        assert hashlib.sha256((here/r['path']).read_bytes()).hexdigest()==r['sha256']
    oldplan=read(a.old_plan);newplan=read(a.new_plan)
    assert len(oldplan['cells'])==36 and len(newplan['cells'])==12
    assert oldplan['code_commit']==newplan['code_commit']=='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf'
    old=a.old_root;new=a.new_root/'core'
    assert read(old/'aggregate/SUMMARY.json')['accepted_cells']==36
    assert read(a.new_root/'GATE.json')['gate']=='PASS_ALL_12_MIDPOINT_RECOUNTS'
    assert read(new/'aggregate/SUMMARY.json')['accepted_cells']==12
    assert read(a.old_secondary/'GATE.json')['gate']=='PASS_ALL_36_READ_ONLY_CONTINUITY_RECOUNT'
    pointmap={x['point']:x for x in oldplan['points']+newplan['points']}
    plan=dict(cells=oldplan['cells']+newplan['cells'],points=[pointmap[k] for k in ('c8-sync','c8-staggered','c12-staggered','c16-staggered')])
    n=len(plan['cells']);assert n==48
    def joined(name):return read(old/name)+read(new/name)
    planned={c['cell_id']:c for c in plan['cells']};assert len(planned)==48
    runs={r['cell_id']:r for r in joined('aggregate/RUNS.json')};assert set(runs)==set(planned)
    opportunities=joined('opportunities/UPDATES.json');sources=joined('aggregate/SOURCE_METRICS.json')
    useful={r['cell_id']:r for r in joined('usefulness/RUNS.json')};assert set(useful)==set(planned)
    critical={r['cell_id']:r for r in joined('critical_path/RUNS.json')};assert set(critical)==set(planned)
    secondary={r['cell_id']:r for r in read(a.old_secondary/'RUNS.json')+read(a.new_root/'RUNS.json')};assert set(secondary)==set(planned)
    strong_decision=read(a.new_root/'STRONG_WITNESS_DECISION.json')
    all_updates=defaultdict(list)
    for u in opportunities:all_updates[u['cell_id'],u['clock_scope']].append(u)
    labels=lambda c:dict(cell_id=c['cell_id'],point=c['cohort'],sessions=c['sessions'],arrival=c['arrival'],
        arm=c['arm'],repeat=c['repeat'],paired_block=c['paired_block'],run_order_index=c['run_order_index'])
    endpoint_rows=[];opp_rows=[];path_rows=[]
    for cid,c in planned.items():
        r=runs[cid];u=useful[cid];cr=critical[cid];ss=secondary[cid];assert cr['accepted']
        assert abs(ss['original_dual_credited_audio_seconds']-r['dual_credited_audio_seconds'])<1e-6
        endpoint_rows.append(dict(labels(c),**{k:r.get(k) for k in ENDPOINTS},
            whole_run_dual_P99_pass=r['whole_run_dual_P99_pass'],
            compatible_timely_deficit_area=ss['compatible']['timely_deficit_area'],
            compatible_timely_loss_windows=ss['compatible']['timely_interval_loss_windows'],
            compatible_unique_timely_withdrawn_audio_seconds=ss['compatible']['unique_timely_withdrawn_audio_seconds'],
            compatible_D2_read_deficit_audio_seconds=ss['compatible']['original_D2_read_in_deficit_audio_seconds'],
            incompatible_timely_deficit_area=ss['incompatible']['timely_deficit_area'],
            UNKNOWN_timely_deficit_area=ss['UNKNOWN']['timely_deficit_area'],
            original_D2_margin_seconds=2-r['display_P99'] if finite(r['display_P99']) else None,
            original_C8_margin_seconds=8-r['commit_view_P99'] if finite(r['commit_view_P99']) else None,
            offered_audio_seconds=r['offered_audio_seconds'],offered_frontiers=r['offered_frontiers'],
            first_certified_or_same_F_raw_agreeing_timely_audio_seconds=
                u['first_certified_dual_timely_audio_seconds']+u['first_ahead_raw_equal_dual_timely_audio_seconds'],
            selected_lead_audio_weighted_mean_seconds=u['selected_lead_audio_weighted_mean_seconds'],
            Consumer_certification_lead_audio_weighted_mean_seconds=u['consumer_certification_lead_audio_weighted_mean_seconds'],
            content_scope='same-F later selected complete Canonical agreement, not groundtruth'))
        for clock in ('owner_install','consumer_apply'):
            updates=all_updates[cid,clock];assert updates
            counts=Counter(canonical_updates=len(updates))
            for v in updates:
                counts['ahead_observation_missing']+=v['ahead_observation_missing']
                if not v['ahead']:continue
                counts['ahead_updates']+=1
                if v['compatible'] is True:
                    counts['compatible_opportunities']+=1
                    key={'retained_same_view':'compatible_retained','cleared_to_canonical':'compatible_cleared',
                        'changed_ahead_view':'compatible_changed','unmatched':'compatible_unmatched'}[v['consumer_outcome']]
                    counts[key]+=1
                elif v['compatible'] is False:
                    counts['incompatible_ahead_updates']+=1
                    counts['incompatible_cleared']+=v['consumer_outcome']=='cleared_to_canonical'
                    counts['incompatible_still_visible']+=v['consumer_outcome']=='retained_same_view'
                else:counts['unresolved_ahead_updates']+=1
            ahead=[(v['before_visible_F']-v['F'])/16000 for v in updates if v['ahead']]
            opp_rows.append(dict(labels(c),clock_scope=clock,**{k:counts[k] for k in COUNTS},
                ahead_rate_all_updates=ratio(counts['ahead_updates'],counts['canonical_updates']),
                compatible_rate_all_updates=ratio(counts['compatible_opportunities'],counts['canonical_updates']),
                compatible_rate_given_ahead=ratio(counts['compatible_opportunities'],counts['ahead_updates']),
                retained_rate_given_compatible=ratio(counts['compatible_retained'],counts['compatible_opportunities']),
                ahead_audio_seconds_P50=quantile(ahead,.5),ahead_audio_seconds_P99=quantile(ahead,.99),
                ahead_audio_seconds_max=max(ahead) if ahead else None,
                ahead_audio_seconds_sum=sum(ahead),
                scope='actual complete visible progress relative to newly selected F; opportunity incidence, not an independent workload axis'))
        for population in ('all_frontier_path','display_miss_paths'):
            z=cr[population]
            path_rows.append(dict(labels(c),population=population,frontiers=z['frontiers'],audio_seconds=z['audio_seconds'],
                **{'stage_P50_'+k:v for k,v in z['stage_P50'].items()},
                **{'stage_P99_'+k:v for k,v in z['stage_P99'].items()},dominant_stage_counts=z['dominant_stage_counts'],
                scope='per-stage quantiles are not additive; summed stages are validated per individual frontier'))
    points=[];interactions=[];block_history=[]
    sourceby=defaultdict(list)
    for s in sources:sourceby[s['cell_id']].append(s)
    for point in (p['point'] for p in plan['points']):
        for arm in ARMS:
            rows=sorted((r for r in endpoint_rows if r['point']==point and r['arm']==arm),key=lambda r:r['repeat'])
            assert len(rows)==3 and [r['repeat'] for r in rows]==[0,1,2]
            pp=sum(r['whole_run_dual_P99_pass'] for r in rows)
            summary={}
            for k in ENDPOINTS:
                vals=[r[k] for r in rows];known=[x for x in vals if finite(x)]
                summary[k]=dict(values_by_repeat=vals,median=statistics.median(known) if len(known)==3 else None,
                    minimum=min(known) if known else None,maximum=max(known) if known else None)
            points.append(dict(point=point,arm=arm,whole_run_pass_count=pp,total_fresh_processes=3,
                measured_class='ALL_THREE_PASS' if pp==3 else 'ALL_THREE_FAIL' if pp==0 else 'TIMING_DEPENDENT_PASS',
                metrics=summary,scope='descriptive observed three-process region; no population reliability confidence bound'))
        for repeat in range(3):
            rr={r['arm']:r for r in endpoint_rows if r['point']==point and r['repeat']==repeat};assert set(rr)==set(ARMS)
            for metric in (*ENDPOINTS,'first_certified_or_same_F_raw_agreeing_timely_audio_seconds'):
                vals=[rr[arm][metric] for arm in ARMS]
                if not all(finite(v) for v in vals):continue
                y00,y01,y10,y11=vals
                interactions.append(dict(point=point,repeat=repeat,metric=metric,
                    R0S0=y00,R0S1=y01,R1S0=y10,R1S1=y11,
                    interaction_Y11_minus_Y10_minus_Y01_plus_Y00=y11-y10-y01+y00,
                    R1S1_minus_R0S0=y11-y00,R1S1_minus_R0S1=y11-y01,R1S1_minus_R1S0=y11-y10))
            histories=defaultdict(dict)
            for arm,r in rr.items():
                for s in sourceby[r['cell_id']]:histories[s['source_id']][arm]=s.get('canonical_history_sha256')
            block_history.append(dict(point=point,repeat=repeat,source_count=len(histories),
                all_four_arm_same_full_history_sources=sum(len(h)==4 and len(set(h.values()))==1 and None not in h.values() for h in histories.values()),
                sources_with_differences=[source for source,h in histories.items() if len(h)!=4 or len(set(h.values()))!=1 or None in h.values()],
                scope='exact complete F/Z/P/text selected history within this point and fresh timing repeat'))
    out=a.output;out.mkdir(parents=True,exist_ok=False)
    for name,rows in [('RUN_ENDPOINTS',endpoint_rows),('OPPORTUNITY_RATES',opp_rows),('POINT_SUMMARY',points),
        ('PAIRED_INTERACTIONS',interactions),('POINT_BLOCK_CANONICAL_HISTORY',block_history),('CRITICAL_PATH_STAGE_DATA',path_rows)]:put(out,name,rows)
    put(out,'FROZEN_MIDPOINT_STRONG_WITNESS',strong_decision)
    put(out,'FIGURE_CONTRACT',dict(primary_question='Where does joint retention preserve progress, where do arms converge, and where can the real service meet original deadlines?',
        panels=[dict(panel='A',data='RUN_ENDPOINTS',x='point',y='display_P99',hue='arm',points='all three fresh repeats',threshold=2.),
            dict(panel='B',data='RUN_ENDPOINTS',x='point',y='dual_audio_fraction',hue='arm',points='all three fresh repeats'),
            dict(panel='C',data='OPPORTUNITY_RATES',filter='clock_scope == consumer_apply',x='point',y='compatible_rate_all_updates',hue='arm',points='all three repeats; also show ahead and incompatible rates'),
            dict(panel='D',data='RUN_ENDPOINTS',x='point',y='compatible_timely_deficit_area',hue='arm',points='all three fresh repeats')],
        commitments=['Retain original36 plus fixed midpoint12; the new point is exploratory, not a source-independent confirmation.',
            'Single-root timely deficit area is secondary and right-censored at the next Canonical root when no earlier covering view returns; it never replaces original first credit.',
            'Keep C8 endpoint separate and show every run, even though D2 may dominate.',
            'No best-point or best-repeat selection; no mean-of-P99 curve described as a pooled P99.',
            'Relative progress is measured endogenous opportunity incidence, not a controlled independent speed ratio.',
            'c8 to c16 uses a nested real-source mixture, so no precise universal capacity boundary is inferred.',
            'All offered denominators, WER and actual two-board joules are available beside the figure.',
            'Owner and Consumer clocks remain separate; use Consumer application for visible-retention opportunity.',
            'A necessary incompatible withdrawal is reported separately from compatible progress loss.']))
    put(out,'ANALYSIS_RECORD',dict(analysis_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        code_commit=source['code_commit'],command=sys.argv,inputs=INPUTS,new_GPU_calls=0,planned_cells=n,
        environment=dict(python=sys.version,platform=platform.platform()),
        rendering='data only; publication rendering is a separate step'))
    print(json.dumps(dict(output=str(out),run_rows=len(endpoint_rows),opportunity_rows=len(opp_rows),blocks=len(block_history),new_GPU_calls=0)))

if __name__=='__main__':main()
