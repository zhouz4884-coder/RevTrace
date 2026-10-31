"""Write complete clean source manifest and bundle outside this checkout."""
import argparse,pathlib,subprocess
from common import git,need,put,sha,verify_checkout
def freeze(out,version='v2'):
    root=pathlib.Path(__file__).resolve().parent;need(not git(root,'status','--porcelain','--untracked-files=all'),'commit independent source before freeze');commit=git(root,'rev-parse','HEAD');out=pathlib.Path(out);need(not out.resolve().is_relative_to(root),'manifest cannot contaminate source');out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for name in sorted(set(git(root,'ls-files','-z').split('\0'))-{''}):
        path=root/name;rows.append(dict(path=name,bytes=path.stat().st_size,sha256=sha(path)))
    manifest=out/f'PAIRED_RESIDENT_SOURCE_{version}.json';bundle=out/f'PAIRED_RESIDENT_SOURCE_{version}.bundle';need(not manifest.exists() and not bundle.exists(),'do not overwrite source freeze')
    put(manifest,dict(source_commit=commit,code_commit=commit,files=rows,scope='Independent outer controller/finite resident Supervisor and clock checker; exact external BDFA/4f NN dependency identities are frozen in campaign configs'))
    subprocess.run(['git','-C',str(root),'bundle','create',str(bundle),'HEAD'],check=True);gate=verify_checkout(root,manifest,commit);put(out/f'PAIRED_RESIDENT_SOURCE_{version}_GATE.json',gate);print(commit)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--version',default='v2',choices=['v2']);a=p.parse_args();freeze(a.out,a.version)
