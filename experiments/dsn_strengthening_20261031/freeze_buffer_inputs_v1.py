"""Freeze local four-cell inputs using the immutable 4eb fixture builder.

No remote operations, CURRENT changes, models, CUDA or campaign launch.
"""
from __future__ import annotations
import copy, datetime, hashlib, inspect, json, os, pathlib, subprocess, sys

E=pathlib.Path(__file__).resolve().parent
F=E.parent/'dsn_native_resilience_20261030'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_dsn_strengthening_20261031'
OLDP=B+'/projects/revtrace_dsn_native_resilience_20261030'
O=B+'/results/revtrace/dsn_strengthening_20261031/buffer4_v1'
OUT=E/'buffer_fixture_inputs_v1'

def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8')
def put(p,v):
    with pathlib.Path(p).open('xb') as f:f.write((json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf8'))
def binding(p):return dict(local=str(p.resolve()),bytes=p.stat().st_size,sha256=sha(p))

def main():
    sys.dont_write_bytecode=True
    local={
      'base':(F/'source_v2',F/'packages/SOURCE_v2.json','4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47','60ae549fcc98165a74e5a3dc420bf93418296099fa12b410572b15d281b2c457'),
      'harness':(E/'paired_resident_source_v2',E/'paired_resident_packages_v2/PAIRED_RESIDENT_SOURCE_v2.json','a13fa0a335529dc188f7e738877a3acd027ce4a7','8cadffbfe9ffcc1eb3efdf5e2702e7afbc2ec932158c12dd197d6f0bdc334934'),
      'fixture':(E/'buffer_fixture_source_v1',E/'buffer_fixture_packages_v1/BUFFER_FIXTURE_SOURCE_v1.json','4eb03d6f4f9a918cce693c979e9cfa07e3d6bb28','1e5a787221fc37bb8118e1f070dfed0f7bb433053bd737c86c9f42ac9d9cfe4b')}
    remote={
      'base':dict(source_root=OLDP+'/source_v2',source_manifest=OLDP+'/SOURCE_v2.json'),
      'harness':dict(source_root=P+'/paired_resident_source_v2',source_manifest=P+'/PAIRED_RESIDENT_SOURCE_v2.json'),
      'fixture':dict(source_root=P+'/buffer_fixture_source_v1',source_manifest=P+'/BUFFER_FIXTURE_SOURCE_v1.json')}
    for name,(root,manifest,commit,digest) in local.items():
        assert sha(manifest)==digest and read(manifest)['source_commit']==commit
        remote[name].update(source_commit=commit,source_manifest_sha256=digest)
    sys.path.insert(0,str(local['fixture'][0]))
    from run_buffer_fixture import verify_dependency
    source_gates=[]
    for name,(root,manifest,commit,digest) in local.items():
        source_gates.append(dict(role=name,**verify_dependency(dict(source_root=str(root),source_manifest=str(manifest),source_commit=commit,source_manifest_sha256=digest))))
    a=F/'FORMAL_SHORT28_V1_RESULTS_v1/cells/SC_FORMAL_SHORT28_v1_BAC009S0908W0369_none_fullcall_r0/CONFIG.json'
    b=F/'FORMAL_SHORT28_V1_RESULTS_v1/cells/SC_FORMAL_SHORT28_v1_BAC009S0905W0246_none_fullcall_r0/CONFIG.json'
    original=read(a);followup=read(b)['settings']['sources'][0]
    assert followup['source_id']=='BAC009S0905W0246'
    environment=E/'paired_resident_inputs_v2/ENVIRONMENT_v2_FROZEN.json'
    env=read(environment);assert sha(environment)=='40c867b5225ee1d23253fe63dba4e5e2727f97ececa34f9c94d26f39ff51920a'
    assert original['frozen_environment_packages']==env['packages']
    assert original['runtime_environment']==env['runtime_environment']
    template=copy.deepcopy(original)
    template.update(environment_record=P+'/ENVIRONMENT_v2_FROZEN.json',environment_sha256=sha(environment))
    OUT.mkdir(exist_ok=False)
    (OUT/'buffer4_v1_configs').mkdir()
    (OUT/'SOURCE_A_ORIGINAL_CONFIG.json').write_bytes(a.read_bytes())
    (OUT/'SOURCE_B_ORIGINAL_CONFIG.json').write_bytes(b.read_bytes())
    (OUT/'ENVIRONMENT_v2_FROZEN.json').write_bytes(environment.read_bytes())
    put(OUT/'BUILDER_TEMPLATE_v1.json',template)
    put(OUT/'FOLLOWUP_S0905_v1.json',followup)
    put(OUT/'DEPENDENCIES_v1.json',remote)
    put(OUT/'LOCAL_SOURCE_PREFLIGHT_v1.json',dict(status='PASS_ALL_THREE_LOCAL_COMPLETE_CLEAN_IMMUTABLE_SOURCE_IDENTITIES',sources=source_gates,neural_calls=0,CURRENT_changed=False))
    command=[sys.executable,'-B',str(local['fixture'][0]/'build_buffer_plan.py'),'--template',str(OUT/'BUILDER_TEMPLATE_v1.json'),'--dependencies',str(OUT/'DEPENDENCIES_v1.json'),'--raw-root',O,'--followup-source',str(OUT/'FOLLOWUP_S0905_v1.json'),'--out',str(OUT/'BUILDER_OUTPUT_v1.json')]
    built=subprocess.run(command,text=True,capture_output=True,check=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    raw_plan=read(OUT/'BUILDER_OUTPUT_v1.json');cells=[]
    assert len(raw_plan['cells'])==4 and sum(c['expect_match'] for c in raw_plan['cells'])==2
    for row in raw_plan['cells']:
        cfg=row['config'];cid=row['cell_id'];cfgpath=OUT/'buffer4_v1_configs'/f'{cid}.json'
        expected=[original['settings']['sources'][0],followup] if row['expect_match'] else original['settings']['sources']
        assert canonical(cfg['settings']['sources'])==canonical(expected)
        assert cfg['settings']['backend']==original['settings']['backend'] and cfg['settings']['warmup']==original['settings']['warmup']
        assert cfg['settings']['source_commit']==remote['base']['source_commit']
        assert (cfg['maximum_service_seconds'],cfg['maximum_process_seconds'],cfg['watchdog_cleanup_seconds'],cfg['watchdog_cli_timeout_seconds'])==(240,900,40,5)
        assert cfg['request_order']==[s['source_id'] for s in expected]
        put(cfgpath,cfg)
        remotecfg=P+'/buffer4_v1_configs/'+cfgpath.name
        cells.append(dict(cell_id=cid,position=cfg['position'],repeat=row['repeat'],expect_match=row['expect_match'],arm='fullcall',primary_gpu=row['primary_gpu'],request_order=cfg['request_order'],config=remotecfg,config_sha256=sha(cfgpath),out=cfg['raw_result_location'],watchdog_out=cfg['watchdog_result_location'],watchdog_gate=cfg['watchdog_result_location']+'/WATCHDOG_GATE.json',buffer_gate=cfg['gate_decision_location'],resident_gate=cfg['raw_result_location']+'/GATE.json',command=[env['executable'],remote['fixture']['source_root']+'/run_buffer_fixture.py','--config',remotecfg,'--out',cfg['raw_result_location']]))
    # Import and entry-point smoke only. No worker or model is instantiated.
    for name in ('base','harness','fixture'):sys.path.insert(0,str(local[name][0]))
    import buffer_fixture,resident_supervisor,fixture_watchdog,audit_buffer_witness
    assert len(inspect.signature(buffer_fixture.timing_owner_entry).parameters)==9
    assert {'owner_target','observer'}.issubset(inspect.signature(resident_supervisor.run_resident).parameters)
    assert 'torch' not in sys.modules
    help_result=subprocess.run([sys.executable,'-B',str(local['fixture'][0]/'run_buffer_fixture.py'),'--help'],text=True,capture_output=True,check=True)
    assert '--config' in help_result.stdout and '--out' in help_result.stdout
    smoke=dict(status='PASS_LOCAL_FROZEN_BUILDER_IMPORT_AND_ENTRY_PATHS_NO_MODEL',builder_command=command,builder_stdout=built.stdout.strip(),builder_file_sha256=sha(local['fixture'][0]/'build_buffer_plan.py'),entry_help_exitcode=help_result.returncode,owner_signature=str(inspect.signature(buffer_fixture.timing_owner_entry)),resident_signature=str(inspect.signature(resident_supervisor.run_resident)),modules={m.__name__:str(pathlib.Path(m.__file__).resolve()) for m in (buffer_fixture,resident_supervisor,fixture_watchdog,audit_buffer_witness)},torch_imported=False,new_neural_calls=0,formal_Linux25='NOT_RUN_BY_THIS_FREEZE',formal_NN4='NOT_RUN_BY_THIS_FREEZE')
    put(OUT/'LOCAL_IMPORT_BUILDER_ENTRY_GATE_v1.json',smoke)
    frozen=dict(experiment_id=raw_plan['experiment_id'],created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_identity=dict(queue_orchestrator=remote['harness'],fixture_entry_controller=remote['fixture'],actual_neural_C_U=remote['base']),dependencies=remote,source_commit=remote['fixture']['source_commit'],harness_source_commit=remote['harness']['source_commit'],actual_NN_source_commit=remote['base']['source_commit'],environment_python=env['executable'],environment_record=P+'/ENVIRONMENT_v2_FROZEN.json',environment_sha256=sha(environment),runtime_environment=env['runtime_environment'],reference_details=template['reference_details'],reference_details_sha256=template['reference_details_sha256'],reference_gate=template['reference_gate'],reference_gate_sha256=template['reference_gate_sha256'],reference_kind=template['reference_kind'],expected_cells=4,positive_trials=2,negative_trials=2,random_order_seed=raw_plan['seed'],maximum_service_seconds=240,maximum_process_seconds=900,watchdog_cleanup_seconds=40,watchdog_cli_timeout_seconds=5,original_D2_seconds=2.,original_C8_seconds=8.,all_offered_including_EOS=True,raw_result_location=O,aggregate_summary_location=O+'/SUMMARY.json',gate_decision_location=O+'/GATE.json',cells=cells,gate_rule='All four fresh predetermined trials must run unless an evidenced physical-resource/technical blocker prevents safe progress. Each cell requires CLI exit zero AND watchdog gate PASS_EXTERNAL_HARD_CLOCK_CHILD_AND_PHYSICAL_DRAIN AND BUFFER_WITNESS_GATE PASS for its expected match/mismatch AND resident full-task/reference gate. Preserve every timeout/untriggered site/mismatch/failure; never mask watchdog/cleanup failure with a mechanism PASS.',next_request_scope='Positive trials append the exact original BAC009S0905W0246 source after source A actual certified EOS in the same logical run; negative trials have source A only. No alias, reset-by-hindsight or long-stream claim.',source_hierarchy_rule='Runtime C/U source tag remains NN4f; fixture and shared harness have separate actual complete manifests. Root CURRENT and exclusive queue are owned by the execution agent; this freeze does not change either.',formal_Linux25='NOT_RUN_BY_THIS_FREEZE',formal_NN4='NOT_RUN_BY_THIS_FREEZE',GPU_launched=False,CURRENT_changed=False,remote_files_not_written=True)
    put(OUT/'BUFFER4_v1_FROZEN.json',frozen)
    originals=dict(source_A=binding(a),source_B=binding(b),new_common_environment=binding(environment),base_manifest=binding(local['base'][1]),harness_manifest=binding(local['harness'][1]),fixture_manifest=binding(local['fixture'][1]),freezer_script=binding(pathlib.Path(__file__)))
    files=[]
    for path in sorted(OUT.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(OUT).as_posix();remote_file=(P+'/'+relative) if relative.startswith('buffer4_v1_configs/') or relative=='BUFFER4_v1_FROZEN.json' else (P+'/buffer_fixture_inputs_v1/'+relative)
        files.append(dict(relative=relative,local=str(path.resolve()),remote=remote_file,bytes=path.stat().st_size,sha256=sha(path)))
    index=dict(status='PASS_LOCAL_FROZEN_FOUR_CELL_INPUTS_COMPLETE_HASH_INDEX',experiment_id=frozen['experiment_id'],plan_sha256=sha(OUT/'BUFFER4_v1_FROZEN.json'),builder_output_sha256=sha(OUT/'BUILDER_OUTPUT_v1.json'),original_inputs=originals,source_identity=frozen['source_identity'],files=files,formal_Linux25='NOT_RUN_BY_THIS_FREEZE',formal_NN4='NOT_RUN_BY_THIS_FREEZE',remote_writes=0,CURRENT_changed=False)
    put(OUT/'INPUT_INDEX_v1.json',index)
    print(json.dumps(dict(status=index['status'],plan_sha256=index['plan_sha256'],configs=[dict(cell_id=c['cell_id'],sha256=c['config_sha256']) for c in cells],files=len(files)+1,neural_calls=0,CURRENT_changed=False)))

if __name__=='__main__':main()
