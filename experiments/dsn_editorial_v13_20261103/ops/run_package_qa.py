from pathlib import Path
import hashlib,json,platform,shutil,subprocess,sys
import matplotlib,fitz
E=Path(__file__).resolve().parents[1];R=E.parents[1];S=E/'package_qa_source';Q=E/'paper_qa';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,j):Path(p).write_text(json.dumps(j,indent=2)+'\n',encoding='utf-8')
for name in ['reproduce_figures.py','verify_reported_statistics.py']:shutil.copyfile(E/'ops'/name,S/name)
(S/'.gitattributes').write_text('* -text\n',encoding='utf-8')
subprocess.run(['git','init',str(S)],check=True,capture_output=True)
git=lambda *args:subprocess.check_output(['git','-C',str(S),*args],stderr=subprocess.PIPE).decode().strip()
git('checkout','-b','codex/anonymous-package-qa');git('add','--all');git('-c','user.name=RevTrace artifact','-c','user.email=artifact@example.invalid','commit','-m','Freeze anonymous v13 evidence validation and reproduction code')
assert not git('status','--porcelain','--untracked-files=all');commit=git('rev-parse','HEAD')
manifest=E/'packages/PACKAGE_QA_SOURCE_v1.json';bundle=E/'packages/PACKAGE_QA_SOURCE_v1.bundle'
put(manifest,dict(code_commit=commit,files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in git('ls-files').splitlines()]))
git('bundle','create',str(bundle),'HEAD')
subprocess.run(['git','-C',str(R),'fetch',str(bundle),'HEAD:refs/archive/revtrace/dsn_editorial_v13_20261103/package_qa_v1'],check=True,capture_output=True)
root_gate=Q/'PACKAGE_QA_ROOT_DEFAULT_SOURCE_GATE.json'
subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--output',str(root_gate)],cwd=R,check=True,capture_output=True)
archive=R/'Paper_DSN/revisions/20261103_dsn2027_release_v13/RevTrace_DSN2027_anonymous_evidence_v13.zip'
config=Q/'ANONYMOUS_EVIDENCE_QA_CONFIG.json';env=Q/'ANONYMOUS_EVIDENCE_QA_ENVIRONMENT.json';out=Q/'anonymous_evidence_check'
put(config,dict(archive=str(archive),archive_sha256=sha(archive),frozen_figure_export=str(E/'figures/EXPORT_v2')))
put(env,dict(python=sys.version,executable=sys.executable,platform=platform.platform(),matplotlib=matplotlib.__version__,pymupdf=fitz.VersionBind))
record=dict(experiment_id='REVTRACE_V13_ANONYMOUS_PACKAGE_FRESH_EXTRACT_20261103_V1',actual_code_commit=commit,source_manifest_sha256=sha(manifest),frozen_config_sha256=sha(config),environment_sha256=sha(env),root_default_source_gate_sha256=sha(root_gate),raw_result_location='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_editorial_v13_20261103/anonymous_package_qa_v1',bounded_local_output=str(out),aggregate_summary=str(out/'SUMMARY.json'),gate_decision=str(out/'GATE.json'),new_model_calls=0,raw_service_readers=0)
rec=Q/'ANONYMOUS_EVIDENCE_QA_RUN_RECORD.json';put(rec,record)
r=subprocess.run([sys.executable,'-B',str(S/'check_package.py'),'--config',str(config),'--manifest',str(manifest),'--out',str(out)],capture_output=True,cwd=S)
(Q/'ANONYMOUS_EVIDENCE_QA_OUTPUT.txt').write_bytes(r.stdout+r.stderr)
record['returncode']=r.returncode;put(rec,record)
if r.returncode:raise RuntimeError((r.stdout+r.stderr).decode(errors='replace')[-2500:])
record.update(summary_sha256=sha(out/'SUMMARY.json'),gate_sha256=sha(out/'GATE.json'));put(rec,record);print(r.stdout.decode())
