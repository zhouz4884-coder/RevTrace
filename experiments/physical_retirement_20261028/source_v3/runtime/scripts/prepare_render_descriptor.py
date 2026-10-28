"""Run inside frozen actual model environment; CPU only, no neural execution."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from revtrace.startup_overlap import prepare_descriptor

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    descriptor=prepare_descriptor(a.model)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf8') as f:json.dump(descriptor,f,indent=2);f.write('\n')
    print(json.dumps(dict(path=str(a.output),sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),
        package_python_files=len(descriptor['package_files']),model_assets=len(descriptor['render_contract']['assets']),
        scope='Native processor/parser identity preparation only; no model generation or recovery proof')))

if __name__=='__main__':main()
