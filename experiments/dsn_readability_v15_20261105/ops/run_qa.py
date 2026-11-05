from pathlib import Path
import argparse,hashlib,json,platform,subprocess,sys
import fitz
E=Path(__file__).resolve().parents[1];R=E.parents[1];S=E/'qa_source';P=R/'Paper_DSN/revisions/20261105_dsn2027_release_v15';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):Path(p).write_bytes((json.dumps(x,indent=2)+'\n').encode())
a=argparse.ArgumentParser();a.add_argument('--version',default='v1');args=a.parse_args();version=args.version
(S/'.gitattributes').write_bytes(b'* -text\n')
if not (S/'.git').exists():
 subprocess.run(['git','init',str(S)],capture_output=True,check=True)
 subprocess.run(['git','-C',str(S),'checkout','-b','codex/v15-readability-qa'],capture_output=True,check=True)
g=lambda *a:subprocess.check_output(['git','-C',str(S),*a],stderr=subprocess.PIPE).decode().strip()
g('add','--all')
if g('diff','--cached','--name-only'):g('-c','user.name=RevTrace artifact','-c','user.email=artifact@example.invalid','commit','-m','Freeze v15 readability identity and cold-build verification '+version)
commit=g('rev-parse','HEAD');mp=E/'packages'/('QA_SOURCE_'+version+'.json');bundle=E/'packages'/('QA_SOURCE_'+version+'.bundle');put(mp,dict(code_commit=commit,files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in g('ls-files').splitlines()]))
g('bundle','create',str(bundle),'HEAD');subprocess.run(['git','-C',str(R),'fetch',str(bundle),'HEAD:refs/archive/revtrace/dsn_readability_v15_20261105/qa_'+version],capture_output=True,check=True)
env=E/'paper_qa'/('ENVIRONMENT_'+version+'.json');put(env,dict(python=sys.version,executable=sys.executable,platform=platform.platform(),pymupdf=fitz.VersionBind,scope='CPU editorial verification only'))
cfg=E/'paper_qa'/('CONFIG_'+version+'.json');helper='C:/Users/LENOVO/.agents/skills/latex-paper-en/scripts/compile.py'
put(cfg,dict(version=version,root=str(R),study=str(E),paper=str(P),old_paper=str(R/'Paper_DSN/revisions/20261104_dsn2027_release_v14'),pdf_sha256=sha(P/'main.pdf'),compile_helper=helper,compile_helper_sha256=sha(helper)))
rec=E/'paper_qa'/('RUN_RECORD_'+version+'.json');record=dict(experiment_id='REVTRACE_V15_READABILITY_SOURCE_COLD_QA_20261105_'+version.upper(),code_commit=commit,source_manifest_sha256=sha(mp),config_sha256=sha(cfg),environment_sha256=sha(env),raw_result_location='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_readability_v15_20261105/editorial_qa_'+version,bounded_local_output=str(E/'paper_qa'/('FINAL_'+version)),summary_path='editorial_qa_'+version+'/SUMMARY.json',decision_path='editorial_qa_'+version+'/GATE.json',new_model_calls=0,new_GPU_runs=0);put(rec,record)
subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--output',str(E/('ROOT_NOARG_QA_'+version+'.json'))],capture_output=True,cwd=R,check=True)
r=subprocess.run([sys.executable,'-B',str(S/'validate.py'),'--config',str(cfg),'--manifest',str(mp)],capture_output=True,cwd=S);(E/'paper_qa'/('QA_OUTPUT_'+version+'.txt')).write_bytes(r.stdout+r.stderr);record['returncode']=r.returncode;put(rec,record)
if r.returncode:raise RuntimeError((r.stdout+r.stderr).decode(errors='replace')[-2500:])
record.update(summary_sha256=sha(E/'paper_qa'/('FINAL_'+version)/'SUMMARY.json'),gate_sha256=sha(E/'paper_qa'/('FINAL_'+version)/'GATE.json'));put(rec,record);print(r.stdout.decode())
