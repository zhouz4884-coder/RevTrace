"""Freeze8 metadata/configs from measured references; no service/model launch."""
import json,pathlib,shlex,sys
E=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
PROJECT=B+'/projects/revtrace_dsn_strengthening_v16_20261111/resource_driver_v2';PREP=B+'/results/revtrace/dsn_strengthening_v16_20261111/PILOT_PREPARATION_V2'
def main():
    local=E/'baseline_ops/RESOURCE_PREPARATION_V2';local.mkdir(exist_ok=False)
    runtime=B+'/projects/revtrace_dsn_strengthening_v16_20261111/baseline_runtime_v3';support=B+'/projects/revtrace_dsn_strengthening_20261031';generator=B+'/projects/revtrace_dsn_strengthening_v16_20261111/pilot_driver_v2'
    plan=PROJECT+'/RESOURCE_PLAN_v1.json';raw=B+'/results/revtrace/dsn_strengthening_v16_20261111/RESOURCE8_V1'
    command=[PY,'-B',PROJECT+'/source/make_resource_plan.py','--manifest',PROJECT+'/SOURCE.json','--base-source',runtime+'/source','--base-manifest',runtime+'/SOURCE.json','--support-source',support+'/paired_resident_source_v2','--support-manifest',support+'/PAIRED_RESIDENT_SOURCE_v2.json','--reference-generator-source',generator+'/source','--reference-generator-manifest',generator+'/SOURCE.json','--full-selection',PREP+'/REFERENCE_SELECTION_RECEIPT.json','--subset-selection',PREP+'/PILOT_SELECTION_RECEIPT.json','--full-reference',B+'/results/revtrace/dsn_strengthening_v16_20261111/REFERENCE_FULL4_V2/REFERENCE_RECEIPT.json','--subset-reference',PREP+'/PILOT_BOUND_REFERENCE/REFERENCE_RECEIPT.json','--template',B+'/results/revtrace/dsn_strengthening_20261031/paired32_v2/cells/SC_PAIRED32_V2_BAC009S0908W0369_final_fullcall_r0/CONFIG.json','--environment',PREP+'/ENVIRONMENT.json','--config-dir',PROJECT+'/configs_v1','--raw-root',raw,'--out',plan]
    sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
    from contractkv_ssh_credential import ssh_client
    c=ssh_client()
    try:
        cmd='env CUDA_VISIBLE_DEVICES='+shlex.quote('')+' PYTHONPATH='+shlex.quote(PROJECT+'/source')+' PYTHONDONTWRITEBYTECODE=1 '+shlex.join(command)
        i,o,e=c.exec_command(cmd,timeout=90);stdout,stderr=o.read().decode(),e.read().decode();code=o.channel.recv_exit_status();(local/'STDOUT.log').write_text(stdout,encoding='utf8');(local/'STDERR.log').write_text(stderr,encoding='utf8')
        if code:raise RuntimeError('resource metadata preparation failed (no GPU): '+stderr)
        with c.open_sftp() as s:
            s.get(plan,str(local/'RESOURCE_PLAN_v1.json'));(local/'configs_v1').mkdir()
            for name in s.listdir(PROJECT+'/configs_v1'):s.get(PROJECT+'/configs_v1/'+name,str(local/'configs_v1'/name))
        identity=json.loads((E/'packages/RESOURCE_DRIVER_FREEZE_v2.json').read_bytes())
        handoff=dict(status='CPU_PASS_AND_METADATA8_FROZEN_GPU_NOT_RUN',driver_source_commit=identity['source_commit'],driver_manifest_sha256=identity['manifest_sha256'],remote_source=PROJECT+'/source',remote_manifest=PROJECT+'/SOURCE.json',resource_plan=plan,local_plan=str(local/'RESOURCE_PLAN_v1.json'),raw_result_location=raw,
            prelaunch_requirements=dict(plan_sha256='compute exact resource plan SHA',root_noarg_preflight='Root current de0936 gate path and SHA',driver_explicit_preflight='Root explicit7b83 source gate path and SHA',exclusive_GPU_window_authorized_by_root=True,asset_byte_gate=dict(path=PREP+'/ASSET_BYTE_BINDING.json',sha256='same verified binding SHA')),
            resource_command=[PY,'-B',PROJECT+'/source/run_resource_campaign.py','--plan',plan,'--manifest',PROJECT+'/SOURCE.json','--prelaunch',PROJECT+'/RESOURCE_PRELAUNCH.json','--out',raw],expected_trials=8,reference_generator_commit='f367c4e1068a9391a0e99d8537c94995a3388e13',actual_NN='de0936b2e30179d63aeef6e235cd1af685578c58',new_independent_speakers=0,new_GPU_trials=0)
        (local/'LAUNCH_HANDOFF.json').write_text(json.dumps(handoff,indent=2)+'\n',encoding='utf8');print(json.dumps(handoff,indent=2))
    finally:c.close()
if __name__=='__main__':main()
