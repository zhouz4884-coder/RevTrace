"""Read-only serving-declaration/library-state audit; no production imports."""
from pathlib import Path
import argparse,hashlib,json,platform,sys


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,required=True);p.add_argument('--native-audit',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--source-manifest',type=Path,required=True);a=p.parse_args()
    m=json.loads(a.source_manifest.read_text())
    for r in m['files']:assert sha(Path(__file__).parent/r['path'])==r['sha256']
    assert not a.out.exists();a.out.mkdir(parents=True)
    def put(n,x):
        with (a.out/n).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
    summary=json.loads((a.study/'SUMMARY.json').read_text());native=json.loads((a.native_audit/'RESULT.json').read_text())
    assert native['status']=='PASS_NATIVE_ASSET_INPUT_RENDER_AND_CLOCK_RECOUNT' and len(native['cells'])==4
    assert len(summary['completed'])==len(summary['rows'])==4
    env=dict(python=sys.version,platform=platform.platform());put('ENVIRONMENT.json',env)
    put('FREEZE.json',dict(experiment_id='REVTRACE-OWNER-RENDER-DECLARATION-POSTCHECK-20261028',source_commit=m['code_commit'],source_manifest_sha256=sha(a.source_manifest),study_summary_sha256=sha(a.study/'SUMMARY.json'),native_audit_result_sha256=sha(a.native_audit/'RESULT.json'),environment_sha256=sha(a.out/'ENVIRONMENT.json'),raw_result_location=str(a.out),aggregate_summary_location=str(a.out/'RESULT.json'),gate_decision_location=str(a.out/'GATE.json'),GPU_inference_calls=0))
    records=[]
    for name,row in zip(summary['completed'],summary['rows']):
        D=a.study/name;cfg0=json.loads((D/'attempt0/config.json').read_text());cfg1=json.loads((D/'attempt1/config.json').read_text());assert cfg0==cfg1
        spec=cfg1['authority_runtime']['render_contract']['owner_render_program'];assert spec['allowed_backends']==['native','light']
        init=json.loads((D/'attempt1/initialization.json').read_text());backend=row['cell']['restart_owner_render_backend']
        assert init['owner_render_backend']==backend and init['render_program_sha256']==spec['descriptor_sha256'] and init['render_use_sha256']==spec['use_manifest_sha256']
        trace=[json.loads(x) for x in (D/'attempt1/startup_profile.jsonl').read_text().splitlines()]
        observations=[x for x in trace if x.get('stage')=='owner-render-library-state'];assert len(observations)==1
        observed=observations[0];assert observed['backend']==backend
        if backend=='light':assert not any(observed['modules'].values())
        kill=json.loads((D/'KILL.json').read_text())['kill_perf'];old=kill+row['recovery']['RTO_old_all_durable_facts'];assert observed['observed_perf']<=old
        reference=next(r for r in native['cells'] if r['cell']==name)
        for k,v in reference['recounted_clocks'].items():assert abs(v-row['recovery'][k])<1e-7
        records.append(dict(cell=name,backend=backend,same_precrash_recovery_contract=True,modules=observed['modules'],implementation_ready_before_old_fact=True,independent_native_rows=reference['same_job_native_render_rows'],durable_text_bindings=reference['durable_text_bindings'],recounted_clocks=reference['recounted_clocks']))
    assert len(summary['pairs'])==2 and all(p['exact_fault_cut_match'] for p in summary['pairs'])
    result=dict(gate='PASS_DECLARED_RENDERER_REAL_COLD_AND_NATIVE_REPLAY',records=records,pairs=summary['pairs'],GPU_inference_calls=0,scope='single-repeat four-arm descriptive result, same new contract/intact storage, actual local Consumer; shared optimization not an exclusive scheduler or transcript-quality guarantee')
    put('RESULT.json',result);put('GATE.json',dict(gate=result['gate'],source_commit=m['code_commit'],cells=4,GPU_inference_calls=0));print(json.dumps(result),flush=True)


if __name__=='__main__':main()
