"""Prepared launch only: root allocation and preceding completed scopes required."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_dsn_midpoint_continuity_20261029';N=B/'projects/revtrace_physical_retirement_20261028'
S=N/'source_v3';O=B/'results/revtrace/physical_retirement_20261028'
PLAN_SHA='fb344f88774b8cdae15af213e66f296adcaf4632fa982383e730f92a18023b84'
RUNTIME_COMMIT='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf'
RUNTIME_SHA='19547df369c2899d4cb0eec49d137eff7f160802668072033ae9197565771625'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--allocation',type=Path,required=True);a=ap.parse_args()
    allocation=load(a.allocation)
    assert allocation['experiment_id']=='REVTRACE-DSN-MIDPOINT-CONTINUITY-20261029-V1' and allocation['root_allocated'] is True
    expected={'joint24_execution','joint24_analysis','native_prescribed_scope_decision','native_analysis'}
    prereq=allocation['prerequisite_evidence'];assert {x['label'] for x in prereq}==expected
    for item in prereq:
        q=Path(item['path']).resolve();assert q.is_relative_to(B.resolve())
        assert sha(q)==item['sha256']
        record=load(q)
        for key,value in item['required_json_fields'].items():assert record.get(key)==value
    receipt=allocation['local_current_preflight']
    assert receipt['gate']=='SOURCE_IDENTITY_PASS' and receipt['code_commit']==RUNTIME_COMMIT and receipt['manifest_sha256']==RUNTIME_SHA
    assert allocation['native_scope_executed'] in ('two_witnesses_gate_closed_no_formal','two_witnesses_gate_passed_all12_formal_complete')
    import run_analysis
    run_analysis.validate(load(P/'ANALYSIS_SOURCE_v1.json'))
    plan=P/'PLAN_v1_FROZEN.json';assert sha(plan)==PLAN_SHA
    runtime=N/'SOURCE_v3.json';assert sha(runtime)==RUNTIME_SHA
    m=load(runtime);assert m['code_commit']==RUNTIME_COMMIT
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==RUNTIME_COMMIT
    assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=S,text=True).strip()
    tracked=set(subprocess.check_output(['git','ls-files'],cwd=S,text=True).splitlines())
    assert tracked=={r['path'] for r in m['files']}
    for r in m['files']:assert (S/r['path']).stat().st_size==r['bytes'] and sha(S/r['path'])==r['sha256']
    assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    campaign=load(plan);assert len(campaign['cells'])==12
    for c in campaign['cells']:assert not Path(c['output']).exists()
    py=str(B/'envs/revbatch-cu128/bin/python');out=O/'dsn_midpoint_controller_v1'
    argv=[py,'-B','-u',str(S/'retirement_campaign.py'),'--plan',str(plan),'--plan-sha256',PLAN_SHA,'--source-manifest',str(runtime),'--out',str(out)]
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',HF_HOME=str(B/'cache/huggingface'),XDG_CACHE_HOME=str(B/'cache'),TMPDIR=str(B/'tmp/physical_retirement_20261028'))
    log=O/'dsn_midpoint_controller_v1.log';handle=P/'GPU_HANDLE_v1.json'
    assert not out.exists() and not log.exists() and not handle.exists()
    with log.open('x') as f:child=subprocess.Popen(argv,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    proc=Path('/proc',str(child.pid));record=dict(experiment_id=campaign['experiment_id'],pid=child.pid,
        start_ticks=(proc/'stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=sha(proc/'cmdline'),
        argv=argv,launched_unix=time.time(),result=str(out),log=str(log),planned_cells=12,
        allocation_file=str(a.allocation),allocation_sha256=sha(a.allocation),actual_neural_source_commit=RUNTIME_COMMIT,
        resource_note='root allocated after both preceding scopes; no heavy IO/CPU or other model during timed cells')
    with handle.open('x',encoding='utf8') as f:json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps(record))
if __name__=='__main__':main()
