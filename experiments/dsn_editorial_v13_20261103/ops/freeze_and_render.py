"""Freeze clean figure source before each versioned editorial export."""
from pathlib import Path
import argparse, hashlib, json, platform, subprocess, sys
import matplotlib, fitz
E=Path(__file__).resolve().parents[1];R=E.parents[1];S=E/'figure_source'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,j):Path(p).write_text(json.dumps(j,indent=2)+'\n',encoding='utf-8')
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],stderr=subprocess.PIPE).decode().strip()
p=argparse.ArgumentParser();p.add_argument('--version',type=int,required=True);a=p.parse_args();tag=f'v{a.version}'
if not (S/'.git').exists():
 subprocess.run(['git','init',str(S)],check=True,capture_output=True)
 subprocess.run(['git','-C',str(S),'checkout','-b','codex/editorial-v13-figures'],check=True,capture_output=True)
git('add','--all')
if git('diff','--cached','--name-only'):
 git('-c','user.name=RevTrace artifact','-c','user.email=artifact@example.invalid','commit','-m','Freeze editorial v13 figure source '+tag)
assert not git('status','--porcelain','--untracked-files=all')
commit=git('rev-parse','HEAD');manifest=E/'packages'/f'FIGURE_SOURCE_{tag}.json';bundle=E/'packages'/f'FIGURE_SOURCE_{tag}.bundle'
assert not manifest.exists() and not bundle.exists()
rows=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in git('ls-files').splitlines()]
put(manifest,dict(code_commit=commit,files=rows,scope='Complete clean editor figure source; distinct from frozen NN execution source'))
git('bundle','create',str(bundle),'HEAD')
subprocess.run(['git','-C',str(R),'fetch',str(bundle),'HEAD:refs/archive/revtrace/dsn_editorial_v13_20261103/'+tag],check=True,capture_output=True)
assert subprocess.check_output(['git','-C',str(R),'cat-file','-t',commit],text=True).strip()=='commit'
root_gate=E/'figures'/f'ROOT_DEFAULT_SOURCE_GATE_{tag}.json'
subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--output',str(root_gate)],cwd=R,check=True,capture_output=True)
out=E/'figures'/f'EXPORT_{tag}';env=E/'figures'/f'ENVIRONMENT_{tag}.json'
put(env,dict(python=sys.version,executable=sys.executable,platform=platform.platform(),matplotlib=matplotlib.__version__,pymupdf=fitz.VersionBind,scope='Editorial rendering; no service execution'))
archive='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_editorial_v13_20261103/figure_exports_'+tag
record=dict(experiment_id='REVTRACE_V13_EDITORIAL_FIGURES_20261103_'+tag.upper(),actual_code_commit=commit,complete_source_manifest_sha256=sha(manifest),bundle_sha256=sha(bundle),config_sha256=sha(S/'CONFIG.json'),environment_sha256=sha(env),root_default_NN_gate_sha256=sha(root_gate),root_default_gate_scope='Original NN4f remains current; renderer is independently clean and manifest-frozen',raw_result_location=archive,bounded_local_export_location=str(out),aggregate_summary_location=archive+'/SUMMARY.json',gate_decision_location=archive+'/GATE.json',new_model_calls=0,raw_service_readers=0)
rec=E/'figures'/f'RUN_RECORD_{tag}.json';put(rec,record)
command=[sys.executable,'-B',str(S/'render.py'),'--manifest',str(manifest),'--out',str(out)]
r=subprocess.run(command,capture_output=True,cwd=S);(E/'figures'/f'RENDER_{tag}.txt').write_bytes(r.stdout+r.stderr)
record.update(command=command,returncode=r.returncode);put(rec,record)
if r.returncode:raise RuntimeError((r.stdout+r.stderr).decode(errors='replace')[-3000:])
record.update(summary_sha256=sha(out/'SUMMARY.json'),gate_sha256=sha(out/'GATE.json'));put(rec,record)
print(r.stdout.decode())
