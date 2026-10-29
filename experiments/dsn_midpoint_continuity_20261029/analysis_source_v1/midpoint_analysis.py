"""Frozen four-component recount plus timely-continuity decision; no models."""
from pathlib import Path
import argparse,hashlib,json,platform,subprocess,sys
from collections import defaultdict
from continuity_secondary import analyze_cell

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def put(p,v):
    with Path(p).open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')

def full_non_eos_interval(loss,total_samples):
    return loss['audio_seconds']==2.0 and loss['frontier']<total_samples

def strong_decision(runs,history_equal):
    r=[x for x in runs if x['arm']=='R1_S0'];j=[x for x in runs if x['arm']=='R1_S1']
    need=lambda x:len(x)==3 and sorted(z['repeat'] for z in x)==[0,1,2]
    conditions=dict(all_six_required_runs_present=need(r) and need(j),
        compute_only_P99_3_of_3=need(r) and all(x['whole_run_dual_P99_pass'] for x in r),
        joint_P99_3_of_3=need(j) and all(x['whole_run_dual_P99_pass'] for x in j),
        compute_only_full_non_EOS_witness_at_least_2_of_3=need(r) and sum(x['strong_full_non_EOS_timely_compatible_windows']>0 for x in r)>=2,
        joint_compatible_timely_losses_zero_in_all_3=need(j) and all(x['compatible']['timely_interval_loss_windows']==0 for x in j),
        protected_full_histories_equal=bool(history_equal))
    return dict(strong_witness=all(conditions.values()),conditions=conditions,
        decision='STRONG_WITNESS_OBSERVED_STOP' if all(conditions.values()) else 'STRONG_WITNESS_NOT_ESTABLISHED_STOP',
        first_credit_requirement='NONE: Joint need not win first credit',
        stop='No 10/11 point, phase/source/deadline retuning, or repeat extension')

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--plan-sha256',required=True)
    p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert sha(a.plan)==a.plan_sha256
    import run_analysis
    manifest=load(a.source_manifest);run_analysis.validate(manifest)
    plan=load(a.plan);assert len(plan['cells'])==12
    out=a.output;out.mkdir(parents=True,exist_ok=False)
    config=dict(experiment_id=plan['experiment_id']+'-CPU-RECOUNT',frozen_plan=str(a.plan),frozen_plan_sha256=a.plan_sha256,
        analysis_source_manifest_sha256=sha(a.source_manifest),GPU_calls=0,scope='all twelve new development runs; no source-independent confirmation')
    put(out/'CONFIG.json',config);put(out/'ENVIRONMENT.json',dict(python=sys.version,platform=platform.platform(),executable=sys.executable))
    put(out/'RUN_RECORD.json',dict(experiment_id=config['experiment_id'],code_commit=manifest['code_commit'],source_manifest_sha256=sha(a.source_manifest),
        measured_neural_commit=plan['code_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),
        environment_record=str(out/'ENVIRONMENT.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),
        raw_result_location=[c['output'] for c in plan['cells']],aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    try:
        cmd=[sys.executable,'-B',str(HERE/'run_analysis.py'),'--plan',str(a.plan),'--plan-sha256',a.plan_sha256,
            '--source-manifest',str(a.source_manifest),'--output',str(out/'core')]
        with (out/'CORE_RECOUNTS.log').open('x',encoding='utf8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
        assert r.returncode==0 and load(out/'core/GATE.json')['gate']=='PASS_CPU_RECOUNTS','core recount incomplete'
        primary={r['cell_id']:r for r in load(out/'core/aggregate/RUNS.json')}
        updates=defaultdict(list)
        for u in load(out/'core/opportunities/UPDATES.json'):
            if u['clock_scope']=='consumer_apply':updates[u['cell_id']].append(u)
        hashes={};rr=[];ll=[];ee=[]
        def raw(path,lines=False):
            b=Path(path).read_bytes();hashes[str(path)]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
            return [json.loads(x) for x in b.decode('utf8').splitlines() if x] if lines else json.loads(b)
        for c in plan['cells']:
            root=Path(c['output']);cs=raw(root/'attempt0/consumer.jsonl',True);fs=raw(root/'audit/FRONTIERS.json')
            meta={k:c[k] for k in ['cell_id','arm','cohort','arrival','repeat','sessions','paired_block']}
            row,losses,events=analyze_cell(meta,cs,fs,updates[c['cell_id']])
            totals={sid:max(f['frontier'] for f in fs if f['session_id']==sid) for sid in {f['session_id'] for f in fs}}
            for z in losses:
                z['full_non_EOS_original_interval']=full_non_eos_interval(z,totals[z['session_id']])
            strong=[z for z in losses if z['classification']=='compatible' and z['full_non_EOS_original_interval']]
            row['strong_full_non_EOS_timely_compatible_windows']=len(strong)
            row['strong_witness_frontiers']=[dict(session_id=z['session_id'],frontier=z['frontier'],version=z['version']) for z in strong]
            for key in ['whole_run_dual_P99_pass','display_P99','commit_view_P99','all_offered_WER_percent','GPU_joules','GPU_J_per_offered_audio_second']:
                row[key]=primary[c['cell_id']][key]
            assert abs(row['offered_audio_seconds']-plan['cohorts'][0]['selected_audio_seconds'])<1e-6
            assert row['offered_frontiers']==plan['cohorts'][0]['expected_offered_frontiers']
            rr.append(row);ll.extend(losses);ee.extend(events)
        groups=load(out/'core/aggregate/CANONICAL_HISTORY_GROUPS.json')
        history_equal=all(g['all_recorded_histories_equal'] and not g['missing_history_cells'] for g in groups)
        assert len(rr)==12 and sum(r['canonical_boundaries'] for r in rr)==sum(len(x) for x in updates.values())
        decision=strong_decision(rr,history_equal)
        put(out/'RUNS.json',rr);put(out/'TIMELY_LOSS_WINDOWS.json',ll);put(out/'ALL_ROLLBACK_EVENTS.json',ee)
        put(out/'SECONDARY_INPUT_HASHES.json',hashes);put(out/'STRONG_WITNESS_DECISION.json',decision)
        put(out/'SUMMARY.json',dict(status='COMPLETE_ALL_12_MIDPOINT_RECOUNT',cells=12,new_GPU_calls=0,
            all_protected_histories_equal=history_equal,strong_witness=decision['strong_witness'],decision=decision['decision'],
            original_metrics='all original first-credit, offered/EOS, D2/C8, quality and energy retained in core/',
            continuation='STOP: one fixed midpoint only'))
        put(out/'GATE.json',dict(gate='PASS_ALL_12_MIDPOINT_RECOUNTS',strong_witness=decision['strong_witness'],
            same_task_attribution=history_equal,negative_effect_is_complete=True,new_GPU_calls=0))
        run_analysis.validate(manifest)
        print(json.dumps(load(out/'SUMMARY.json')))
    except BaseException as e:
        put(out/'GATE.json',dict(gate='FAIL_PRESERVED_MIDPOINT_RECOUNT',reason=str(e),exception_type=type(e).__name__))
        raise

if __name__=='__main__':main()
