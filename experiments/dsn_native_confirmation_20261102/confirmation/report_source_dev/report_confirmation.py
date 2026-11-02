"""Fixed complete32/8 service report; separate quality, task and C4 evidence."""
from __future__ import annotations
import argparse,collections,hashlib,pathlib,sys,traceback
from report_common import (NN4F,DRIVER,CHECKER,SPEAKERS,CELLS,SEED,DRAWS,B,need,read,put,sha,canonical,csvout,
    identity,verify_inputs,run_p99_distribution,paired_bootstrap)

def c4_status(cfg,plan):
    if not cfg['c4_summary']:return dict(status='PENDING_SEPARATE_C4_CLOSURE',passed=False,illegal_install_count=None,scope='task/reference PASS does not close structural trace evidence')
    s=read(cfg['c4_summary']);g=read(cfg['c4_gate'])
    expected='PASS_COMPLETE_ORIGINAL_C4_CONFIRM32_TRACE_CLOSURE'
    need(s['status']==g['status']==expected,'C4 complete closure failed')
    for data in (s,g):
        need(data['planned_cells']==data['completed_cells']==data['passed_cells']==CELLS and data['failed_cells']==0 and data['expected_source_count']==SPEAKERS,'C4 scope incomplete')
        need(data['actual_checker_source_commit']==CHECKER and data['actual_NN_source_commit']==NN4F,'C4 execution roles differ')
        need(data['Root_actual_trace_audit_pending'] is False and data['root_actual_trace_recheck_pending'] is False,'C4 closure remains pending')
    by={c['cell_id']:c for c in plan['cells']};need(len(s['cells'])==CELLS and {c['cell_id'] for c in s['cells']}==set(by),'C4 cells differ from complete plan')
    selected=0
    for cell in s['cells']:
        planned=by[cell['cell_id']];need(cell['status']=='PASS_UNCHANGED_C4_ACTUAL_TRACE' and cell['input_SHA_before_after_equal'] is True,'C4 cell or raw immutability failed')
        need((cell['source_id'],cell['speaker_id'],cell['strategy'],cell['repeat'])==(planned['source_id'],planned['speaker_id'],planned['strategy'],planned['repeat']),'C4 case identity changed')
        raw=cell['checker_summary'];need(raw['status']=='PASS_ACTUAL_ORIGINAL_FULLCALL_DURABLE_AND_CONSUMER_REFINEMENT' and raw['CPU_controls']==35,'original C4 checker did not complete')
        need(raw['actual_runtime_source_commit']==NN4F and raw['checker_source_commit']==CHECKER,'original C4 identity wrong');selected+=raw['durable_original_transitions']
    expected_steps=4*sum((s['frames']+7999)//8000 for s in plan['sources'])
    need(selected==expected_steps,'C4 selected-step denominator changed')
    return dict(status=expected,passed=True,checked_cases=CELLS,checked_selected_steps=selected,original_checker=CHECKER,
        CPU_controls_distinct=35,repeated_controls_are_not_new_fault_types=True,source_summary_sha256=sha(cfg['c4_summary']),source_gate_sha256=sha(cfg['c4_gate']))

def collect(plan,summary):
    need(plan['expected_trials']==CELLS and plan['expected_source_count']==SPEAKERS and plan['driver']['source_commit']==DRIVER and plan['actual_NN']['source_commit']==NN4F,'fixed plan/source scope changed')
    need(len(plan['sources'])==SPEAKERS and len({s['speaker_id'] for s in plan['sources']})==len({s['source_id'] for s in plan['sources']})==SPEAKERS,'independent speaker scope wrong')
    need(summary['status']=='COMPLETE_FROZEN_NEW_TEST_CONFIRMATION_TASK_AND_ENDPOINTS' and summary['completed_trials']==CELLS,'complete queue required')
    by={c['cell_id']:c for c in plan['cells']};need(len(by)==CELLS and len(summary['cells'])==CELLS and {c['cell_id'] for c in summary['cells']}==set(by),'complete cell IDs changed')
    cells=[];quality_by_source=collections.defaultdict(list)
    for result in summary['cells']:
        cell=by[result['cell_id']];raw=pathlib.Path(cell['out']);ind=read(raw/'EXTERNAL_NEW_TEST_AUDIT.json');original=read(raw/'SUMMARY.json');config=read(raw/'CONFIG.json');gate=read(raw/'GATE.json')
        need(ind==result,'original a13 independent audit differs from campaign result')
        need((ind['source_id'],ind['strategy'],ind['repeat'])==(cell['source_id'],cell['strategy'],cell['repeat']),'independent audit case identity changed')
        need(sha(cell['config'])==cell['config_sha256'] and config==read(cell['config']),'actual/frozen cell config changed')
        need(config['settings']['source_commit']==NN4F and config['arm']==cell['strategy'] and config['reference_kind']=='strict','original4f execution/selection contract changed')
        need(len(config['settings']['sources'])==1 and config['settings']['sources'][0]['source_id']==cell['source_id'] and config['settings']['sources'][0]['speaker_id']==cell['speaker_id'] and config['fault']['kind']=='none' and 'cost_observer' not in config,'actual source/single-chain/normal uninstrumented contract changed')
        need(gate['status']=='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK' and original['gate']=='PASS_COMPLETE_TRIAL_TASK_AND_ORIGINAL_ENDPOINT_RECOUNT','original task gate failed')
        need(original['integrity']['original_reference']['status']=='PASS_COMPLETE_ORIGINAL_REFERENCE' and ind['semantic']['status']=='PASS_COMPLETE_SELECTED_TRACE_REFERENCE','original/a13 full task reference equality missing')
        expected=(config['settings']['sources'][0]['frames']+7999)//8000
        need(ind['semantic']['checked_steps']==expected,'complete original task-step count changed')
        p=ind['primary'];need(p['offered_frontiers']==expected and abs(p['offered_audio_seconds']-config['settings']['sources'][0]['frames']/16000)<1e-8,'all offered/EOS denominator changed')
        need(len(p['frontiers'])==expected and sum(r['is_EOS'] for r in p['frontiers'])==1,'EOS row missing')
        frames=config['settings']['sources'][0]['frames'];boundaries=list(range(8000,frames,8000))+[frames]
        need([r['frontier'] for r in p['frontiers']]==boundaries and all(r['source_id']==cell['source_id'] and r['is_EOS'] is (r['frontier']==frames) for r in p['frontiers']),'original offered source/cadence/EOS identity changed')
        need(abs(sum(r['audio_seconds'] for r in p['frontiers'])-p['offered_audio_seconds'])<1e-8,'original duration weights changed')
        q=original['quality'];need(len(q)==1 and q[0]['source_id']==cell['source_id'],'original quality source changed');quality_by_source[cell['source_id']].append(q[0])
        energy=ind['common_external_energy']['origin_to_confirmed_physical_model_drain'];need(abs(sum(energy['board_joules'].values())-energy['total_joules'])<1e-6,'both-board energy sum differs')
        cells.append(dict(cell_id=cell['cell_id'],source_id=cell['source_id'],speaker_id=cell['speaker_id'],policy=cell['strategy'],repeat=cell['repeat'],
            offered_audio_s=p['offered_audio_seconds'],offered_frontiers=p['offered_frontiers'],credit_audio_s=p['dual_deadline_audio_credit_seconds'],coverage_percent=100*p['dual_deadline_audio_credit_seconds']/p['offered_audio_seconds'],D99_s=p['primary_linear_all_offered_D99'],C99_s=p['primary_linear_all_offered_C99'],
            D2_C8_pass=p['complete_coverage_and_original_quantile_pass'],D2_misses=p['D2_misses_all_offered'],C8_misses=p['C8_misses_all_offered'],EOS_D2_misses=p['EOS_D2_misses'],missing_D=p['missing_D_frontiers'],missing_C=p['missing_C_frontiers'],common_model_drain_board_J=energy['total_joules'],common_model_drain_window_s=energy['seconds'],
            checked_original_steps=expected,task_reference_equal=True,original_quality=q[0],raw_result_location=str(raw)))
    expected_keys={(s['source_id'],a,r) for s in plan['sources'] for a in ('conservative','fullcall') for r in (0,1)}
    need({(r['source_id'],r['policy'],r['repeat']) for r in cells}==expected_keys,'source/policy/repeat matrix incomplete')
    unique_quality=[];source_rows=[]
    for src in sorted(plan['sources'],key=lambda s:(s['speaker_id'],s['source_id'])):
        sid=src['source_id'];qualities=quality_by_source[sid];need(len(qualities)==4 and all(q==qualities[0] for q in qualities),'original final task/quality differs between policies/repeats')
        unique_quality.append(qualities[0]);own=[r for r in cells if r['source_id']==sid];values={}
        for arm in ('conservative','fullcall'):
            ss=[r for r in own if r['policy']==arm];need(len(ss)==2,'source repeats incomplete')
            values[arm]=dict(den=sum(r['offered_audio_s'] for r in ss),credit=sum(r['credit_audio_s'] for r in ss),energy=sum(r['common_model_drain_board_J'] for r in ss),passes=sum(r['D2_C8_pass'] for r in ss))
        c,f=values['conservative'],values['fullcall'];need(abs(c['den']-f['den'])<1e-10,'paired source offered denominator differs')
        source_rows.append(dict(source_id=sid,speaker_id=src['speaker_id'],timing_repeats=2,offered_audio_s=c['den'],conservative_credit_audio_s=c['credit'],fullcall_credit_audio_s=f['credit'],paired_gain_audio_s=f['credit']-c['credit'],paired_gain_pp=100*(f['credit']-c['credit'])/c['den'],
            conservative_model_drain_board_J=c['energy'],fullcall_model_drain_board_J=f['energy'],energy_difference_J=f['energy']-c['energy'],conservative_passes=c['passes'],fullcall_passes=f['passes']))
    policies={}
    for arm in ('conservative','fullcall'):
        own=[r for r in cells if r['policy']==arm];den=sum(r['offered_audio_s'] for r in own);credit=sum(r['credit_audio_s'] for r in own)
        policies[arm]=dict(trials=len(own),offered_audio_s=den,offered_frontiers=sum(r['offered_frontiers'] for r in own),credit_audio_s=credit,duration_weighted_coverage_percent=100*credit/den,
            per_run_D99=run_p99_distribution([r['D99_s'] for r in own]),per_run_C99=run_p99_distribution([r['C99_s'] for r in own]),D2_C8_passes=sum(r['D2_C8_pass'] for r in own),
            D2_misses=sum(r['D2_misses'] for r in own),C8_misses=sum(r['C8_misses'] for r in own),EOS_D2_misses=sum(r['EOS_D2_misses'] for r in own),missing_D=sum(r['missing_D'] for r in own),missing_C=sum(r['missing_C'] for r in own),
            common_model_drain_board_J=sum(r['common_model_drain_board_J'] for r in own),J_per_offered_audio_s=sum(r['common_model_drain_board_J'] for r in own)/den)
    characters=sum(q['reference_characters'] for q in unique_quality);edits=sum(q['character_edits'] for q in unique_quality)
    quality=dict(source_units=SPEAKERS,policy_repeat_consistent=True,reference_characters_unique_once=characters,character_edits_unique_once=edits,CER_unique_sources=edits/characters if characters else None,original_per_source=unique_quality,
        scope='original whitespace-only native quality; one acoustic reference per speaker, not4x repeated characters; no quality-improvement claim')
    return cells,source_rows,policies,quality

def run(a):
    cfg=read(a.config);own=identity(a.manifest);pre=read(a.prelaunch)
    need(pre['config_sha256']==sha(a.config) and sha(pre['root_noarg_preflight'])==pre['root_noarg_preflight_sha256'],'report prelaunch differs')
    root=read(pre['root_noarg_preflight']);need(root['gate']=='SOURCE_IDENTITY_PASS' and root['code_commit']==own['source_commit'] and root['manifest_sha256']==own['manifest_sha256'],'Root CURRENT/noarg source gate wrong')
    need(root['setup_pointer'].replace('\\','/').endswith('/CURRENT.json') and 'setup_pointer_sha256' in root,'not no-argument source receipt')
    need(cfg['expected_trials']==CELLS and cfg['expected_speakers']==SPEAKERS and cfg['bootstrap']['draws']==DRAWS and cfg['bootstrap']['seed']==SEED and cfg['old_four_speaker_bank_included'] is False,'predeclared statistics changed')
    verify_inputs(cfg['inputs']);plan=read(cfg['service_plan']);campaign=pathlib.Path(cfg['campaign'])
    need(read(campaign/'CONFIG.json')==plan and read(campaign/'GATE.json')['status']=='COMPLETE_FROZEN_NEW_TEST_CONFIRMATION_TASK_AND_ENDPOINTS','campaign original gate/plan differs')
    out=pathlib.Path(cfg['raw_result_location']);need(out.is_absolute() and out.resolve().is_relative_to(B.resolve()),'report output outside8TB');out.mkdir(parents=True,exist_ok=False)
    put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,identity=own,CPU_only=True,new_model_calls=0))
    put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=own['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    try:
        cells,sources,policies,quality=collect(plan,read(campaign/'SUMMARY.json'));bootstrap,samples=paired_bootstrap(sources);closure=c4_status(cfg,plan)
        csvout(out/'ALL32_CELLS.csv',[{k:v for k,v in r.items() if k!='original_quality'} for r in cells]);csvout(out/'SOURCE8_PAIRED.csv',sources);csvout(out/'BOOTSTRAP20000.csv',samples)
        report=dict(status='PASS_COMPLETE_NEW8_CONFIRMATION_REPORT' if closure['passed'] else 'PERFORMANCE_COMPLETE_C4_PENDING',actual_NN_source=NN4F,original_service_driver=DRIVER,analysis_identity=own,
            trials=CELLS,independent_speakers=SPEAKERS,timing_repeats_per_policy=2,old_four_speaker_bank_included=False,policies=policies,source_pairs=sources,bootstrap=bootstrap,quality=quality,
            original_task_equal_all_trials=True,checked_original_steps=sum(c['checked_original_steps'] for c in cells),C4=closure,
            reference_generation='separate fixed reference-only computation, not serving trials/credit/energy',energy_scope='sum of original common both-board origin-to-confirmed-physical-model-drain windows',
            statistical_scope='eight paired speakers; two repeats held together; no frontier/transition/repeat pseudoreplication; negative effects retained')
        verify_inputs(cfg['inputs']);put(out/'PAPER_DATA.json',report);put(out/'SUMMARY.json',report)
        put(out/'GATE.json',dict(status=report['status'],performance_direction_not_a_gate=True,C4_closed=closure['passed'],new_model_calls=0))
    except BaseException:
        put(out/'GATE.json',dict(status='FAIL_NEW8_REPORT_PRESERVED',failure=traceback.format_exc()));raise

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('config','manifest','prelaunch'):p.add_argument('--'+n,required=True)
    run(p.parse_args())
