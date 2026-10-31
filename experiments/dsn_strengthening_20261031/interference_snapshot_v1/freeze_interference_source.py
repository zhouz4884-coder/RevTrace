"""Root-reviewed source freeze helper; explicit invocation only, no NN."""
import argparse,pathlib,subprocess
from common import git,need,put,sha,verify_checkout
def freeze(out):
    root=pathlib.Path(__file__).resolve().parent;need(not git(root,'status','--porcelain','--untracked-files=all'),'commit reviewed independent source before freeze');commit=git(root,'rev-parse','HEAD');out=pathlib.Path(out);need(not out.resolve().is_relative_to(root),'freeze outside source');out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for name in sorted(set(git(root,'ls-files','-z').split('\0'))-{''}):
        path=root/name;rows.append(dict(path=name,bytes=path.stat().st_size,sha256=sha(path)))
    manifest=out/'INTERFERENCE_SOURCE_v1.json';bundle=out/'INTERFERENCE_SOURCE_v1.bundle';need(not manifest.exists() and not bundle.exists(),'never overwrite a freeze')
    put(manifest,dict(source_commit=commit,code_commit=commit,files=rows,scope='Two-client fixed-phase observation-only original NN59 controller, independent per-request clocks and actual-dispatch audit. No admission change.'))
    subprocess.run(['git','-C',str(root),'bundle','create',str(bundle),'HEAD'],check=True);put(out/'INTERFERENCE_SOURCE_v1_GATE.json',verify_checkout(root,manifest,commit));print(commit)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();freeze(a.out)
