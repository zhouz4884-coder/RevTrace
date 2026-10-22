"""Final fixed-plan/source/environment/data audit; no neural calls or edits."""
from pathlib import Path
import csv,hashlib,json,sys

def main():
    B=Path(sys.argv[1]);P=B/'projects/revtrace_row_completion_20261023';O=B/'results/revtrace/row_completion_20261023';D=O/'matrix_consistency_v1';D.mkdir(exist_ok=False)
    def read(p):return json.loads(p.read_text())
    def sha(p):
        with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
    terminal=read(O/'FORMAL_ROW_SUMMARY_v1.json');assert terminal['status']=='COMPLETE_ALL150_INDEPENDENT_AUDITS_PASS'
    assert (O/'F2_EXPOSURE_CPU_SUMMARY_v1.json').exists(),'complete all frozen CPU supplements first'
    freeze=read(O/'FORMAL_ROW_FREEZE_v1.json');plan=freeze['core_plan']+freeze['validation_plan']
    names=[{'phase':i['phase'],'cell':f"{i['method']}-{i['delivery']}-{i['load']}-{i['traffic']}-r{i['repeat']}"} for i in plan]
    assert names==terminal['completed'] and len(names)==150
    S=P/'source_row_sdk_v2';source=read(S/'SOURCE_MANIFEST.json');hashes={r['path']:r['sha256'] for r in source['files']}
    assert source['code_commit']==freeze['source_commit']=='2bc71af5457de5d065ff9e771d2fad428c5c6ed9'
    for name,value in hashes.items():assert sha(S/name)==value
    manifests={'core':B/'datasets/revtrace/phaseD_20261021/manifest.json','validation':O/'validation_source_v1/MANIFEST.json'}
    mf={label:read(path) for label,path in manifests.items()};assert all(len(x['sessions'])==16 for x in mf.values())
    assert not {s['source_id'].split('-')[0] for s in mf['core']['sessions']}&{s['source_id'].split('-')[0] for s in mf['validation']['sessions']}
    profile_keys=['model','model_config_sha256','warmup_policy','hardware_fingerprint','software','backend','max_new_tokens',
      'rollback_tokens','unfixed_chunks','code_commit','render_contract']
    common=None;rows=[]
    try:
        for item,named in zip(plan,names):
            stage='formal_row_v1' if item['phase']=='core' else 'validation_row_v1';C=O/stage/named['cell']
            cfg=read(C/'config.json');prov=read(C/'provenance.json');rt=cfg['authority_runtime'];pr=cfg['proposal_runtime'];ss=read(C/'sessions.json')
            profile={k:rt[k] for k in profile_keys}
            if common is None:common=profile
            assert profile==common and {k:pr[k] for k in profile_keys}==common
            assert prov['code_commit']==source['code_commit']
            assert all(hashes[n]==v for n,v in prov['source_sha256'].items())
            assert cfg['replicas']=={'proposal':[0],'authority':[1]} and cfg['microbatch']==cfg['authority_microbatch']==16
            assert rt['dtype']=='float32' and pr['dtype']=='float16' and rt['row_delivery']==pr['row_delivery']==item['delivery']
            assert cfg['result_delivery']==item['delivery'] and cfg['seed']==20261023+item['repeat']
            assert cfg['fine_seconds']==2 and cfg['sample_rate']==16000 and cfg['rho']==(3 if item['method'] in ['dgft','standard'] else 1)
            assert cfg['proposal_barrier']=='decoupled' and cfg['proposal_reconciliation']=='lazy' and cfg['retain_verified_private_prefix']
            assert cfg['journal_mode']=='durable' and cfg['journal_sync_mode']=='group_ready' and cfg['trusted_text_binding']
            assert cfg['consumer_policy']=='two_lane' and cfg['display_protocol']=='canonical-snapshot-v1' and cfg['capture_worker_records']
            assert cfg['online_study']['method']==item['method'] and cfg['online_study']['traffic']==item['traffic']
            assert cfg['online_study']['fallback_layout']=='selective' and cfg['online_study']['score_threshold']==.05
            assert not cfg['online_study']['oracle_diagnostic'] and not cfg['online_study']['unsafe_negative_contract'] and not cfg['diagnostic_receipt_trace']
            assert cfg['async_implementation']==('standard' if item['method']=='standard' else 'revtrace')
            assert rt['online_selection_mode']==(item['method'] if item['method'] in ['strict','score'] else None)
            assert cfg['manifest_sha256']==prov['manifest_sha256']==sha(manifests[item['phase']])
            assert len(ss)==16 and len({s['source_id'] for s in ss})==16
            for i,(s,declared) in enumerate(zip(ss,mf[item['phase']]['sessions'])):
                assert s['session_id']==i and s['source_id']==declared['source_id'] and s['audio_sha256']==declared['audio_sha256']
                expected=0. if item['load']=='sync16' else (i//8)*32.+(i%8)*.25
                assert s['offset']==expected and s['language']=='English' and abs(s['duration']-declared['duration'])<1e-9
            assert read(C/'result.json')['fine_window_accounting_complete']
            rows.append({'phase':item['phase'],'cell':C.name,'source_code_profile_and_source_audio':'PASS','source_speaker_subjects':16,
              'fixed_worker_allocation':'1_FP16_Proposer_plus_1_FP32_Authority','precision_and_profile_not_universal_bitwise_determinism':True})
        # Initial/final boundary identity;this is not continuous attestation that
        # another actor could never replace and restore a file during the run.
        initial=read(O/'probe_v1/MODEL_IDENTITY.json');weights=[]
        for r in initial['weights']:
            p=B/'models/Qwen3-ASR-1.7B'/r['file'];actual=sha(p);assert actual==r['sha256'];weights.append({**r,'after_formal_sha256':actual})
        with (D/'FIXED_CELL_CONFIGS.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        out={'status':'PASS_COMPLETE150_FIXED_PLAN_CODE_ENV_AUDIO_AND_BOUNDARY_MODEL_IDENTITY','cells':len(rows),
          'actual_order_matches_preregistered_plan':True,'unique_sources':32,'core_sources':16,'validation_sources':16,
          'no_outcome_filtered_or_silently_replaced_cells':True,'stable_common_model_profile':common,'weights':weights,
          'new_model_calls':0,'precision_scope':'declared FP16/FP32 tensor/runtime profile;no universal cross-layout bitwise or IEEE-kernel guarantee',
          'script_sha256':sha(Path(__file__))}
        (D/'SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['stable_common_model_profile','weights']}))
    except BaseException as e:
        (D/'STOP.json').write_text(json.dumps({'error':repr(e),'cells_audited':len(rows),'new_model_calls':0,'raw_preserved':True})+'\n');raise

if __name__=='__main__':main()
