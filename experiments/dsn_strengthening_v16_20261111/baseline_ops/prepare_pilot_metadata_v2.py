"""Run only frozen metadata preparation; never a reference/service launcher."""
import hashlib,json,pathlib,shlex,sys
E=pathlib.Path(__file__).resolve().parents[1]
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
PROJECT=B+'/projects/revtrace_dsn_strengthening_v16_20261111/pilot_driver_v2'
OUT=B+'/results/revtrace/dsn_strengthening_v16_20261111/PILOT_PREPARATION_V2'
def main():
    local=E/'baseline_ops/PILOT_PREPARATION_V2';local.mkdir(exist_ok=False)
    command=[PY,'-B',PROJECT+'/source/prepare_pilot.py','--manifest',PROJECT+'/SOURCE.json',
        '--base-source',B+'/projects/revtrace_dsn_strengthening_v16_20261111/baseline_runtime_v3/source',
        '--base-manifest',B+'/projects/revtrace_dsn_strengthening_v16_20261111/baseline_runtime_v3/SOURCE.json',
        '--support-source',B+'/projects/revtrace_dsn_strengthening_20261031/paired_resident_source_v2',
        '--support-manifest',B+'/projects/revtrace_dsn_strengthening_20261031/PAIRED_RESIDENT_SOURCE_v2.json',
        '--bank-receipt',B+'/results/revtrace/dsn_native_confirmation_20261102/audio_acquisition_v2/SOURCE_RECEIPT.json',
        '--template',B+'/results/revtrace/dsn_strengthening_20261031/paired32_v2/cells/SC_PAIRED32_V2_BAC009S0908W0369_final_fullcall_r0/CONFIG.json',
        '--old-environment',B+'/projects/revtrace_dsn_strengthening_20261031/ENVIRONMENT_v2_FROZEN.json',
        '--readiness-summary',B+'/results/revtrace/dsn_strengthening_v16_20261111/readiness_v2/SUMMARY.json',
        '--readiness-gate',B+'/results/revtrace/dsn_strengthening_v16_20261111/readiness_v2/GATE.json',
        '--out',OUT,'--reference-raw',B+'/results/revtrace/dsn_strengthening_v16_20261111/REFERENCE_FULL4_V2',
        '--service-raw',B+'/results/revtrace/dsn_strengthening_v16_20261111/PILOT24_V2']
    sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
    from contractkv_ssh_credential import ssh_client
    client=ssh_client()
    def run(cmd,body=None):
        i,o,e=client.exec_command(cmd,timeout=120)
        if body is not None:i.write(body);i.flush();i.channel.shutdown_write()
        raw,err=o.read().decode('utf8'),e.read().decode('utf8');return o.channel.recv_exit_status(),raw,err
    try:
        prelude='''import datetime,hashlib,json,pathlib,platform,sys
p=pathlib.Path(PROJECT)/'PREPARATION_LAUNCH';p.mkdir(exist_ok=False)
def put(path,x):path.write_text(json.dumps(x,indent=2)+'\\n',encoding='utf8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
cfg=dict(experiment_id='DSN_V16_PILOT_METADATA_PREPARATION_WRAPPER_V2',actual_prepare_source_commit='f367c4e1068a9391a0e99d8537c94995a3388e13',actual_NN_source_commit='de0936b2e30179d63aeef6e235cd1af685578c58',command=COMMAND,model_calls_authorized=0,GPU_launch_authorized=False)
env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),CUDA_VISIBLE_DEVICES='',PYTHONPATH=PROJECT+'/source')
put(p/'CONFIG.json',cfg);put(p/'ENVIRONMENT.json',env);put(p/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=cfg['actual_prepare_source_commit'],frozen_config=str(p/'CONFIG.json'),frozen_config_sha256=sha(p/'CONFIG.json'),environment_record=str(p/'ENVIRONMENT.json'),environment_record_sha256=sha(p/'ENVIRONMENT.json'),raw_result_location=OUT,aggregate_summary_location=OUT+'/SUMMARY.json',gate_decision_location=OUT+'/GATE.json',prelaunch_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
'''
        code,raw,err=run(shlex.quote(PY)+' -B -','PROJECT='+repr(PROJECT)+'\nOUT='+repr(OUT)+'\nCOMMAND='+repr(command)+'\n'+prelude);assert code==0,err
        env='env CUDA_VISIBLE_DEVICES='+shlex.quote('')+' PYTHONPATH='+shlex.quote(PROJECT+'/source')+' PYTHONDONTWRITEBYTECODE=1 '
        code,raw,err=run(env+shlex.join(command));(local/'STDOUT.log').write_text(raw,encoding='utf8');(local/'STDERR.log').write_text(err,encoding='utf8')
        with client.open_sftp() as s:
            for name in ('CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json'):s.get(PROJECT+'/PREPARATION_LAUNCH/'+name,str(local/('PRELAUNCH_'+name)))
            try:
                for name in s.listdir(OUT):
                    if name.endswith('.json'):s.get(OUT+'/'+name,str(local/name))
            except FileNotFoundError:pass
        if code:raise RuntimeError('metadata preparation failed; preserved: '+err)
        summary=json.loads((local/'SUMMARY.json').read_bytes());handoff=json.loads((local/'LAUNCH_HANDOFF.json').read_bytes())
        assert summary['new_GPU_trials']==summary['new_model_calls']==0 and summary['reference_expected_sources']==4
        print(json.dumps(dict(status=summary['status'],reference_sources=summary['reference_source_ids'],pilot_source_ids=[r['source_id'] for r in json.loads((local/'PILOT_SELECTION_RECEIPT.json').read_bytes())['sources']],planned_total=summary['expected_total_trials'],new_GPU_trials=0,launch_handoff_remote=OUT+'/LAUNCH_HANDOFF.json',launch_handoff_local=str(local/'LAUNCH_HANDOFF.json')),indent=2))
    finally:client.close()
if __name__=='__main__':main()
