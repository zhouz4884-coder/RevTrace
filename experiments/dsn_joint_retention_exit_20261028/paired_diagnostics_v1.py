"""Local-only all-pair frontier and exact following-batch diagnostics.

A K0 proposal being obsolete is not itself a missed service obligation.  Both
arms' first actual views are taken from every offered frontier, including
Canonical coverage.  A linked K1 display equal to the first-ever target-F
Consumer time proves new frontier progress, without inventing a prior view.
"""
from pathlib import Path
from collections import Counter
import argparse,csv,hashlib,json,platform,subprocess,sys

INPUTS={}
def read(path):
    path=Path(path);raw=path.read_bytes();INPUTS[str(path.resolve())]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());return json.loads(raw)

def verify_source(path):
    manifest=read(path);root=Path(__file__).resolve().parent
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
    assert Path(git('rev-parse','--show-toplevel')).resolve()==root and git('rev-parse','HEAD')==manifest['code_commit']
    assert not git('status','--porcelain','--untracked-files=all')
    assert set(git('ls-files').splitlines())=={r['path'] for r in manifest['files']}
    for row in manifest['files']:
        p=root/row['path'];assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
    return manifest['code_commit']

def credit_class(a,b):
    return ('same_hit' if a else 'miss_to_hit') if b else ('hit_to_miss' if a else 'same_miss')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--results',type=Path,required=True);parser.add_argument('--source-manifest',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    commit=verify_source(args.source_manifest);base=args.results
    assert read(base/'analysis/GATE.json')['gate']=='PASS_OFFLINE_RECOUNT'
    assert read(base/'detail/GATE.json')['gate']=='PASS_SUPPLEMENTAL_OFFLINE_AUDIT'
    runs=read(base/'analysis/RUNS.json');matched=read(base/'analysis/MATCHED_ROWS.json');exits=read(base/'detail/EXIT_FOLLOWING_CONSUMER.json')
    byid={r['cell_id']:r for r in runs};frontiers={}
    for run in runs:
        rows=read(base/'cells'/run['cell_id']/'audit/FRONTIERS.json')
        index={(r['session_id'],r['frontier']):r for r in rows};assert len(index)==len(rows)
        assert abs(sum(r['audio_seconds'] for r in rows)-run['offered_audio_seconds'])<1e-8
        frontiers[run['cell_id']]=index
    effects=[];changed=[]
    for group in matched:
        a,b=group['a'],group['b'];A,B=frontiers[a],frontiers[b];assert set(A)==set(B)
        counts=Counter();audio=Counter()
        for key in sorted(A):
            x,y=A[key],B[key];assert x['audio_seconds']==y['audio_seconds']
            label=credit_class(x['dual_credit'],y['dual_credit']);counts[label]+=1;audio[label]+=x['audio_seconds']
            if x['dual_credit']!=y['dual_credit']:
                changed.append(dict(a=a,b=b,session_id=key[0],frontier=key[1],audio_seconds=x['audio_seconds'],classification=label,
                                    a_display_latency=x['display_latency'],b_display_latency=y['display_latency'],
                                    a_commit_view_latency=x['commit_view_latency'],b_commit_view_latency=y['commit_view_latency']))
        delta=byid[b]['metrics']['dual_credited_audio_seconds']-byid[a]['metrics']['dual_credited_audio_seconds']
        assert abs(audio['miss_to_hit']-audio['hit_to_miss']-delta)<1e-8
        effects.append(dict(a=a,b=b,arrival=byid[b]['arrival'],repeat=byid[b]['repeat'],arm_R=byid[b]['arm'][1],
                            all_offered_frontiers=len(A),classes={k:counts[k] for k in ('miss_to_hit','hit_to_miss','same_hit','same_miss')},
                            audio_seconds={k:audio[k] for k in ('miss_to_hit','hit_to_miss','same_hit','same_miss')},
                            net_dual_credit_audio_seconds=delta))
    case_rows=[];case_summaries=[]
    for exit in exits:
        if exit['arrival']!='sync':continue
        b=exit['cell_id'];group=next(m for m in matched if m['b']==b);a=group['a'];pairs={r['b_job']:r for r in group['rows']}
        first=[]
        for following in exit['following_actual_consumer_links']:
            jid=following['job_id'];pair=pairs[jid]
            assert pair['output_equal'] and pair['full_model_input_audit_equal'] and pair['actual_execution_context_equal'] and pair['peers_equal']
            applications=[c for c in following['actual_consumer_applications'] if c['exact_consumer_application']]
            assert len(applications)==1
            application=applications[0];key=(application['session_id'],pair['target_F']);x,y=frontiers[a][key],frontiers[b][key]
            advances=abs(application['consumer_observed_perf']-y['first_actual_visible_perf'])<1e-7
            row=dict(a=a,b=b,a_job=pair['a_job'],b_job=jid,source_id=pair['source_id'],session_id=key[0],target_F=key[1],
                     complete_input_sha256=pair['input_sha256'],same_actual_full_input_context_and_peers=True,same_complete_output=True,
                     a_owner_obsolete='proposal-obsolete' in pair['a_timing']['owner_outcomes'],
                     b_exact_actual_consumer_application=True,b_application_is_first_ever_target_coverage=advances,
                     b_advances_visible_frontier_from_previous_view=True if advances else None,
                     a_first_actual_consumer_source_kind=pair['a_timing']['first_actual_consumer_source_kind'],
                     b_first_actual_consumer_source_kind=pair['b_timing']['first_actual_consumer_source_kind'],
                     a_display_latency=x['display_latency'],b_display_latency=y['display_latency'],
                     a_commit_view_latency=x['commit_view_latency'],b_commit_view_latency=y['commit_view_latency'],
                     a_dual_credit=x['dual_credit'],b_dual_credit=y['dual_credit'],
                     credit_class=credit_class(x['dual_credit'],y['dual_credit']),
                     first_visible_lead_seconds=x['display_latency']-y['display_latency'],
                     model_start_lead_seconds=pair['a_timing']['model_start_relative_origin']-pair['b_timing']['model_start_relative_origin'])
            first.append(row);case_rows.append(row)
        assert len(first)==16
        counter=Counter(row['credit_class'] for row in first)
        case_summaries.append(dict(a=a,b=b,arrival='sync',repeat=byid[b]['repeat'],arm_R=byid[b]['arm'][1],
                                   following_batch_rows=len(first),same_full_input_context_output_and_peers=len(first),
                                   a_owner_obsolete=sum(r['a_owner_obsolete'] for r in first),
                                   b_exact_consumer_applications=len(first),b_first_ever_target_frontier_advances=sum(r['b_application_is_first_ever_target_coverage'] for r in first),
                                   credit_classes={k:counter[k] for k in ('miss_to_hit','hit_to_miss','same_hit','same_miss')},
                                   credited_audio_gained_seconds=sum(frontiers[b][r['session_id'],r['target_F']]['audio_seconds'] for r in first if r['credit_class']=='miss_to_hit'),
                                   credited_audio_lost_seconds=sum(frontiers[b][r['session_id'],r['target_F']]['audio_seconds'] for r in first if r['credit_class']=='hit_to_miss'),
                                   first_visible_lead_range_seconds=[min(r['first_visible_lead_seconds'] for r in first),max(r['first_visible_lead_seconds'] for r in first)],
                                   model_start_lead_seconds=first[0]['model_start_lead_seconds']))
    args.out.mkdir(parents=True,exist_ok=False)
    payloads=dict(ALL_FRONTIER_PAIRED_EFFECTS=effects,CHANGED_CREDIT_FRONTIERS=changed,SYNC_FOLLOWING_BATCH_ROWS=case_rows,SYNC_FOLLOWING_BATCH_SUMMARY=case_summaries)
    for name,payload in payloads.items():(args.out/(name+'.json')).write_text(json.dumps(payload,indent=2)+'\n',encoding='utf8')
    with (args.out/'SYNC_FOLLOWING_BATCH_ROWS.csv').open('x',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(case_rows[0]));writer.writeheader();writer.writerows(case_rows)
    record=dict(experiment_id='REVTRACE-DSN-RXK-JOINT-20261028-v1-PAIRED-SERVICE-DIAGNOSTICS',code_commit=commit,inputs=INPUTS,
                new_model_calls=0,python=sys.version,platform=platform.platform(),paired_contrasts=len(effects),sync_following_batches=len(case_summaries),actual_following_rows=len(case_rows),
                scope='Local offline exact matching and full offered-frontier service accounting; does not establish global mediation or natural prevalence')
    (args.out/'RUN_RECORD.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
    (args.out/'GATE.json').write_text(json.dumps(dict(gate='PASS_ALL_PAIRED_FRONTIER_AND_CONSUMER_CHECKS',strict_matching_rows=len(case_rows),new_model_calls=0),indent=2)+'\n',encoding='utf8')
    assert verify_source(args.source_manifest)==commit
    print(json.dumps(case_summaries))

if __name__=='__main__':main()
