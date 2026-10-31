"""Independent all-offered native event recount with original f0 quantiles.

No runtime, model, selector, scheduler or native-service metric code is imported.
The linear interpolation and infinity rule reproduce f0 x_service_metrics.py.
"""
import argparse,datetime,hashlib,json,math,pathlib,platform,subprocess,sys
R=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def lines(p):return [json.loads(s) for s in pathlib.Path(p).read_text(encoding='utf-8').splitlines() if s.strip()]
def hfile(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def quantile(xs,q):
    xs=sorted(xs)
    if not xs:return math.inf
    pos=(len(xs)-1)*q;i=int(pos);j=min(i+1,len(xs)-1)
    if math.isinf(xs[j]):return math.inf
    return xs[i]+(xs[j]-xs[i])*(pos-i)
def finite(x):return x if math.isfinite(x) else None
def cell_metrics(cell):
    out=pathlib.Path(cell['out']);c=read(out/'CONFIG.json');origin=read(out/'ORIGIN.json')['origin_perf'];rows=lines(out/'consumer.jsonl')
    offered=[]
    for source in c['settings']['sources']:
        sid=source['source_id'];n=source['frames'];observed=[r for r in rows if r['source_id']==sid];last=0
        if not observed:raise ValueError('source has no actual Consumer events')
        if any(b['observed']<a['observed'] for a,b in zip(observed,observed[1:])):raise ValueError('actual Consumer clock order')
        for F in list(range(8000,n,8000))+[n]:
            ready=origin+F/16000
            D=next((r['observed']-ready for r in observed if r['observed']>=ready and r['visible_frontier']>=F),math.inf)
            C=next((r['observed']-ready for r in observed if r['observed']>=ready and r['certified_frontier']>=F),math.inf)
            offered.append(dict(source_id=sid,F=F,audio_seconds=(F-last)/16000,D=D,C=C));last=F
    ds=[r['D'] for r in offered];cs=[r['C'] for r in offered];d99=quantile(ds,.99);c99=quantile(cs,.99)
    missingD=sum(not math.isfinite(x) for x in ds);missingC=sum(not math.isfinite(x) for x in cs)
    return dict(cell_id=cell['cell_id'],stage=cell['stage'],cohort=cell['cohort'],arm=cell['arm'],repeat=cell['repeat'],
        offered_frontiers=len(offered),offered_audio_seconds=sum(r['audio_seconds'] for r in offered),
        primary_linear_all_offered_D99=finite(d99),primary_linear_all_offered_C99=finite(c99),
        original_quantile_test_pass=d99<=2. and c99<=8.,complete_coverage_and_original_quantile_pass=not missingD and not missingC and d99<=2. and c99<=8.,
        D2_misses_all_offered=sum(x>2. for x in ds),C8_misses_all_offered=sum(x>8. for x in cs),
        missing_D_frontiers=missingD,missing_C_frontiers=missingC,D_max=finite(max(ds,default=math.inf)),C_max=finite(max(cs,default=math.inf)),
        dual_deadline_audio_credit_seconds=sum(r['audio_seconds'] for r in offered if r['D']<=2. and r['C']<=8.),
        raw_inputs=dict(config_sha256=hfile(out/'CONFIG.json'),origin_sha256=hfile(out/'ORIGIN.json'),consumer_sha256=hfile(out/'consumer.jsonl')))
def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
    commit=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()
    if subprocess.check_output(['git','-C',str(R),'status','--porcelain','--untracked-files=all'],text=True).strip():raise ValueError('analysis source must be clean and frozen')
    a.out.mkdir(parents=True,exist_ok=False);plan=read(a.plan)
    record=dict(experiment_id='SC_NATIVE_PRIMARY_QUANTILES_V1',code_commit=commit,analysis_started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        frozen_plan=str(a.plan),frozen_plan_sha256=hfile(a.plan),environment=dict(python=sys.version,platform=platform.platform()),
        raw_result_location='per-cell actual native Consumer events on designated experiment disk',aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json'),
        primary_rule='f0 linear interpolation including positive infinity for missing offered-frontier observations; nearest-rank is auxiliary only')
    (a.out/'RUN_RECORD.json').write_text(json.dumps(record,indent=2));results=[];failures=[]
    for cell in plan['cells']:
        try:results.append(cell_metrics(cell))
        except Exception as e:failures.append(dict(cell_id=cell['cell_id'],error=type(e).__name__+': '+str(e)))
    status='PASS_ALL_OFFERED_NATIVE_PRIMARY_QUANTILES_RECOUNTED' if not failures else 'INCOMPLETE_NATIVE_QUANTILE_RECOUNT_PRESERVED'
    result=dict(status=status,planned_cells=len(plan['cells']),recounted_cells=len(results),failures=failures,cells=results)
    (a.out/'SUMMARY.json').write_text(json.dumps(result,indent=2));(a.out/'GATE.json').write_text(json.dumps(dict(status=status),indent=2));print(json.dumps({k:v for k,v in result.items() if k!='cells'},indent=2))
if __name__=='__main__':main()
