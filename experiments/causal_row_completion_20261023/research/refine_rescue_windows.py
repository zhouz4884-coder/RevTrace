"""After full fixed statistics: legal one-flight window screen, no generation."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,sys
from rescue_window_core import subtract

def main():
    B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/row_completion_20261023';D=O/'rescue_feasibility_v1';assert not D.exists();D.mkdir()
    def read(p):return json.loads(p.read_text())
    def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
    primary=read(O/'ROW_FORMAL_RESULTS_v1/GONOGO.json')['primary_generic_executor_gate']
    with (O/'row_timing_v1/RESCUE_OBSERVABLE_SCREEN.csv').open() as f:screens=list(csv.DictReader(f))
    cache={};rows=[];recipes=[]
    for r in screens:
        stage,cell=r['stage'],r['cell'];C=O/stage/cell
        if (stage,cell) not in cache:
            es=lines(C/'events.jsonl');rs=lines(C/'worker_records.jsonl');cfg=read(C/'config.json');ss=read(C/'sessions.json')
            t0=next(e['t0_perf'] for e in es if e['kind']=='run-start')
            end={e['job_id']:e.get('displayed',e['time']) for e in es if e['kind'] in ['display','proposal-obsolete']}
            blocks=defaultdict(list)
            for z in rs:
                j=z['job']
                if j['role']=='proposal':
                    assert j['job_id'] in end,'do not presume a missing owner completion clock'
                    blocks[j['session_id']].append((j['enqueue_perf']-t0,max(end[j['job_id']],z['result']['received_perf']-t0)))
            walstarts={};owner=[]
            for e in es:
                if e['kind']=='wal-owner-start':walstarts[tuple(e['job_ids'])]=e['time']
                if e['kind']=='wal-owner-complete':
                    key=tuple(e['job_ids']);assert key in walstarts;owner.append((walstarts.pop(key),e['time']))
                if e['kind']=='render-checked':owner.append((e['time']-e['host_cpu_wall_seconds'],e['time']))
            assert not walstarts
            cache[stage,cell]=(es,rs,cfg,ss,t0,blocks,owner)
        es,rs,cfg,ss,t0,blocks,owner=cache[stage,cell];sid=int(r['session_id']);parent=int(r['known_parent'])
        target=int(r['target_frontier']);initial=[tuple(x) for x in json.loads(r['available_worker_lease_windows'])]
        private_free=subtract(initial,blocks[sid]);final=subtract(private_free,owner)
        next_parent=min((e['installed'] for e in es if e['kind']=='commit' and e['session_id']==sid and e['version']>parent),default=float('inf'))
        final=[(a,min(b,next_parent)) for a,b in final if min(b,next_parent)>a]
        already=r['already_timely_under_existing_rebase']=='True';largest=max((b-a for a,b in final),default=0.)
        target_job=[x for x in rs if x['job']['role']=='proposal' and x['job']['session_id']==sid and x['job']['audio_end_sample']==target]
        target_accounted=any(x['result']['received_perf']-t0<=float(r['deadline_s']) for x in target_job)
        out={**r,'after_Private_flight_windows':json.dumps(private_free),'after_owner_work_and_next_parent_windows':json.dumps(final),
          'largest_refined_window_s':largest,'target_already_accounted_requires_auxiliary_publication_not_window_rewind':target_accounted,
          'eligible_cost_probe_not_integrated_algorithm':bool(primary['primary_Goodput_gate'] and not already and largest>0),
          'future_observed_windows_are_offline_upper_bounds_not_online_prediction':True}
        rows.append(out)
        if out['eligible_cost_probe_not_integrated_algorithm']:
            c=next(e for e in es if e['kind']=='commit' and e['session_id']==sid and e['version']==parent)
            original=next(x['job'] for x in rs if x['job']['job_id']==c['job_id']);s=next(x for x in ss if x['session_id']==sid)
            expected_manifest=B/'datasets/revtrace/phaseD_20261021/manifest.json' if stage=='formal_row_v1' else O/'validation_source_v1/MANIFEST.json'
            source=next(x for x in read(expected_manifest)['sessions'] if x['source_id']==r['source_id'])
            recipes.append({'stage':stage,'cell':cell,'source_id':r['source_id'],'session_id':sid,'parent_version':parent,
              'parent_contract_digest':original['contract_digest'],'parent_epoch':original['contract_epoch'],
              'parent_frontier':c['audio_end_sample'],'parent_window':original['end_window'],'parent_P':c['next_prompt_tokens'],
              'target_frontier':target,'target_window':(target+31999)//32000,'audio_path':source['path'],'language':s['language'],
              'available_window_s':largest,'actual_windows':final,'target_already_accounted':target_accounted,
              'source_manifest':str(expected_manifest),'authority_runtime':cfg['authority_runtime'],
              'execution_role':'private-FP32-cost-operator-only-no-Canonical-admission-or-publication',
              'singleton_layout_is_declared_not_reused_original_batch_output':True})
    recipes.sort(key=lambda x:(-x['available_window_s'],x['cell'],x['source_id'],x['parent_version']))
    selected=[];seen_inputs=set()
    for recipe in recipes:
        key=(recipe['source_id'],recipe['parent_frontier'],recipe['target_frontier'],recipe['parent_window'],
          json.dumps(recipe['parent_P']),json.dumps(recipe['authority_runtime'],sort_keys=True))
        if key in seen_inputs:continue
        seen_inputs.add(key);selected.append(recipe)
        if len(selected)==6:break
    for i,x in enumerate(selected):x['recipe_id']=i
    with (D/'REFINED_WINDOWS.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (D/'COST_RECIPES_FROZEN.json').write_text(json.dumps({'recipes':selected,'maximum_generation_calls':2*len(selected),
       'selection':'largest actual positive refined lease/deadline window then immutable cell/source/parent keys;deduplicate identical neural inputs;no ASR outcome selection',
       'not_an_online_result_or_contract_extension':True},indent=2)+'\n')
    out={'status':'GO_BOUNDED_COST_OPERATOR_ONLY' if selected else 'NO_GO_NO_UNOCCUPIED_LEGAL_PRIVATE_WINDOW',
      'primary_shared_return_gate':primary['primary_Goodput_gate'],'screened_exact_P_events':len(rows),
      'late_positive_initial_windows':sum(r['already_timely_under_existing_rebase']=='False' and float(r['largest_observed_window_s'])>0 for r in rows),
      'late_positive_after_single_Private_flight_owner_work_and_parent':len(recipes),'selected_recipes':len(selected),
      'maximum_refined_window_s':max((r['available_window_s'] for r in recipes),default=0.),'new_model_calls':0,
      'no_integrated_Rescue_or_new_scheduling_algorithm_implemented':True,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (D/'SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main()
