"""Run bounded specification controls and exploration; never starts neural code."""
import argparse,datetime,hashlib,json,pathlib,platform,subprocess,sys,unittest,io,traceback
from model import explore

def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument("--plan",type=pathlib.Path,required=True)
    p.add_argument("--manifest",type=pathlib.Path,required=True);p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args();root=pathlib.Path(__file__).resolve().parent
    plan=json.loads(a.plan.read_bytes());manifest=json.loads(a.manifest.read_bytes())
    commit=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    assert commit==manifest["source_commit"]==plan["source_commit"]
    assert not subprocess.check_output(["git","-C",str(root),"status","--porcelain","--untracked-files=all"],text=True).strip()
    tracked=set(subprocess.check_output(["git","-C",str(root),"ls-files"],text=True).splitlines())
    assert tracked=={r["path"] for r in manifest["files"]}
    for r in manifest["files"]:
        path=root/r["path"];assert path.stat().st_size==r["bytes"] and sha(path)==r["sha256"]
    assert sha(a.manifest)==plan["source_manifest_sha256"]
    a.out.mkdir(parents=True,exist_ok=False)
    def put(name,value):(a.out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    put("CONFIG.json",plan)
    put("ENVIRONMENT.json",dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
        execution="finite symbolic CPU specification only",model_calls=0,GPU_calls=0))
    put("RUN_RECORD.json",dict(experiment_id=plan["experiment_id"],code_commit=commit,
        frozen_config=str(a.out/"CONFIG.json"),frozen_config_sha256=sha(a.out/"CONFIG.json"),
        environment_record=str(a.out/"ENVIRONMENT.json"),environment_record_sha256=sha(a.out/"ENVIRONMENT.json"),
        raw_result_location=str(a.out/"CPU_CONTROLS.log"),aggregate_summary_location=str(a.out/"SUMMARY.json"),
        gate_decision_location=str(a.out/"GATE.json"),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope=plan["scope"]))
    try:
        stream=io.StringIO();tests=unittest.defaultTestLoader.discover(str(root),pattern="test_*.py")
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(tests)
        (a.out/"CPU_CONTROLS.log").write_text(stream.getvalue(),encoding="utf8")
        if not result.wasSuccessful() or result.skipped:
            raise AssertionError("source specification controls failed; raw log preserved")
        profiles={}
        for name,bounds in plan["profiles"].items():
            profiles[name]=explore(**bounds)
            put("PROGRESS.json",dict(completed_profiles=list(profiles),tests_passed=result.testsRun))
        for r in manifest["files"]:assert sha(root/r["path"])==r["sha256"]
        put("PROFILES.json",profiles)
        summary=dict(status="PASS_BOUNDED_SPECIFICATION_REFINEMENT_AND_COUNTEREXAMPLE_CONTROLS",
            source_commit=commit,source_manifest_sha256=sha(a.manifest),tests=result.testsRun,skipped=0,
            profiles=profiles,model_calls=0,GPU_calls=0,
            evidence_tier="finite symbolic specification plus source correspondence; NOT deployed serving, natural prevalence, arbitrary GPU equality, unbounded liveness, or whole Python/CUDA verification",
            final_runtime_mechanical_extraction=False,scope=plan["scope"])
        put("SUMMARY.json",summary);put("GATE.json",summary);print(json.dumps(summary,indent=2))
    except BaseException:
        (a.out/"failure.txt").write_text(traceback.format_exc(),encoding="utf8")
        put("GATE.json",dict(status="FAIL_SPECIFICATION_CONTROL_OR_MODEL_PRESERVED",source_commit=commit,
            model_calls=0,GPU_calls=0))
        raise

if __name__=="__main__":main()

