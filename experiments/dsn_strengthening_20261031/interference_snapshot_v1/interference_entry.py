"""Validate exact external NN59 before loading the derived Supervisor."""
import argparse,pathlib,sys
from common import read,verify_checkout,need,FINAL
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--manifest',required=True);p.add_argument('--out',required=True);a=p.parse_args();config=read(a.config)
    dependency=config['base_NN_source'];need(dependency['source_commit']==FINAL,'wrong actual NN dependency');verify_checkout(dependency['source_root'],a.manifest,FINAL);sys.path.insert(0,dependency['source_root'])
    from interference_supervisor import run_interference
    run_interference(a.config,a.manifest,a.out)
