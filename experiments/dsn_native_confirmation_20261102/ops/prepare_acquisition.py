from pathlib import Path
import hashlib,json
from remote import Remote,E,B,P,O,PY
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
with Remote() as c:
    for n in ['METADATA_SELECTION.json','GATE.json','RULE.json','HISTORICAL_EXCLUSION_INPUTS.json','RUN_RECORD.json']:
        c.get(O+'/metadata_selection_v2/'+n,E/'selection/METADATA_SELECTION_v2'/n)
    sel=json.loads((E/'selection/METADATA_SELECTION_v2/METADATA_SELECTION.json').read_bytes());N=sel['selected_speaker_count']
    assert N==8 and sel['status']=='PASS_STRICT_SAME_SPLIT_METADATA_SELECTION_PENDING_AUDIO'
    cfg=P+'/ACQUISITION_CONFIG_v1.json';out=O+'/audio_acquisition_v1';src=P+'/acquisition_v1';pre=P+'/ACQUISITION_ENTRY_v1.json'
    command=[PY,'-B',src+'/make_acquisition_config.py','--selection-dir',O+'/metadata_selection_v2','--rule',P+'/SELECTION_RULE_v2.json','--reference-metadata',B+'/datasets/revtrace/streamcorrect_adaptation_20261028/reference.json','--expected-sources',str(N),'--dataset-root',B+'/datasets/revtrace/dsn_native_confirmation_20261102','--raw-out',out,'--out',cfg]
    raw=c.python('import subprocess\nsubprocess.run('+repr(command)+',check=True)\n');print(raw.decode())
    c.get(cfg,E/'selection/ACQUISITION_CONFIG_v1.json')
    m=E/'packages/ACQUISITION_V1_SOURCE.json';identity=json.loads(m.read_bytes())
    job=dict(tag='ACQUISITION_RUN_V1',experiment_id='REVTRACE_STRICT_NEW_TEST_AUDIO_ACQUISITION_20261102_V1',code_commit=identity['code_commit'],local_source=str((E/'selection/acquire_source_dev').relative_to(E.parents[1])),local_manifest=str(m.relative_to(E.parents[1])),remote_source=src,out=out,command=[PY,'-B',src+'/acquire_audio.py','--config',cfg,'--manifest',P+'/ACQUISITION_V1_SOURCE.json','--prelaunch',pre],frozen_input_files={cfg:sha(E/'selection/ACQUISITION_CONFIG_v1.json')},entry_prelaunch_file=pre,entry_config_sha256=sha(E/'selection/ACQUISITION_CONFIG_v1.json'))
    p=E/'selection/ACQUISITION_JOB_v1.json';assert not p.exists();p.write_text(json.dumps(job,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(N=N,job=str(p))))
