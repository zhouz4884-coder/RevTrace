"""Read Windows history, stream RAM results directly to their declared8TB raw root."""
from pathlib import Path
import argparse,hashlib,io,json,platform,subprocess,sys,zipfile
from remote import Remote,E,B,P,O
R=E.parents[1]
p=argparse.ArgumentParser();p.add_argument('--version',type=int,default=2);a=p.parse_args()
name='SELECTION_V'+str(a.version);tag='CENSUS_LOCAL_V'+str(a.version)
source=E/('selection/source_v'+str(a.version));M=E/'packages'/(name+'_SOURCE.json')
commit=json.loads(M.read_bytes())['code_commit'];cfg=E/'selection/CENSUS_CONFIG.json'
control=E/'selection'/('local_prelaunch_v'+str(a.version));control.mkdir(exist_ok=False)
env=dict(executable=sys.executable,python=sys.version,platform=platform.platform(),code_commit=commit,
         execution_host='local Windows metadata reader',new_model_calls=0,
         raw_transport='RAM binary stdout ZIP directly persisted over SFTP on designated8TB; no local raw/temp files')
ep=control/'ENVIRONMENT.json';ep.write_bytes((json.dumps(env,indent=2)+'\n').encode())
sha=lambda q:hashlib.sha256(Path(q).read_bytes()).hexdigest()
out=O+'/census_local_history_v'+str(a.version);bundle=out+'.stream.zip'
cmd=[sys.executable,'-B',str(source/'metadata_census.py'),'--manifest',str(M),'--config',str(cfg),
     '--phase','local_history','--out',out,'--stream-bundle']
record=dict(experiment_id='REVTRACE_AISHELL_LOCAL_HISTORY_CENSUS_20261102_V'+str(a.version),code_commit=commit,
    frozen_config=str(cfg.resolve()),frozen_config_sha256=sha(cfg),environment_record=str(ep.resolve()),
    environment_record_sha256=sha(ep),raw_result_location=out,aggregate_summary_location=out+'/SUMMARY.json',
    gate_decision_location=out+'/GATE.json',actual_command=cmd,actual_execution_platform=platform.platform(),
    source_manifest_sha256=sha(M),stream_archive_location=bundle,source_reader_local_raw_files_created=False)
rp=control/'RUN_RECORD_PRELAUNCH.json';rp.write_bytes((json.dumps(record,indent=2)+'\n').encode())
r=subprocess.run([sys.executable,'-B',str(E/'ops/activate_source.py'),'--source',str(source),'--manifest',str(M),
                  '--tag',tag,'--run-record',str(rp)],cwd=R,capture_output=True,check=True)
print(r.stdout.decode(),flush=True)
with Remote() as c:
    script='C='+repr(dict(base=B,P=P,O=O,out=out,bundle=bundle))+'\n'+r'''
from pathlib import Path
for s in [C['P'],C['O']]:
 p=Path(s).resolve();assert p.is_relative_to(Path(C['base']));p.mkdir(parents=True,exist_ok=True)
assert not Path(C['out']).exists() and not Path(C['bundle']).exists()
'''
    c.python(script)
    c.put(rp,P+'/'+tag+'_PRELAUNCH.json');c.put(ep,P+'/'+tag+'_WINDOWS_ENVIRONMENT.json');c.put(cfg,P+'/'+tag+'_CONFIG.json')
    gate=E/('ROOT_NOARG_'+tag+'.json');c.put(gate,P+'/'+gate.name)
    # The sole scientific output is captured in RAM, never printed as raw bytes.
    result=subprocess.run(cmd,cwd=source,capture_output=True)
    if not zipfile.is_zipfile(io.BytesIO(result.stdout)):
        raise RuntimeError('Metadata reader did not produce its declared RAM bundle: '+result.stderr.decode(errors='replace')[-3000:])
    s=c.client.open_sftp()
    try:
        with s.open(bundle,'wx') as f:f.write(result.stdout);f.flush()
        if result.stderr:
            with s.open(bundle+'.stderr.txt','wx') as f:f.write(result.stderr);f.flush()
    finally:s.close()
    extraction='C='+repr(dict(out=out,bundle=bundle,sha=hashlib.sha256(result.stdout).hexdigest(),exit_code=result.returncode))+'\n'+r'''
from pathlib import Path
import hashlib,json,zipfile
p=Path(C['bundle']);assert hashlib.sha256(p.read_bytes()).hexdigest()==C['sha']
out=Path(C['out']);out.mkdir(exist_ok=False)
with zipfile.ZipFile(p) as z:
 for name in z.namelist():
  target=(out/name).resolve();assert target.is_relative_to(out.resolve());target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(z.read(name))
g=json.loads((out/'GATE.json').read_bytes())
print(json.dumps(dict(status='WINDOWS_RAM_CENSUS_FIRST_PERSISTED_ON8TB',out=str(out),stream_sha256=C['sha'],reader_exit_code=C['exit_code'],gate=g)))
'''
    raw=c.python(extraction);(control/'STREAM_TRANSFER_RECEIPT.json').write_bytes(raw)
    mirror=E/'selection'/('LOCAL_CENSUS_v'+str(a.version))
    for leaf in ['SUMMARY.json','GATE.json','EXCLUSIONS.json','UNRESOLVED.json','ERRORS.json','OPTIONAL_ROOTS_MISSING.json']:
        try:c.get(out+'/'+leaf,mirror/leaf)
        except FileNotFoundError:pass
    print(raw.decode(),flush=True)
