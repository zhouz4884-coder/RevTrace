"""Fit bounded profiles from the 48 actually executed diagnostic V5 cells.

No model or SSH is invoked. Unselected operations remain unobserved. Private
root equality is not a full-chain retention or transcript-quality guarantee.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf8'))
def lines(path):return [json.loads(s) for s in path.read_text(encoding='utf8').splitlines()]
def audio_bin(seconds):return '0-8' if seconds<=8 else '8-16' if seconds<=16 else '16+'
def quantile(values,p):
    xs=sorted(values);at=(len(xs)-1)*p;i=int(at);f=at-i
    return xs[i] if not f else xs[i]+f*(xs[i+1]-xs[i])


def proposal_features(jobs):
    n=len(jobs)
    audio=[j['audio_end_sample']/16000 for j in jobs]
    interval=[(j['audio_end_sample']-j['audio_start_sample'])/16000 for j in jobs]
    return [1.,float(n),sum(audio)/10.,n*max(audio)**2/100.,
            n*max(len(j['prompt_tokens']) for j in jobs)/256.,n*max(interval)/2.,0.]


def root_probability(support,matches):
    """Prediction: Beta(1/2,1/2) mean. Descriptive raw-count Wilson interval."""
    assert 0<=matches<=support
    if not support:return {'support':0,'matches':0,'probability':None,'lower':0.,'upper':1.}
    z=1.959963984540054;p=matches/support;d=1+z*z/support
    center=(p+z*z/(2*support))/d
    half=z*math.sqrt(p*(1-p)/support+z*z/(4*support*support))/d
    return {'support':support,'matches':matches,
            'probability':(matches+.5)/(support+1.) if support>=8 else None,
            'lower':max(0.,center-half),'upper':min(1.,center+half)}


def collect_cell(cell,records,events,accounts):
    """Pure extraction used by the full run and explicit CPU fixtures."""
    byid={r['job']['job_id']:r for r in records};assert len(byid)==len(records)
    batches={a['batch_id']:a for a in accounts};assert len(batches)==len(accounts)
    published={e['job_id']:e for e in events if e['kind']=='display'}
    t0=next(e['t0_perf'] for e in events if e['kind']=='run-start')
    commits={e['job_id']:e for e in events if e['kind']=='commit'}
    obsolete={e['job_id'] for e in events if e['kind']=='proposal-obsolete'}
    proposer_rows=[];proposer_batches=[];compatibility=[];excluded=Counter()
    complete_nodes=defaultdict(list);available_nodes=defaultdict(list)
    for rec in records:
        j,r=rec['job'],rec['result']
        if j['role']!='proposal':continue
        key=j['session_id'],j['audio_end_sample']
        complete_nodes[key].append(rec)
        # In the production owner, obsolete completions do not enter
        # _proposal_results. The display event witnesses the actual accepted
        # Private node, even if a later Consumer rejects/withdraws its view.
        if j['job_id'] in published and j['job_id'] not in obsolete:
            available_nodes[key].append(rec)
    for a in accounts:
        rr=[byid[jid] for jid in a['job_ids']]
        assert rr and len({r['job']['role'] for r in rr})==1
        if rr[0]['job']['role']!='proposal':continue
        n=len(rr);start=a['worker_started_perf'];end=a['batch_drained_perf'];lease=end-start
        assert math.isfinite(lease) and lease>0
        xs=proposal_features([r['job'] for r in rr])
        proposer_batches.append({'cell':cell,'batch_id':a['batch_id'],'rows':n,
            'worker_started_perf':start,'batch_drained_perf':end,'physical_lease_s':lease,
            'physical_model_calls':len(a.get('phases',[])),
            **{f'x{i}':v for i,v in enumerate(xs)}})
        for rec in rr:
            j,r=rec['job'],rec['result'];receipt=r['_row_receipt']
            assert receipt['binding']['batch_id']==a['batch_id']
            assert receipt['binding']['job_id']==j['job_id']
            terminal=receipt['terminal_perf'];fraction=(terminal-start)/lease
            if not math.isfinite(fraction) or not 0<=fraction<=1:
                raise AssertionError(('row terminal outside actual physical lease',cell,j['job_id'],fraction))
            # No fault_actual/context override or generated Token count enters
            # the cost feature vector. Generated length is a training target.
            audio=j['audio_end_sample']/16000
            proposer_rows.append({'cell':cell,'batch_id':a['batch_id'],'job_id':j['job_id'],
                'session':j['session_id'],'source_id':j['source_id'],'rows':n,
                'audio_seconds':audio,'audio_bin':audio_bin(audio),
                'interval_seconds':(j['audio_end_sample']-j['audio_start_sample'])/16000,
                'declared_prompt_tokens':len(j['prompt_tokens']),
                'physical_lease_s':lease,'terminal_after_start_s':terminal-start,
                'row_fraction':fraction,'generated_tokens':len(r['token_ids']),
                'terminated_by_eos':r.get('terminated_by_eos'),'hit_token_limit':r.get('hit_token_limit'),
                'obsolete_at_owner':j['job_id'] in obsolete})
    for rec in records:
        j,r=rec['job'],rec['result']
        if j['role']!='authority':continue
        assert j['job_id'] in commits,'Only completed actual Canonical selections belong to this source study'
        if j['ces_operation']=='generate':operation='direct'
        elif r.get('online_verification',{}).get('fallback_used'):operation='fallback'
        else:
            excluded['accepted_verify_not_used_for_direct_fallback_fit']+=1;continue
        key=j['session_id'],j['audio_end_sample'];enqueue=j['enqueue_perf']
        available=[x for x in available_nodes[key] if x['result']['received_perf']<=enqueue
                   and t0+published[x['job']['job_id']]['displayed']<=enqueue]
        completed=[x for x in complete_nodes[key] if x['result']['received_perf']<=enqueue]
        out={'cell':cell,'operation':operation,'job_id':j['job_id'],'session':j['session_id'],
            'source_id':j['source_id'],'frontier_sample':j['audio_end_sample'],
            'parent':j['parent'],'authority_enqueue_perf':enqueue,
            'same_boundary_completed_nodes':len(completed),'available_nodes_at_enqueue':len(available),
            'node_job_id':'','node_received_perf':'','birth_group':'','root_equal':'','no_node_reason':'',
            'scope':'Actual selected output P versus pre-enqueue available same-boundary Private P; full chain not inferred'}
        if not available:
            reason='completed_but_not_available_private_node' if completed else 'no_completed_same_boundary_node'
            excluded[operation+'_'+reason]+=1;out['no_node_reason']=reason
            compatibility.append(out);continue
        # Reconstruct the same latest-owner-received map entry used at enqueue.
        _,node=max(enumerate(available),key=lambda item:(item[1]['result']['received_perf'],item[0]));nj,nr=node['job'],node['result']
        assert nj['source_id']==j['source_id'] and nj['session_id']==j['session_id']
        assert nj['audio_end_sample']==j['audio_end_sample'] and nj['audio_start_sample']<nj['audio_end_sample']
        if 'contract_digest' in j:assert nj['contract_digest']==j['contract_digest']
        if operation=='fallback':assert j['candidate_origin_job_id']==nj['job_id']
        same=nj['parent']==j['parent'] and nj['prompt_tokens']==j['prompt_tokens']
        matched=nr['state_tokens']==r['state_tokens']
        out.update(node_job_id=nj['job_id'],node_received_perf=nr['received_perf'],
            birth_group='same' if same else 'mismatch',root_equal=matched)
        compatibility.append(out)
    return proposer_rows,proposer_batches,compatibility,dict(excluded)


def fit_ridge(batches):
    """Fixed 15-step Huber IRLS ridge, raw seven cost() coordinates."""
    import numpy as np
    X=np.asarray([[r[f'x{i}'] for i in range(7)] for r in batches],dtype=float)
    y=np.asarray([r['physical_lease_s'] for r in batches],dtype=float)
    assert np.isfinite(X).all() and np.isfinite(y).all() and (y>0).all()
    weights=np.ones(len(y));penalty=np.eye(7)*.1;penalty[0,0]=0.
    for _ in range(15):
        beta=np.linalg.solve(X.T@(weights[:,None]*X)+penalty,X.T@(weights*y))
        residual=y-X@beta
        scale=max(1e-6,1.4826*float(np.median(np.abs(residual-np.median(residual)))))
        weights=np.minimum(1.,1.345*scale/np.maximum(np.abs(residual),1e-12))
    return {'coefficients':beta.tolist(),'prediction_floor_s':float(min(y)),
        'prediction_ceiling_s':float(max(y)),'support_physical_batches':len(y),
        'features':['1','n','sum_audio_prefix/10','n*max_audio_prefix^2/100',
            'n*max_declared_prompt_tokens/256','n*max_interval/2','0_for_proposal'],
        'fit':'15 fixed Huber IRLS steps; ridge=.1 except intercept; no rows discarded',
        'prediction_bounds':'Observed minimum/maximum physical lease; all raw outliers retained',
        'dtype_role':'FP16 proposer only','future_tokens_or_fault_labels_in_features':False}


def build_profiles(proposal_rows,proposal_batches,compatibility):
    by_n={};by_n_audio=defaultdict(dict);tokens={}
    for n in ['global']+sorted({str(r['rows']) for r in proposal_rows},key=int):
        selected=proposal_rows if n=='global' else [r for r in proposal_rows if r['rows']==int(n)]
        by_n[n]={'support':len(selected),'physical_batches':len({(r['cell'],r['batch_id']) for r in selected}),
            'fractions':[r['row_fraction'] for r in selected]}
        for audio in ('0-8','8-16','16+'):
            subset=[r for r in selected if r['audio_bin']==audio]
            if subset:by_n_audio[n][audio]={'support':len(subset),
                'physical_batches':len({(r['cell'],r['batch_id']) for r in subset}),
                'fractions':[r['row_fraction'] for r in subset]}
    for audio in ('0-8','8-16','16+'):
        subset=[r for r in proposal_rows if r['audio_bin']==audio]
        if subset:tokens[audio]={'support':len(subset),
            'median_generated_tokens':statistics.median(r['generated_tokens'] for r in subset)}
    matched={}
    for operation in ('direct','fallback'):
        matched[operation]={}
        for birth in ('same','mismatch'):
            selected=[r for r in compatibility if r['operation']==operation and r['birth_group']==birth]
            rate=root_probability(len(selected),sum(r['root_equal'] for r in selected))
            rate.update(unique_cells=len({r['cell'] for r in selected}),
                unique_source_frontiers=len({(r['source_id'],r['frontier_sample']) for r in selected}))
            matched[operation][birth]=rate
    costs={str(n):statistics.median(r['physical_lease_s'] for r in proposal_batches if r['rows']==n)
           for n in sorted({r['rows'] for r in proposal_batches})}
    return {'proposal':{'row_fraction_by_n':by_n,'row_fraction_by_n_audio':dict(by_n_audio),
        'median_generated_tokens_by_audio_bin':tokens,
        'audio_bin_definition':'0-8 means [0,8]; 8-16 means (8,16]; 16+ means (16,infinity)',
        'row_fraction_definition':'(actual complete Token/Stop terminal - Worker start) / full physical Batch-drained lease',
        'cdf_backoff':'Use supported n/audio cell; otherwise n, then global. support is rows, physical_batches is separate.',
        'minimum_support':8,'minimum_physical_batches':8,'no_future_token_length_feature':True},
        'compatibility':matched,'compatibility_scope':{
            'predicate':'Actual Canonical P equals latest pre-enqueue Owner-available Private P at same Session/audio frontier',
            'denominator':'Only pre-enqueue Private nodes accepted by owner into proposal-results (display event, not obsolete). No-node is excluded, never failure.',
            'full_chain_checked':False,'runtime_full_chain_guard_still_required':True,
            'probability':'Beta(0.5,0.5) posterior mean (matches+.5)/(support+1), only support>=8; otherwise null',
            'interval':'Wilson z=1.959963984540054 on raw transition counts; descriptive repeated-observation interval, not IID/clustered inferential guarantee',
            'unchosen_operation_outcomes_imputed':False}},costs


def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf8') as stream:
        if rows:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--base8tb',type=Path,required=True)
    ap.add_argument('--old-results',type=Path,required=True)
    ap.add_argument('--old-calibration',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();base=args.base8tb.resolve();old=args.old_results.resolve();out=args.output.resolve()
    for path in (old,args.old_calibration.resolve(),out):
        assert path!=base and base in path.parents,('All data/output must stay on designated experiment disk',str(path))
    if out.exists():raise FileExistsError('Select a unique profile output directory')
    summary=read(old/'SUMMARY.json');expected=read(old/'pilot_v1_EXPECTED.json')['cells']
    assert summary['status']=='COMPLETE_BOUNDED_V5_GPU_PILOT_AND_AUDIT' and summary['online_cells']==48
    assert len(expected)==len(set(expected))==48 and set(summary['completed_online'])==set(expected)
    audit_path=old/'pilot_v1_audit_corrected/SUMMARY.json'
    if not audit_path.exists():audit_path=old/'pilot_v1_audit/SUMMARY.json'
    audit=read(audit_path)
    assert audit['status']=='PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT' and audit['cells']==48 and not audit['failures']
    actual={p.name for p in (old/'pilot_v1').iterdir() if p.is_dir() and (p/'result.json').exists()}
    assert actual==set(expected),'Missing or unplanned completed online cells'
    out.mkdir(parents=True)
    inputs=[]
    def remember(path):inputs.append({'path':str(path.relative_to(base)),'sha256':sha(path),'bytes':path.stat().st_size})
    for path in (old/'SUMMARY.json',old/'pilot_v1_EXPECTED.json',audit_path,args.old_calibration.resolve()):remember(path)
    all_rows=[];all_batches=[];all_compat=[];excluded=Counter()
    try:
        for cell in sorted(expected):
            C=old/'pilot_v1'/cell
            files={name:C/name for name in ('config.json','result.json','provenance.json','worker_records.jsonl','events.jsonl','worker_batch_accounting.jsonl')}
            for path in files.values():remember(path)
            cfg=read(files['config.json']);result=read(files['result.json']);prov=read(files['provenance.json'])
            assert cfg['rho']==1 and cfg['fine_seconds']==2 and cfg['result_delivery']=='row'
            assert cfg['proposal_runtime']['dtype']=='float16' and cfg['authority_runtime']['dtype']=='float32'
            assert not cfg['authority_runtime'].get('online_oracle_diagnostic',False)
            assert prov['code_commit']==summary['source_commit']
            assert result['decision']=='PASS_PROTOCOL_COMPLETENESS'
            rows,batches,compat,counts=collect_cell(cell,lines(files['worker_records.jsonl']),
                lines(files['events.jsonl']),lines(files['worker_batch_accounting.jsonl']))
            all_rows.extend(rows);all_batches.extend(batches);all_compat.extend(compat);excluded.update(counts)
        assert len({r['cell'] for r in all_batches})==48
        profiles,costs=build_profiles(all_rows,all_batches,all_compat)
        hold=[r for r in all_batches if int(hashlib.sha256(r['cell'].encode()).hexdigest()[:8],16)%5==0]
        train=[r for r in all_batches if int(hashlib.sha256(r['cell'].encode()).hexdigest()[:8],16)%5!=0]
        fitted=fit_ridge(all_batches);train_fit=fit_ridge(train)
        errors=[]
        for r in hold:
            p=sum(r[f'x{i}']*train_fit['coefficients'][i] for i in range(7))
            p=min(train_fit['prediction_ceiling_s'],max(train_fit['prediction_floor_s'],p))
            errors.append(abs(p-r['physical_lease_s']))
        profiles['proposal']['contextual_cost_fit']=fitted
        profiles['proposal']['held_cell_diagnostic']={'physical_batches':len(hold),
            'cells':len({r['cell'] for r in hold}),'median_absolute_error_s':statistics.median(errors),
            'mean_absolute_error_s':statistics.mean(errors),
            'scope':'Cell-held historical diagnostic; reused acoustic sources, not independent confirmation'}
        cal=read(args.old_calibration)
        cal.setdefault('cost_seconds',{})['proposal']=costs
        cal.setdefault('contextual_cost_models',{})['proposal']=fitted
        profiles['source']={'source_commit':summary['source_commit'],'online_cells':48,
            'source_pool':'All prior V5 pilot sources are training/diagnostic for this extension, not held-out',
            'actual_proposal_rows':len(all_rows),'actual_proposal_physical_batches':len(all_batches),
            'actual_direct_fallback_transitions':len(all_compat),'excluded_denominators':dict(excluded),
            'new_GPU_calls':0,'source_calibration_sha256':sha(args.old_calibration),
            'script_sha256':sha(Path(__file__))}
        cal['closed_loop_profiles']=profiles
        write_csv(out/'PROPOSAL_ROWS.csv',all_rows);write_csv(out/'PROPOSAL_BATCHES.csv',all_batches)
        write_csv(out/'ROOT_COMPATIBILITY.csv',all_compat)
        (out/'CALIBRATION.json').write_text(json.dumps(cal,indent=2,allow_nan=False)+'\n',encoding='utf8')
        (out/'INPUT_MANIFEST.json').write_text(json.dumps(inputs,indent=2)+'\n',encoding='utf8')
        report={'status':'PASS_ACTUAL_SELECTED_EXECUTION_PROFILES','created_utc':datetime.now(timezone.utc).isoformat(),
            **profiles['source'],'compatibility':profiles['compatibility'],
            'held_cell_diagnostic':profiles['proposal']['held_cell_diagnostic'],
            'outputs':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()}}
        (out/'SUMMARY.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
        print(json.dumps(report,indent=2))
    except BaseException as error:
        (out/'STOP.json').write_text(json.dumps({'status':'PROFILE_BUILD_FAILED','error':repr(error),
            'processed_proposal_rows':len(all_rows),'source_evidence_preserved':True},indent=2)+'\n')
        raise


if __name__=='__main__':main()
