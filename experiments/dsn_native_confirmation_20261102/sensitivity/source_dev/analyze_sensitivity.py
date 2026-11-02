"""Fixed display-budget sensitivity; does not alter original D2/C8 results."""
from __future__ import annotations
import argparse,collections,pathlib,statistics,sys,traceback
from sensitivity_common import NN4F,SOURCE_RECEIPT_SHA,SOURCES,B,need,read,put,sha,csvout,verify_inputs,verify_self,nearly,credit,denominator,validate_primary,validate_source_extent

def load_units(matched,resident,source_specs=None):
    need(matched['status']=='COMPLETE_PAIRED32_ACTUAL_SERVICE_AND_REFERENCE_AUDIT','matched archive incomplete')
    need(resident['status']=='PASS_RESIDENT4_COMPLETE_FROZEN_SCOPE','resident archive incomplete')
    units=[];resident_trial_checks=[]
    for cell in matched['cells']:
        if cell['version']!='final':continue
        need(cell['semantic']['status']=='PASS_COMPLETE_SELECTED_TRACE_REFERENCE' and cell['semantic']['actual_NN_source_commit']==NN4F,'matched original task/source gate changed')
        units.append(dict(bank='matched',cell_id=cell['cell_id'],source_id=cell['source_id'],arm=cell['strategy'],repeat=cell['repeat'],
            primary=cell['primary'],origin=None,audit=validate_primary(cell['primary'],cell['source_id'])))
    for cell in resident['cells']:
        s=cell['summary'];need(s['actual_NN_source_commit']==NN4F and s['gate']=='PASS_RESIDENT_COMPLETE_TASK_PER_REQUEST_CLOCK_AND_REFERENCE','resident original source/task gate changed')
        need(s['request_contract']=='closed_loop_single_outstanding_independent_EOS_v1' and len(s['per_request'])==4,'resident request scope changed')
        resident_trial_checks.append(dict(cell_id=cell['cell_id'],original_trial_metrics=validate_primary(s['primary'])))
        flat={}
        for req in s['per_request']:
            sid=req['source_id'];need(req['original_reference_status']=='PASS_COMPLETE_SELECTED_TRACE_REFERENCE','resident original reference missing')
            units.append(dict(bank='resident',cell_id=cell['cell_id'],source_id=sid,arm=cell['arm'],repeat=cell['repeat'],
                primary=req['primary'],origin=req['request_origin_perf'],audit=validate_primary(req['primary'],sid,req['request_origin_perf'])))
            for row in req['primary']['frontiers']:
                key=(sid,row['frontier']);need(key not in flat,'resident per-request duplicate');flat[key]=row
        need(flat=={(r['source_id'],r['frontier']):r for r in s['primary']['frontiers']},'resident per-request and whole-trial original rows differ')
    expected={(b,s,a,r) for b in ('matched','resident') for s in SOURCES for a in ('conservative','fullcall') for r in (0,1)}
    need(len(units)==32 and {(u['bank'],u['source_id'],u['arm'],u['repeat']) for u in units}==expected,'32 original request units incomplete or duplicated')
    by=collections.defaultdict(list)
    for u in units:by[u['source_id']].append(u)
    for sid,items in by.items():
        if source_specs is not None:
            for u in items:validate_source_extent(u['primary']['frontiers'],source_specs[sid])
        reference=[(r['frontier'],r['audio_seconds'],r['is_EOS']) for r in items[0]['primary']['frontiers']]
        need(all([(r['frontier'],r['audio_seconds'],r['is_EOS']) for r in u['primary']['frontiers']]==reference for u in items),'same acoustic source changed offered/EOS across bank/policy/repeat')
    return units,resident_trial_checks

