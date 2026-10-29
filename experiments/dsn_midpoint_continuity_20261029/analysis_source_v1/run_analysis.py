"""Audited CPU-only runner for this bounded study's independent recounters."""
from pathlib import Path
import argparse,hashlib,json,os,platform,subprocess,sys,time

HERE=Path(__file__).resolve().parent
PROGRAMS={'critical_path':'critical_path.py','aggregate':'aggregate_service_v5.py',
    'opportunities':'interaction_opportunities_v1.py','usefulness':'canonical_usefulness_v1.py'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def put(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def git(*args):return subprocess.check_output(['git','-C',str(HERE),*args],text=True).strip()
def validate(m):
    assert git('rev-parse','HEAD')==m['code_commit'] and not git('status','--porcelain','--untracked-files=all')
    assert git('config','--get','core.autocrlf')=='false'
    assert set(git('ls-files').splitlines())=={r['path'] for r in m['files']}
    for r in m['files']:assert sha(HERE/r['path'])==r['sha256'] and (HERE/r['path']).stat().st_size==r['bytes']

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--plan-sha256',required=True)
    p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--components',nargs='+',choices=list(PROGRAMS),default=list(PROGRAMS));a=p.parse_args()
    assert sha(a.plan)==a.plan_sha256
    source=read(a.source_manifest);validate(source);plan=read(a.plan);out=a.output;out.mkdir(parents=True,exist_ok=False)
    raw=[c['argv'][c['argv'].index('--out')+1] for c in plan['cells']]
    put(out/'CONFIG.json',dict(experiment_id=plan['experiment_id']+'-CPU-RECOUNT',frozen_plan=str(a.plan),
        frozen_plan_sha256=a.plan_sha256,components=a.components,expected_cells=len(plan['cells']),GPU_calls=0))
    put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),hostname=platform.node()))
    put(out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id']+'-CPU-RECOUNT',code_commit=source['code_commit'],
        source_manifest_sha256=sha(a.source_manifest),measured_neural_commit=plan['code_commit'],
        frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),
        environment_record=str(out/'ENVIRONMENT.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),
        raw_result_location=raw,aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    results={}
    for name in a.components:
        argv=[sys.executable,'-B',str(HERE/PROGRAMS[name]),'--plan',str(a.plan),'--output',str(out/name)]
        with (out/(name+'.log')).open('x') as log:r=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT)
        summary_name='ANALYSIS_RECORD.json' if name=='opportunities' else 'SUMMARY.json'
        s=read(out/name/summary_name) if (out/name/summary_name).exists() else None
        accepted=r.returncode==0 and s is not None and s.get('status') in (
            'OFFLINE_RECOUNT_COMPLETE','OFFLINE_RETROSPECTIVE_RECOUNT_COMPLETE','COMPLETE_FROZEN_PLAN_AGGREGATION')
        # Aggregate's exact status is versioned; never infer completeness from rc.
        if name=='aggregate':accepted=r.returncode==0 and s is not None and s.get('accepted_cells')==len(plan['cells'])
        if name=='usefulness':
            accepted=r.returncode==0 and s is not None and s.get('recounted_cells')==len(plan['cells']) and s.get('formally_source_revalidated_cells')==len(plan['cells'])
        if name=='opportunities':
            accepted=r.returncode==0 and s is not None and s.get('cells_recounted')==len(plan['cells']) and s.get('gate')=='OFFLINE_RECOUNT_COMPLETE'
        results[name]=dict(argv=argv,returncode=r.returncode,accepted=accepted,summary=s)
    validate(source)
    put(out/'SUMMARY.json',results);put(out/'GATE.json',dict(gate='PASS_CPU_RECOUNTS' if all(r['accepted'] for r in results.values()) else 'FAIL_PRESERVED',GPU_calls=0))
    print(json.dumps(dict(output=str(out),gate=read(out/'GATE.json'))))

if __name__=='__main__':main()
