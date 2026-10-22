"""Independent fixed-matrix estimates; never changes serving or old decisions."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,math,sys
from row_stats_core import paired_bootstrap,stratified_quality_bootstrap

def main():
    B=Path(sys.argv[1]);O=B/'results/revtrace/row_completion_20261023';P=B/'projects/revtrace_online_admission_20261022'
    sys.path.insert(0,str(P));from analysis_core import median,good_audio
    assert json.loads((O/'FORMAL_ROW_SUMMARY_v1.json').read_text())['status']=='COMPLETE_ALL150_INDEPENDENT_AUDITS_PASS'
    D=O/'ROW_FORMAL_RESULTS_v1';D.mkdir(exist_ok=False)
    def clean(x):
        if isinstance(x,float) and not math.isfinite(x):return None
        if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
        if isinstance(x,(list,tuple)):return [clean(v) for v in x]
        return x
    def save(n,x):(D/n).write_text(json.dumps(clean(x),indent=2,allow_nan=False)+'\n')
    def csvsave(n,rows):
        with (D/n).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(clean(rows))
    def number(x):return None if x in ['',None,'None','null'] else float(x)
    cells=[];F=defaultdict(list);Q=defaultdict(dict);index={};groups=defaultdict(list);input_hashes={}
    for cohort,stage,expected in [('core','formal_row_v1',120),('validation','validation_row_v1',30)]:
        A=O/(stage+'_independent_audit_v2');audit=json.loads((A/'SUMMARY.json').read_text())
        assert audit['status']=='PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT' and audit['cells']==expected
        def rows(n):
            p=A/n;input_hashes[str(p.relative_to(O))]=hashlib.sha256(p.read_bytes()).hexdigest()
            with p.open() as f:return list(csv.DictReader(f))
        for r in rows('SERVICE_CELLS.csv'):
            method,delivery,load,traffic,rep=r['cell'].split('-');repeat=int(rep[1:])
            assert repeat in range(3) and (cohort!='validation' or delivery=='row')
            c={k:(number(v) if k not in ['cell','method','delivery','traffic'] else v) for k,v in r.items()}
            c.update(cohort=cohort,load=load,repeat=repeat);index[cohort,method,delivery,load,traffic,repeat]=c
            groups[cohort,load,traffic,method,delivery].append(c);cells.append(c)
        for r in rows('COMMON_FRONTIERS.csv'):
            F[cohort,r['cell']].append({**r,**{k:number(r[k]) for k in ['display','commit','certified_consumer','audio_seconds']}})
        for r in rows('SOURCE_QUALITY.csv'):
            Q[cohort,r['cell']][r['source_id']]={k:int(r[k]) for k in ['WER_errors','reference_words','CER_errors','reference_characters']}
    assert len(cells)==len(index)==150
    metrics=['Audio_Goodput_2_8','display_P99','commit_P99','GPU_J_audio_s','WER','CER','wall_seconds',
      'commits','physical_fsyncs','visible_audio_rollback_samples','erased_characters','capped_authority_admissions']
    table=[];grid=[]
    for key,cs in sorted(groups.items()):
        assert len(cs)==3
        out=dict(zip(['cohort','load','traffic','method','delivery'],key));out['repeats']=3
        for k in metrics:
            values=[math.inf if c[k] is None else c[k] for c in cs]
            out[k+'_median']=median(values);out[k+'_min']=min(values);out[k+'_max']=max(values)
        out['dual_P99_passes_2_8']=sum(c['display_P99'] is not None and c['commit_P99'] is not None and c['display_P99']<=2 and c['commit_P99']<=8 for c in cs)
        out['unfinished_sources']=sum(c['unfinished_sources'] for c in cs);table.append(out)
        for c in cs:
            for d in [2.,5.,8.]:
                for t in [4.,8.,12.,16.]:grid.append({'cohort':c['cohort'],'cell':c['cell'],'display_deadline_s':d,'commit_deadline_s':t,
                  'Audio_Goodput':good_audio(F[c['cohort'],c['cell']],d,t)/c['wall_seconds'],'secondary_not_primary_retuning':True})
    csvsave('GROUPS.csv',table);csvsave('DEADLINE_GRID.csv',grid)
    def arm(cohort,method,delivery,load,traffic):
        runs={}
        for repeat in range(3):
            c=index[cohort,method,delivery,load,traffic,repeat];name=c['cell']
            sources={s:dict(q,frontiers=[f for f in F[cohort,name] if f['source_id']==s]) for s,q in Q[cohort,name].items()}
            runs[repeat]={'wall':c['wall_seconds'],'energy':c['GPU_J_audio_s'],'sources':sources}
        return runs
    comparisons=[];gates=[]
    def compare(cohort,load,traffic,bm,bd,nm,nd,kind):
        a,b=arm(cohort,bm,bd,load,traffic),arm(cohort,nm,nd,load,traffic)
        effect=paired_bootstrap((a,b));ac=[index[cohort,bm,bd,load,traffic,r] for r in range(3)];bc=[index[cohort,nm,nd,load,traffic,r] for r in range(3)]
        positive=all(y['Audio_Goodput_2_8']>x['Audio_Goodput_2_8'] for x,y in zip(ac,bc))
        p,ci=effect['paired_median'],effect['paired_95_interval'];quality=ci['WER'][1]<=.005 and ci['CER'][1]<=.005
        g={'quality_noninferiority_0_5pp':quality,'all_three_paired_Goodput_deltas_positive':positive,
          'primary_Goodput_gate':bool(quality and p['goodput']>=.05 and ci['goodput'][0]>0 and positive),
          'zero_new_predicate_or_consumer_violations_in_independent_audit':True,
          'no_unfinished_requests':all(c['unfinished_sources']==0 for c in ac+bc),
          'all_both_population_P99_passes':all(c['display_P99'] is not None and c['commit_P99'] is not None and c['display_P99']<=2 and c['commit_P99']<=8 for c in ac+bc)}
        identity={'cohort':cohort,'load':load,'traffic':traffic,'baseline':bm+'-'+bd,'new':nm+'-'+nd,'kind':kind}
        comparisons.append({**identity,'effect':effect,'gates':g});gates.append({**identity,**g,**{k+'_paired_change':v for k,v in p.items()}})
        print('BOOTSTRAP',identity,flush=True)
    policies=['fine','dgft','standard','strict','score']
    for load in ['sync16','cohort8']:
        for traffic in ['clean','F2']:
            for method in policies:compare('core',load,traffic,method,'batch',method,'row','shared_executor_return')
            for baseline in ['fine','standard','strict','score']:compare('core',load,traffic,baseline,'row','dgft','row','equally_equipped_cross_policy')
    for traffic in ['clean','F2']:
        for baseline in ['fine','standard','strict','score']:compare('validation','sync16',traffic,baseline,'row','dgft','row','independent_validation_same_capability')
    quality32=[]
    for traffic in ['clean','F2']:
        for baseline in ['fine','standard','strict','score']:
            pair=[(arm(cohort,baseline,'row','sync16',traffic),arm(cohort,'dgft','row','sync16',traffic)) for cohort in ['core','validation']]
            quality32.append({'baseline':baseline+'-row','new':'dgft-row','traffic':traffic,**stratified_quality_bootstrap(pair)})
    save('PAIRED_COMPARISONS.json',comparisons);csvsave('GATE_DECISIONS.csv',gates);save('QUALITY32_STRATIFIED.json',quality32)
    primary=next(x for x in comparisons if x['cohort']=='core' and x['load']=='sync16' and x['traffic']=='F2' and x['baseline']=='dgft-batch' and x['new']=='dgft-row')
    save('GONOGO.json',{'status':'COMPLETE_FIXED_ROW_MATRIX_STATISTICS','primary_generic_executor_gate':primary['gates'],
      'independent_C2_algorithm_increment':'NO_GO_NO_DISTINCT_ADDITIONAL_COORDINATION_RULE_IMPLEMENTED',
      'generic_executor_benefit_not_a_proof_of_new_scheduling_algorithm':True,'formal_core_cells':120,'validation_cells':30,
      'old72_and_original_negative_gates_preserved':True,'all_negative_comparisons_retained':True,
      'null_interval_endpoint_means_unbounded_or_missing_not_zero':True,'Rescue_requires_separate_actual_slack_and_generation_cost_gate':True})
    save('INPUT_HASHES.json',input_hashes)
    print('COMPLETE_FIXED_ROW_MATRIX_STATISTICS',flush=True)

if __name__=='__main__':main()
