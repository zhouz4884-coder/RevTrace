from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
p=argparse.ArgumentParser();p.add_argument('--version',type=int,default=1);p.add_argument('--include-plot',action='store_true');a=p.parse_args();version=f'v{a.version}'
H=Path(__file__).resolve().parent;D=H/('figure_data_source_'+version);D.mkdir(exist_ok=False)
shutil.copyfile(H/'summarize_results.py',D/'summarize_results.py')
if a.include_plot:shutil.copyfile(H/'plot_service_region.py',D/'plot_service_region.py')
(D/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf8')
(D/'PROTOCOL.md').write_text('CPU-only point-specific summary and publication figure data. Keep all 36 process repeats and all 3 workload points. Never pool different points into a P99. Exact complete selected histories are compared within each point and repeat. Endogenous relative-progress incidence is not a controlled speed ratio. No model calls.\n',encoding='utf8')
def git(*args):return subprocess.check_output(['git','-C',str(D),*args],text=True).strip()
subprocess.run(['git','-C',str(D),'init'],check=True,capture_output=True);git('config','core.autocrlf','false');git('checkout','-b','codex/dsn-service-stability-figure-data-'+version)
git('add','.');git('commit','-m','Freeze workload-specific timing stability figure data')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=dict(code_commit=git('rev-parse','HEAD'),scope='CPU-only figure data from independently accepted recorded service evidence',
    files=[dict(path=n,bytes=(D/n).stat().st_size,sha256=sha(D/n)) for n in git('ls-files').splitlines()])
with (H/('FIGURE_DATA_SOURCE_'+version+'.json')).open('x',encoding='utf8') as f:json.dump(m,f,indent=2);f.write('\n')
git('bundle','create',str(H/('FIGURE_DATA_SOURCE_'+version+'.bundle')),'HEAD')
assert not git('status','--porcelain','--untracked-files=all')
print(json.dumps(dict(code_commit=m['code_commit'],files=len(m['files']),manifest_sha256=sha(H/('FIGURE_DATA_SOURCE_'+version+'.json')),bundle_sha256=sha(H/('FIGURE_DATA_SOURCE_'+version+'.bundle')))))