def curves(units,grid):
    source=[];bank=[];paired=[]
    for b in ('matched','resident'):
        for tau in grid:
            lookup={}
            for sid in SOURCES:
                for arm in ('conservative','fullcall'):
                    rows=[row for u in units if (u['bank'],u['source_id'],u['arm'])==(b,sid,arm) for row in u['primary']['frontiers']]
                    den=denominator(rows);value=credit(rows,tau);lookup[(sid,arm)]=(value,den)
                    source.append(dict(bank=b,source_id=sid,arm=arm,tau_d_seconds=tau,original_tau_c_seconds=8.,offered_audio_seconds=den,credited_audio_seconds=value,duration_weighted_fraction=value/den,timing_repeats=2))
                c,dc=lookup[(sid,'conservative')];f,df=lookup[(sid,'fullcall')];need(nearly(dc,df),'paired offered denominator changed')
                paired.append(dict(bank=b,source_id=sid,tau_d_seconds=tau,original_tau_c_seconds=8.,offered_audio_seconds=dc,conservative_credit_audio_s=c,fullcall_credit_audio_s=f,paired_gain_audio_s=f-c,paired_gain_percentage_points=100*(f-c)/dc,independent_acoustic_units=1,timing_repeats=2))
            for arm in ('conservative','fullcall'):
                values=[lookup[(sid,arm)] for sid in SOURCES];den=sum(x[1] for x in values);value=sum(x[0] for x in values);fracs=[x[0]/x[1] for x in values]
                bank.append(dict(bank=b,arm=arm,tau_d_seconds=tau,original_tau_c_seconds=8.,offered_audio_seconds=den,credited_audio_seconds=value,duration_weighted_fraction=value/den,source_min_fraction=min(fracs),source_max_fraction=max(fracs),source_median_fraction=statistics.median(fracs),independent_speakers=4,envelope='descriptive minmax of four source curves; not confidence interval'))
    return source,bank,paired

