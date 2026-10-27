"""Run frozen TLC cuts and TLAPS source, one CPU worker, on the 8 TB disk."""
from pathlib import Path
import argparse,hashlib,json,os,platform,re,shutil,signal,subprocess,time

B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
T=B/'tools/revtrace_formal_20261027'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--stage',choices=['pilot','full'],default='full');a=p.parse_args()
    S=Path(__file__).resolve().parent;R=a.output.resolve()
    allowed=(B/'results/revtrace/freeze_boundary_20261027/formal').resolve()
    if allowed not in R.parents:raise ValueError('result path outside formal study root')
    if R.exists():raise FileExistsError(R)
    m=json.loads(a.manifest.read_text());runset=json.loads((S/'RUNS.json').read_text())
    for f in m['files']:
        if sha(S/f['path'])!=f['sha256']:raise ValueError('frozen source changed '+f['path'])
    tools=json.loads((T/'TOOLING_RECEIPT.json').read_text())
    if tools['status']!='PASS_TOOLING_ONLY':raise ValueError('tool smoke gate missing')
    for name,wanted in tools['binary_sha256'].items():
        if sha(name)!=wanted:raise ValueError('tool binary changed '+name)
    R.mkdir(parents=True);(R/'tmp').mkdir()
    env=dict(os.environ);env['TMPDIR']=str(R/'tmp');env['OMP_NUM_THREADS']='1'
    tlapm=Path(tools['tlapm']);env['PATH']=str(tlapm.parent)+os.pathsep+env.get('PATH','')
    environment=dict(python=platform.python_version(),platform=platform.platform(),
       tool_receipt_sha256=sha(T/'TOOLING_RECEIPT.json'),tool_versions={'java':'17.0.17+10','TLC':'2.19 release1.7.4','TLAPS':'1.5.0'},
       cpu_workers=1,java_heap_mib=1024,per_tlc_timeout_seconds=120,per_tlaps_timeout_seconds=180)
    put(R/'ENVIRONMENT.json',environment)
    selected=runset['runs'] if a.stage=='full' else [x for x in runset['runs'] if x['id'] in {'admission-safe','selection-latest-safe-negative','wait-safe-fair'}]
    put(R/'FREEZE.json',dict(experiment_id='REVTRACE-FORMAL-20261027-'+a.stage,source_commit=m['code_commit'],
       source_manifest_sha256=sha(a.manifest),environment_sha256=sha(R/'ENVIRONMENT.json'),runs=selected,
       proof_modules=runset['proof_modules'],raw_result_location=str(R),aggregate_summary_location=str(R/'SUMMARY.json'),
       gate_decision_location=str(R/'GATE.json'),scope='Actual TLC finite checks and separate parameterized TLAPS obligations; no GPU or production refinement'))
    results=[]
    def execute(label,args,folder,timeout):
        started=time.perf_counter()
        with (folder/'stdout.txt').open('x') as out,(folder/'stderr.txt').open('x') as err:
            child=subprocess.Popen([str(x) for x in args],cwd=folder,env=env,stdout=out,stderr=err,start_new_session=True)
            put(folder/'OWNED_PROCESS.json',dict(pid=child.pid,argv=[str(x) for x in args],source_commit=m['code_commit']))
            try:code=child.wait(timeout=timeout);timed_out=False
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
                code=child.returncode;timed_out=True
        text=(folder/'stdout.txt').read_text()+(folder/'stderr.txt').read_text()
        return dict(label=label,exit_code=code,timed_out=timed_out,elapsed_seconds=time.perf_counter()-started,
                    stdout_sha256=sha(folder/'stdout.txt'),stderr_sha256=sha(folder/'stderr.txt')),text
    for x in selected:
        d=R/x['id'];d.mkdir()
        for source in S.glob('*.tla'):shutil.copy2(source,d/source.name)
        shutil.copy2(S/x['config'],d/x['config'])
        args=[tools['java'],'-Djava.io.tmpdir='+str(R/'tmp'),'-XX:+UseParallelGC','-Xmx1g','-cp',T/'downloads/tla2tools-1.7.4.jar',
              'tlc2.TLC','-workers','1','-config',x['config'],'-metadir',d/'states',x['module']]
        r,text=execute(x['id'],args,d,120);r.update(x)
        if x['expected']=='PASS':r['matched_expected']=r['exit_code']==0 and 'No error has been found' in text
        else:r['matched_expected']=r['exit_code']!=0 and ('Invariant '+x['target']+' is violated') in text
        counts=re.search(r'([\d,]+) states generated, ([\d,]+) distinct states found',text)
        if counts:r['generated_states']=int(counts[1].replace(',',''));r['distinct_states']=int(counts[2].replace(',',''))
        put(d/'RESULT.json',r);results.append(r);put(R/'PROGRESS.json',dict(completed=results,status='RUNNING'))
        print(json.dumps(r),flush=True)
        if not r['matched_expected']:
            put(R/'STOP.json',dict(reason='Unexpected TLC outcome; retain raw source and counterexample',result=r));break
    proofs=[]
    for module in runset['proof_modules']:
        d=R/('tlaps-'+module.removesuffix('.tla') if hasattr(module,'removesuffix') else 'tlaps-'+module[:-4]);d.mkdir()
        for source in S.glob('*.tla'):shutil.copy2(source,d/source.name)
        r,text=execute(module,[tlapm,'--threads','1','--nofp','--timing',module],d,180)
        proved=[int(x) for x in re.findall(r'All (\d+) obligations? proved',text)]
        r['proved_obligations']=proved;r['matched_expected']=r['exit_code']==0 and bool(proved) and max(proved)>0
        put(d/'RESULT.json',r);proofs.append(r);print(json.dumps(r),flush=True)
    success=len(results)==len(selected) and all(r['matched_expected'] for r in results+proofs)
    put(R/'SUMMARY.json',dict(status='COMPLETE_EXPECTED' if success else 'INCOMPLETE_OR_FAILED',source_commit=m['code_commit'],
        stage=a.stage,TLC=results,TLAPS=proofs,scope='Proof checks are only of the named frozen TLA modules'))
    put(R/'GATE.json',dict(gate='PASS_SCOPED_FORMAL' if success else 'REPAIR_REQUIRED',source_commit=m['code_commit']))
    print(json.dumps(dict(status='COMPLETE_EXPECTED' if success else 'REPAIR_REQUIRED',TLC=len(results),TLAPS=len(proofs))),flush=True)

if __name__=='__main__':main()
