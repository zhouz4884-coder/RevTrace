from pathlib import Path
import argparse,hashlib,json,platform,subprocess,sys
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    import run_analysis
    m=json.loads(a.manifest.read_bytes());run_analysis.validate(m);config=json.loads(a.config.read_bytes())
    out=a.output;out.mkdir(exist_ok=False)
    put(out/'CONFIG.json',config);put(out/'ENVIRONMENT.json',dict(python=sys.version,platform=platform.platform(),GPU_calls=0))
    put(out/'RUN_RECORD.json',dict(experiment_id=config['experiment_id'],code_commit=m['code_commit'],source_manifest_sha256=sha(a.manifest),
        frozen_config_sha256=sha(a.config),environment_record=str(out/'ENVIRONMENT.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),
        raw_result_location=str(out/'RAW.log'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    r=subprocess.run([sys.executable,'-B','-m','unittest','-v','test_continuity','test_midpoint'],cwd=HERE,capture_output=True,text=True)
    (out/'RAW.log').write_text(r.stdout+r.stderr,encoding='utf8',newline='\n')
    put(out/'SUMMARY.json',dict(status='PASS' if r.returncode==0 else 'FAIL_PRESERVED',returncode=r.returncode,expected_controls=17,GPU_calls=0))
    put(out/'GATE.json',dict(gate='PASS_17_SYNTHETIC_CPU_CONTROLS' if r.returncode==0 else 'FAIL_CPU_CONTROLS',GPU_calls=0))
    run_analysis.validate(m)
    print(json.dumps(dict(output=str(out),returncode=r.returncode)));raise SystemExit(r.returncode)
if __name__=='__main__':main()
