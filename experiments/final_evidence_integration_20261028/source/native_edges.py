"""Actual stored memory -> recorded neural input -> result -> later write table."""
from pathlib import Path
import argparse,csv,json,traceback
from common import begin,put,digest
from task_truth import judge,prior_valid


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--indices',type=Path,nargs='+',required=True)
    p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    source,e=begin(a,'NATIVE-INPUT-WRITEBACK');rows=[];pairs=[];summaries=[]
    try:
        for study in ['native_v8_pilot_v1','native_strong_v10_v1']:
            stage=e.json(study+'/SMOKE_SUMMARY.json');assert stage['execution_complete'] and len(stage['rows'])==10
            lookup={}
            for cell in stage['rows']:
                assert cell['execution_status']=='COMPLETE';base=study+'/cells/'+cell['id']
                d=e.json(base+'/DATABASE_DUMP.json');audit=e.json(base+'/INDEPENDENT_AUDIT.json');cfg=e.json(base+'/RUN_CONFIG.json')
                assert audit['evidence_tier']=='ACTUAL_GPU_MODEL' and not audit['unknown']
                assert not audit['violations'] if cell['arm']!='candidate_only' else all(x.startswith('unauthorized-state-admission:') for x in audit['violations'])
                requests={r['op']:json.loads(r['frozen']) for r in d['requests']}
                selections={r['id']:json.loads(r['evidence']) for r in d['selections']}
                byop={r['op']:(r['id'],selections[r['id']]) for r in d['selections']}
                receipts={r['seq']:json.loads(r['receipt']) for r in d['admissions']}
                committed={r['op']:json.loads(r['receipt']) for r in d['admissions'] if r['seq']>0}
                failures={}
                for x in d['events']:
                    if x['kind']=='model-unfulfilled':
                        y=json.loads(x['payload']);failures[y['op']]=y['evidence']
                for op,f in sorted(requests.items(),key=lambda x:x[1]['cycle']):
                    entry=byop.get(op);selected=entry[1] if entry else failures.get(op);assert selected is not None
                    req=selected['request'];user=json.loads(req['messages'][-1]['content'])
                    assert user=={k:f[k] for k in ['source','prior_memory','request']}
                    assert selected['actual_input_ids']==req['input_ids']
                    prior=receipts[f['parent']];assert prior['value']==f['prior_memory']
                    prior_selection=selections.get(prior.get('selection_id'))
                    prior_unauthorized=bool(prior_selection and not prior_selection['selection_authorized'])
                    if f['parent']>0:assert selected['started_ns']>=prior['committed_ns']
                    current=committed.get(op);write=bool(current)
                    if write:
                        assert current['value']==selected['value'] and current['selection_id']==entry[0]
                        truth=judge(f['family'],f['source'],f['prior_memory'],f['request'],selected['value'])
                        old=next(r['score'] for r in audit['task_scores'] if r['op']==op)
                        for k,v in truth.items():assert old[k]==v,(study,cell['id'],op,k)
                    else:truth=dict(schema_valid=None,current_output_valid=None,transition_valid=None,current_step_success=False)
                    row=dict(study=study,cell=cell['id'],family=f['family'],arm=cell['arm'],cycle=f['cycle'],parent=f['parent'],
                        actual_neural_input_ids_sha256=digest(selected['actual_input_ids']),source_request_key=digest([f['source'],f['request']]),
                        prior_memory=f['prior_memory'],prior_memory_sha256=digest(f['prior_memory']),
                        prior_memory_task_valid=prior_valid(f['family'],f['source'],f['prior_memory']),
                        prior_source='unprotected-previous-selection' if prior_unauthorized else 'authorized-previous-selection' if f['parent']>0 else 'declared-genesis',
                        actual_downstream_input=f['parent']>0,consumed_unauthorized_previous_value=prior_unauthorized,
                        tokens_sha256=digest(selected.get('tokens',[])),returned_value=selected.get('value'),returned_value_sha256=digest(selected.get('value')),
                        full_stop=selected['terminated_by_eos'],selection_authorized=selected.get('selection_authorized',False),
                        committed=write,next_receipt_seq=current['seq'] if current else None,unfulfilled=not write,
                        schema_valid=truth['schema_valid'],current_output_valid=truth['current_output_valid'],step_success=truth['current_step_success'],
                        actual_neural_calls=sum(c.get('operation') in ['generate','verify'] for c in selected.get('actual_calls',[])),
                        control='clean frozen model realizations; not an injected attack or an isolated feedback intervention')
                    rows.append(row);lookup[cell['arm'],f['cycle']]=row
                assert len(requests)==3
            for family in ['runbook','resource_plan']:
                source_rows=[r for r in rows if r['study']==study and r['family']==family]
                reference={r['cycle']:r for r in source_rows if r['arm']=='standard_direct'}
                for r in source_rows:
                    b=reference[r['cycle']];matched=r['source_request_key']==b['source_request_key'];assert matched
                    pairs.append(dict(study=study,family=family,arm=r['arm'],cycle=r['cycle'],same_source_request=True,
                        same_actual_input_ids=r['actual_neural_input_ids_sha256']==b['actual_neural_input_ids_sha256'],same_prior_value=r['prior_memory_sha256']==b['prior_memory_sha256'],same_returned_value=r['returned_value_sha256']==b['returned_value_sha256'],same_tokens=r['tokens_sha256']==b['tokens_sha256'],
                        reference_success=b['step_success'],candidate_success=r['step_success'],
                        reference_success_other_failure=b['step_success'] and not r['step_success'],both_fail=not b['step_success'] and not r['step_success'],
                        causal_scope='not isolated feedback causality: precision/selection contracts can also differ; clean base errors remain'))
            own=[r for r in rows if r['study']==study]
            summaries.append(dict(study=study,offered_cycles=len(own),committed_cycles=sum(r['committed'] for r in own),unfulfilled_cycles=sum(r['unfulfilled'] for r in own),downstream_inputs=sum(r['actual_downstream_input'] for r in own),unauthorized_values_consumed_by_future_requests=sum(r['consumed_unauthorized_previous_value'] for r in own),task_successes=sum(r['step_success'] for r in own)))
        bycycle={(r['study'],r['cell'],r['cycle']):r for r in rows}
        for r in rows:
            nxt=bycycle.get((r['study'],r['cell'],r['cycle']+1))
            if r['committed'] and nxt:
                assert nxt['parent']==r['next_receipt_seq'] and nxt['prior_memory_sha256']==r['returned_value_sha256']
            r['next_request_actually_consumes_this_write']=bool(r['committed'] and nxt)
        assert len(rows)==60 and len(pairs)==60
        put(a.out/'RESULT.json',dict(status='COMPLETE_NATIVE_ACTUAL_INPUT_GENERATION_WRITEBACK_TABLE',summaries=summaries,rows=rows,pairs=pairs,input_files=list(e.used.values()),GPU_inference_calls=0,scope='No attributable task-quality gain or permanent-contamination claim; actual neural consumption/selection and task truth remain separate'))
        scalar=[{k:(json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(dict,list)) else v) for k,v in r.items()} for r in rows]
        with (a.out/'NATIVE_INPUT_GENERATION_WRITEBACK.csv').open('x',newline='',encoding='utf8') as f:w=csv.DictWriter(f,fieldnames=list(scalar[0]));w.writeheader();w.writerows(scalar)
        put(a.out/'GATE.json',dict(gate='PASS_SCOPED_READONLY_NATIVE_EDGE_RECOUNT',code_commit=source['code_commit'],offered_cycles=60,GPU_inference_calls=0))
    except BaseException:
        put(a.out/'STOP.json',dict(error=traceback.format_exc(),completed_rows=len(rows),GPU_inference_calls=0));raise


if __name__=='__main__':main()