def run(a):
    cfg=read(a.config);identity=verify_self(a.manifest);pre=read(a.prelaunch)
    need(pre['config_sha256']==sha(a.config) and sha(pre['root_noarg_preflight'])==pre['root_noarg_preflight_sha256'],'prelaunch binding changed')
    gate=read(pre['root_noarg_preflight']);need(gate['gate']=='SOURCE_IDENTITY_PASS' and gate['code_commit']==identity['source_commit'] and gate['manifest_sha256']==identity['manifest_sha256'],'Root source identity gate missing')
    need(gate['setup_pointer'].replace('\\','/').endswith('/CURRENT.json') and 'setup_pointer_sha256' in gate,'not no-argument CURRENT gate')
    verify_inputs(cfg['inputs']);need(cfg['tau_d_grid']==[.5+i*.25 for i in range(23)] and cfg['tau_c']==8.,'frozen sensitivity grid changed')
    out=pathlib.Path(cfg['raw_result_location']);need(out.is_absolute() and out.resolve().is_relative_to(B.resolve()),'output outside8TB');out.mkdir(parents=True,exist_ok=False)
    put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,identity=identity,CPU_only=True,text_normalization='not used; source receipt text fields are ignored'))
    put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=identity['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    try:
        need(sha(cfg['source_receipt'])==SOURCE_RECEIPT_SHA,'original source-extent receipt differs')
        receipt=read(cfg['source_receipt']);need(receipt['status']=='PASS_FOUR_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE','source receipt gate changed')
        specs={s['source_id']:s for s in receipt['sources']};need(set(specs)==set(SOURCES),'original source receipt identity set changed')
        units,trials=load_units(read(cfg['matched_summary']),read(cfg['resident_summary']),specs)
        source,bank,paired=curves(units,cfg['tau_d_grid'])
        # Event-exact full finite-latency range; no chosen tail cutoff or
        # renormalization after C8/missing observations.
        full_grid=sorted({0.,6.,*(r['D'] for u in units for r in u['primary']['frontiers'] if r['D'] is not None)})
        full_source,full_bank,full_pairs=curves(units,full_grid)
        d2=[r for r in paired if r['tau_d_seconds']==2.];checks=[]
        for b in ('matched','resident'):
            for arm in ('conservative','fullcall'):
                own=[u for u in units if (u['bank'],u['arm'])==(b,arm)];credit2=sum(u['audit']['dual_deadline_audio_credit_seconds'] for u in own);den=sum(u['audit']['offered_audio_seconds'] for u in own);passes=sum(u['audit']['original_D2_C8_pass'] for u in own)
                expected={('matched','conservative'):(30.,0),('matched','fullcall'):(65.821625,6),('resident','conservative'):(31.,0),('resident','fullcall'):(64.118875,7)}[(b,arm)]
                need(nearly(credit2,expected[0]) and passes==expected[1] and nearly(den,66.33975),'original headline D2/C8 result changed')
                curve=next(r for r in bank if (r['bank'],r['arm'],r['tau_d_seconds'])==(b,arm,2.));need(nearly(curve['credited_audio_seconds'],credit2),'D2 sensitivity positive control changed')
                checks.append(dict(bank=b,arm=arm,original_D2_credit_audio_s=credit2,original_D2_C8_request_passes=passes,original_request_count=8,offered_audio_seconds=den))
        repeat_d2=[]
        for b in ('matched','resident'):
            for sid in SOURCES:
                for repeat in (0,1):
                    own={u['arm']:u for u in units if (u['bank'],u['source_id'],u['repeat'])==(b,sid,repeat)}
                    den=own['conservative']['audit']['offered_audio_seconds'];c=own['conservative']['audit']['dual_deadline_audio_credit_seconds'];f=own['fullcall']['audit']['dual_deadline_audio_credit_seconds']
                    repeat_d2.append(dict(bank=b,source_id=sid,repeat=repeat,offered_audio_seconds=den,conservative_credit_audio_s=c,fullcall_credit_audio_s=f,paired_gain_audio_s=f-c,paired_gain_percentage_points=100*(f-c)/den))
        finite_limits=[]
        for b in ('matched','resident'):
            for arm in ('conservative','fullcall'):
                rs=[r for u in units if (u['bank'],u['arm'])==(b,arm) for r in u['primary']['frontiers']];den=denominator(rs)
                finite_limits.append(dict(bank=b,arm=arm,all_offered_audio_s=den,C8_ineligible_audio_s=sum(r['audio_seconds'] for r in rs if r['C'] is None or r['C']>8),missing_D_audio_s=sum(r['audio_seconds'] for r in rs if r['D'] is None),finite_deadline_limit_audio_s=sum(r['audio_seconds'] for r in rs if r['D'] is not None and r['C'] is not None and r['C']<=8),denominator_never_filtered=True))
        csvout(out/'BANK_GRID.csv',bank);csvout(out/'SOURCE_GRID.csv',source);csvout(out/'SOURCE_PAIRED_GRID.csv',paired);csvout(out/'SOURCE_PAIRED_D2.csv',d2);csvout(out/'REPEAT_PAIRED_D2.csv',repeat_d2)
        csvout(out/'BANK_FULL_CDF.csv',full_bank);csvout(out/'SOURCE_FULL_CDF.csv',full_source)
        csvout(out/'ORIGINAL_D2_CHECKS.csv',checks)
        public=dict(status='PASS_FROZEN_D2_POSITIVE_CONTROL_AND_SOURCE_PAIRED_SENSITIVITY',actual_NN_source=NN4F,analysis_identity=identity,tau_d_grid=cfg['tau_d_grid'],tau_c_fixed=8.,original_D2_checks=checks,
            banks_separate=True,independent_acoustic_speakers=4,same_four_speakers_reused_in_both_banks=True,matched_trials=16,resident_trials=4,resident_requests=16,total_original_offered_rows=sum(len(u['primary']['frontiers']) for u in units),
            original_unit_audits=[dict(bank=u['bank'],cell_id=u['cell_id'],source_id=u['source_id'],arm=u['arm'],repeat=u['repeat'],request_origin=u['origin'],**u['audit']) for u in units],resident_trial_checks=trials,
            bank_curves=bank,source_paired_D2=d2,repeat_paired_D2=repeat_d2,finite_limits=finite_limits,full_CDF_knots=len(full_grid),full_CDF_max_seconds=full_grid[-1],
            scope='posthoc budget sensitivity of archived actual offer/D/C; no new neural/serving runs, no accuracy or online support recertification',
            original_P99_and_passes_unchanged=True,threshold_dependent_new_pass_counts_not_generated=True,envelope_not_CI=True,missing_or_C8_ineligible_mass_not_removed=True)
        if cfg['render_figures']:
            from plot_sensitivity import render
            public['figure_exports']=render(bank,full_bank,d2,repeat_d2,out/'FIGURES')
        verify_inputs(cfg['inputs']);put(out/'PAPER_DATA.json',public);put(out/'SUMMARY.json',public)
        put(out/'GATE.json',dict(status=public['status'],original_D2_C8_preserved=True,scientific_curve_direction_not_a_gate=True,new_neural_calls=0))
    except BaseException:
        put(out/'GATE.json',dict(status='FAIL_SENSITIVITY_RECOUNT_PRESERVED',failure=traceback.format_exc()));raise

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('config','manifest','prelaunch'):p.add_argument('--'+n,required=True)
    run(p.parse_args())
