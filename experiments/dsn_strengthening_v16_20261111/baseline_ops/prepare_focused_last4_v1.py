import json,pathlib,shlex,sys,hashlib
E=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python';PROJECT=B+'/projects/revtrace_dsn_strengthening_v16_20261111/focused_confirmation_v2';P=B+'/results/revtrace/dsn_strengthening_v16_20261111/PILOT_PREPARATION_V2'
def main():
    local=E/'baseline_ops/FOCUSED_LAST4_PREPARATION_V1';local.mkdir(exist_ok=False)
    rt=B+'/projects/revtrace_dsn_strengthening_v16_20261111/baseline_runtime_v3';sp=B+'/projects/revtrace_dsn_strengthening_20261031';gen=B+'/projects/revtrace_dsn_strengthening_v16_20261111/pilot_driver_v2';out=PROJECT+'/CONFIRM_LAST4_PLAN';raw=B+'/results/revtrace/dsn_strengthening_v16_20261111/CONFIRM_LAST4_FULL_READY_V1'
    command=[PY,'-B',PROJECT+'/source/prepare_confirmation.py','--manifest',PROJECT+'/SOURCE.json','--base-source',rt+'/source','--base-manifest',rt+'/SOURCE.json','--support-source',sp+'/paired_resident_source_v2','--support-manifest',sp+'/PAIRED_RESIDENT_SOURCE_v2.json','--reference-generator-source',gen+'/source','--reference-generator-manifest',gen+'/SOURCE.json','--bank-receipt',B+'/results/revtrace/dsn_native_confirmation_20261102/audio_acquisition_v2/SOURCE_RECEIPT.json','--parent-selection',B+'/projects/revtrace_dsn_strengthening_v16_20261111/root_last4_reference_v1/SELECTION_RECEIPT.json','--parent-reference',B+'/results/revtrace/dsn_strengthening_v16_20261111/REFERENCE_LAST4_V1/REFERENCE_RECEIPT.json','--indices','4,5,6,7','--template',B+'/results/revtrace/dsn_strengthening_20261031/paired32_v2/cells/SC_PAIRED32_V2_BAC009S0908W0369_final_fullcall_r0/CONFIG.json','--environment',P+'/ENVIRONMENT.json','--out',out,'--raw-root',raw]
    sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
    c=ssh_client()
    try:
        i,o,e=c.exec_command('env CUDA_VISIBLE_DEVICES='+shlex.quote('')+' PYTHONPATH='+shlex.quote(PROJECT+'/source')+' PYTHONDONTWRITEBYTECODE=1 '+shlex.join(command),timeout=90);stdout,stderr=o.read().decode(),e.read().decode();code=o.channel.recv_exit_status();(local/'STDOUT.log').write_text(stdout);(local/'STDERR.log').write_text(stderr)
        if code:raise RuntimeError('focused metadata failed, no GPU: '+stderr)
        with c.open_sftp() as s:
            for n in ('SERVICE_PLAN.json','SELECTION_RECEIPT.json'):s.get(out+'/'+n,str(local/n))
            for sub in ('configs','BOUND_REFERENCE'):
                (local/sub).mkdir()
                for n in s.listdir(out+'/'+sub):
                    if n.endswith('.json'):s.get(out+'/'+sub+'/'+n,str(local/sub/n))
        plan=json.loads((local/'SERVICE_PLAN.json').read_bytes());h=dict(status='CPU_PASS_EXACT_LAST4_REFERENCE_BOUND_AND16_CONFIGS_FROZEN_NO_GPU',source_commit=plan['driver']['source_commit'],source_manifest_sha256=plan['driver']['source_manifest_sha256'],actual_NN=plan['actual_NN'],reference_generator=plan['reference_generator'],plan=out+'/SERVICE_PLAN.json',plan_sha256=hashlib.sha256((local/'SERVICE_PLAN.json').read_bytes()).hexdigest(),raw_result_location=raw,comparison_bank_indices=plan['comparison_bank_indices'],source_ids=[s['source_id'] for s in plan['sources']],expected_trials=16,
            prelaunch_required_fields=dict(plan_sha256='exact value above',root_noarg_preflight='Root NNde0936 gate path',root_noarg_preflight_sha256='exact NNgate SHA',driver_explicit_preflight='Root explicit4fb6 source gate path',driver_explicit_preflight_sha256='exact explicit gate SHA',exclusive_GPU_window_authorized_by_root=True,asset_byte_gate=dict(path=P+'/ASSET_BYTE_BINDING.json',sha256=hashlib.sha256((E/'baseline_ops/PILOT_PREPARATION_V2/ASSET_BYTE_BINDING.json').read_bytes()).hexdigest())),
            command=[PY,'-B',PROJECT+'/source/run_confirmation.py','--plan',out+'/SERVICE_PLAN.json','--manifest',PROJECT+'/SOURCE.json','--prelaunch',PROJECT+'/CONFIRMATION_PRELAUNCH.json','--out',raw],model_calls=0,GPU_trials=0,pilot_first2_remain_separately_labeled=True)
        h['prelaunch_required_fields']['plan_sha256']=h['plan_sha256'];(local/'LAUNCH_HANDOFF.json').write_text(json.dumps(h,indent=2)+'\n',encoding='utf8');print(json.dumps(h,indent=2))
    finally:c.close()
if __name__=='__main__':main()
