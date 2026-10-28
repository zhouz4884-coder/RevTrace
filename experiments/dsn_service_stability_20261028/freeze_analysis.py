"""Freeze CPU analysis source separately from unchanged neural execution source."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
p=argparse.ArgumentParser();p.add_argument('--version',type=int,default=1);a=p.parse_args();version=f'v{a.version}'
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];D=HERE/('analysis_source_'+version);D.mkdir(exist_ok=False)
files={HERE/'critical_path.py':'critical_path.py',HERE/'run_analysis.py':'run_analysis.py',
    ROOT/'experiments/physical_retirement_20261028/analysis_tools/frozen_aggregate_v2/aggregate_service_v5.py':'aggregate_service_v5.py',
    ROOT/'experiments/physical_retirement_20261028/analysis_tools/frozen_analysis_v1/canonical_usefulness_v1.py':'canonical_usefulness_v1.py',
    ROOT/'experiments/physical_retirement_20261028/analysis_tools/frozen_analysis_v1/interaction_opportunities_v1.py':'interaction_opportunities_v1.py'}
for src,name in files.items():shutil.copyfile(src,D/name)
(D/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf8')
(D/'PROTOCOL.md').write_text('Independent CPU-only analysis for the frozen DSN service operating-region study. Neural runtime remains f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf. Raw prior failures are retained. No model calls or metric selection. Critical-path partition is descriptive and overlaps are not counterfactual savings.\n',encoding='utf8')
def git(*args):return subprocess.check_output(['git','-C',str(D),*args],text=True).strip()
subprocess.run(['git','-C',str(D),'init'],check=True,capture_output=True);git('config','core.autocrlf','false');git('checkout','-b','codex/dsn-service-stability-analysis-'+version)
git('add','.');git('commit','-m','Freeze service interval and timing stability analysis')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=dict(code_commit=git('rev-parse','HEAD'),scope='CPU-only independent analysis; neural execution source remains f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf',
    files=[dict(path=n,bytes=(D/n).stat().st_size,sha256=sha(D/n)) for n in git('ls-files').splitlines()])
with (HERE/('ANALYSIS_SOURCE_'+version+'.json')).open('x',encoding='utf8') as f:json.dump(manifest,f,indent=2);f.write('\n')
git('bundle','create',str(HERE/('ANALYSIS_SOURCE_'+version+'.bundle')),'HEAD');assert not git('status','--porcelain','--untracked-files=all')
print(json.dumps(dict(code_commit=manifest['code_commit'],source_files=len(manifest['files']),manifest_sha256=sha(HERE/('ANALYSIS_SOURCE_'+version+'.json')),bundle_sha256=sha(HERE/('ANALYSIS_SOURCE_'+version+'.bundle')))))
