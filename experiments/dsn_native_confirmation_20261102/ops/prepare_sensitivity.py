"""Stage the seven immutable old-bank inputs; prepare a fixed-grid CPU config."""
from pathlib import Path
import hashlib,json
from remote import Remote,E,B,P,O,PY
R=E.parents[1]
dest=E/'sensitivity/inputs_v1';dest.mkdir(exist_ok=False)
old=R/'experiments/dsn_strengthening_20261031'
source_receipt=R/'experiments/dsn_streamcorrect_independent_20261029/SOURCE_RECEIPT_v1.json'
remote_inputs=P+'/sensitivity_inputs_v1';config_remote=P+'/SENSITIVITY_CONFIG_v1.json'
with Remote() as c:
    script='C='+repr(dict(base=B,dirs=[P,O,remote_inputs,remote_inputs+'/matched',remote_inputs+'/resident']))+'\n'+r'''
from pathlib import Path
for name in C['dirs']:
 p=Path(name).resolve();assert p.is_relative_to(Path(C['base']).resolve());p.mkdir(parents=True,exist_ok=True)
'''
    c.python(script)
    rows=[]
    for local_name,remote_name in [('PAIRED32_V2_RESULTS','matched'),('RESIDENT4_V2_RESULTS','resident')]:
        for leaf in ['SUMMARY.json','GATE.json','CONFIG.json']:
            local=old/local_name/leaf;remote=remote_inputs+'/'+remote_name+'/'+leaf
            c.put(local,remote);rows.append(dict(path=local.relative_to(R).as_posix(),remote=remote,bytes=local.stat().st_size,sha256=hashlib.sha256(local.read_bytes()).hexdigest()))
    c.put(source_receipt,remote_inputs+'/SOURCE_RECEIPT_v1.json')
    rows.append(dict(path=source_receipt.relative_to(R).as_posix(),remote=remote_inputs+'/SOURCE_RECEIPT_v1.json',bytes=source_receipt.stat().st_size,sha256=hashlib.sha256(source_receipt.read_bytes()).hexdigest()))
    script='C='+repr(dict(source=P+'/sensitivity_v1',matched=remote_inputs+'/matched',resident=remote_inputs+'/resident',receipt=remote_inputs+'/SOURCE_RECEIPT_v1.json',config=config_remote,out=O+'/sensitivity_v1',python=PY))+'\n'+r'''
from pathlib import Path
import importlib.metadata,json,os,subprocess
has_plot=True
try:version=importlib.metadata.version('matplotlib')
except importlib.metadata.PackageNotFoundError:has_plot=False;version=None
cmd=[C['python'],'-B',str(Path(C['source'])/'make_config.py'),'--matched-dir',C['matched'],'--resident-dir',C['resident'],'--source-receipt',C['receipt'],'--out',C['config'],'--raw-out',C['out']]
if has_plot:cmd.append('--render')
r=subprocess.run(cmd,cwd=C['source'],env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'),capture_output=True)
if r.returncode:raise RuntimeError((r.stdout+r.stderr).decode(errors='replace'))
print(json.dumps(dict(status='FIXED_SENSITIVITY_INPUTS_PREPARED_NOT_ANALYZED',config=C['config'],matplotlib_version=version,render_requested=has_plot,new_model_calls=0)))
'''
    prepared=c.python(script);(dest/'PREPARATION_RECEIPT.json').write_bytes(prepared)
    c.get(config_remote,dest/'CONFIG.json')
    (dest/'SOURCE_INPUT_INDEX.json').write_bytes((json.dumps(rows,indent=2)+'\n').encode())
    print(prepared.decode())
