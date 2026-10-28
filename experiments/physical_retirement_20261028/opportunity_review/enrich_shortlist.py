"""Attach exact archived identities and input-only F2 fixture to probe shortlist."""
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BANK=ROOT/'experiments/ces_v6_abcd_20261025/evidence/results'
DATA=ROOT/'experiments/ces_v6_abcd_20261025/evidence/inputs'
BASE='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
inputs=[]

def read(p,lines=False):
    raw=p.read_bytes();inputs.append({'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
    return [json.loads(x) for x in raw.decode('utf8').splitlines() if x.strip()] if lines else json.loads(raw)

def sha_value(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def dump(name,value):
    (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def main():
    probes=read(HERE/'PROBE_SHORTLIST.json')
    manifests={pool:read(DATA/(pool+'_manifest.json')) for pool in ['development','heldout']}
    for probe in probes:
        path=ROOT/probe['run_dir'];cfg=read(path/'config.json');records=read(path/'worker_records.jsonl',True)
        events=read(path/'events.jsonl',True);batches=read(path/'worker_batch_accounting.jsonl',True)
        provenance=read(path/'provenance.json');workers=read(path/'workers.json');sessions=read(path/'sessions.json')
        command=read(path.parent/(path.name+'.COMMAND.json'))
        byid={r['job']['job_id']:(i+1,r) for i,r in enumerate(records)}
        b=next(x for x in batches if x['batch_id']==probe['batch'])
        t0=next(x['t0_perf'] for x in events if x['kind']=='run-start')
        pool='heldout' if probe['stage']=='D_heldout' else 'development'
        sources={s['source_id']:s for s in manifests[pool]['sessions']}
        probe['original_files']={name:{'path':(path/name).relative_to(ROOT).as_posix(),
          'sha256':hashlib.sha256((path/name).read_bytes()).hexdigest()} for name in ['config.json','worker_records.jsonl','worker_batch_accounting.jsonl','events.jsonl','sessions.json','consumer.jsonl','provenance.json','workers.json']}
        probe['original_command']={'path':(path.parent/(path.name+'.COMMAND.json')).relative_to(ROOT).as_posix(),**command}
        probe['original_runtime_identity']={'source_commit':provenance['code_commit'],
          'authority_runtime':cfg['authority_runtime'],'proposal_runtime':cfg['proposal_runtime'],
          'contract_digest':events[0]['contract_digest'],'workers':workers,
          'all_source_files':provenance['source_sha256']}
        probe['original_model_path']=command['argv'][command['argv'].index('--model')+1]
        probe['original_manifest_path']=command['argv'][command['argv'].index('--manifest')+1]
        probe['local_copied_manifest']=(DATA/(pool+'_manifest.json')).relative_to(ROOT).as_posix()
        probe['source_manifest_expected_sha256']=cfg['manifest_sha256']
        probe['original_release_sessions']=sessions
        probe['ordered_job_pointers']=[]
        for index,jid in enumerate(b['job_ids']):
            line,r=byid[jid];j=r['job'];a=r['result']['execution_context_audit']
            probe['ordered_job_pointers'].append({'physical_row_index':index,'job_id':jid,
              'worker_records_line_1based':line,'source_id':j['source_id'],
              'audio_asset':{k:sources[j['source_id']][k] for k in ['path','audio_sha256','duration']},
              'actual_audio_sha256':a['actual_audio_sha256'],
              'actual_prompt_sha256_compact_json':sha_value(a['executed_prompt_tokens']),
              'target_audio_end_sample':j['audio_end_sample'],'end_window':j['end_window']})
        selected=[]
        for jid in b['job_ids']:
            _,r=byid[jid];j,s=r['job'],r['result']
            if s['hit_token_limit'] or (j['source_id']=='1993-147149-0020' and j['end_window'] in [5,6]):
                selected.append({'job_definition':j,'actual_context':s['execution_context_audit'],
                  'observed_tokens':s['token_ids'],'observed_token_sha256':sha_value(s['token_ids']),
                  'observed_model_input_audit':s['model_input_audit'],
                  'timestamp_fields':{k:v for k,v in s.items() if k.endswith('_perf')},
                  'scope':'Recorded prior output used only as comparison evidence; never injected as a new model output.'})
        probe['selected_exact_targets']=selected
        if 'ideal_drain_run_s' not in probe:
            probe['ideal_drain_run_s']=max(byid[jid][1]['result']['row_terminal_perf'] for jid in b['job_ids'])-t0
            probe['original_last_terminal_run_s']=probe['ideal_drain_run_s']
        start,end=probe['ideal_drain_run_s'],probe['original_last_terminal_run_s']
        cap_sids={r['job']['session_id'] for _,r in byid.values() if r['job']['job_id'] in b['job_ids'] and r['result']['hit_token_limit']}
        probe['other_actual_accepted_commits_during_ideal_tail']=[{k:e[k] for k in ['session_id','job_id','version','audio_start_sample','audio_end_sample','audio_ready','installed','certificate_consumed','durable_journal_sequence']} for e in events if e['kind']=='commit' and start<e['installed']<=end and e['session_id'] not in cap_sids]
        obligations=[]
        for session in sessions:
            if session['session_id'] in cap_sids:continue
            for w in range(1,math.ceil(session['duration']/cfg['fine_seconds'])+1):
                audio_end_s=min(w*cfg['fine_seconds'],session['duration']);ready=session['offset']+audio_end_s
                if start<ready<=end:
                    obligations.append({'session_id':session['session_id'],'source_id':session['source_id'],
                      'end_window':w,'audio_end_sample':round(audio_end_s*cfg['sample_rate']),
                      'original_release_run_s':ready,'original_display_deadline_run_s':ready+2.,
                      'original_commit_deadline_run_s':ready+8.,'scope':'offered fine input obligation; not a claim of scheduler enqueue'})
        probe['other_offered_obligations_released_during_ideal_tail']=obligations
    template=read(BANK/'D_development/development-sync-mixed-standard-r0/config.json')
    donors=template['ces_study']['donors']
    fixture={'schema':'physical-retirement-f2-input-fixture-v1','scope':'Controlled wrong-conditioning MODEL INPUT; never inject output or expose fault labels to exit policy',
      'origin_source_commit':'d3e418b6d1090a78c3a84156ecc87b02a8ee42c4',
      'origin_source':'experiments/ces_v6_abcd_20261025/runtime_D/src/revtrace/ces_runtime.py:108',
      'donor_file_path':BASE+'/projects/revtrace_online_admission_20261022/DONORS.json',
      'donor_file_sha256':template['ces_study']['donors_sha256'],
      'fault_plan':template['ces_study']['fault_plan'],
      'conditions':['role == proposal','exact session_id:end_window is in fault_plan','chunk_id >= 2'],
      'action':'job.fault_actual_prompt_tokens = donors[fault_plan[key] % len(donors)].tokens',
      'donors':donors,'selected_target':{'source_id':'1993-147149-0020','session_id':8,'end_window':5,
        'donor_index':8,'donor':donors[8],
        'observed_audio_sha256':'5b629f56f04b09264b328625d8261acbb812dfc9d43c1b2a1cf65b691f86c628',
        'observed_generation_tokens':37},
      'latest_cli_caveat':'Latest OnlineAdmissionScheduler injects first >=5 for every session and changes selection/rho through online-study flags. Reuse only this common input-fixture hook, not the entire online or CES study carrier.',
      'latest_physical_execution_requirement':'Apply same fixture to Fine and complete Standard; record actual audio/prompt/layout and rerun. 37-token archival behavior is not guaranteed across changed layouts.'}
    comparison=[]
    cells=[('C',f'development-sync-clean-hold_0-r{r}') for r in range(3)]
    cells += [('D_development',f'development-{arrival}-mixed-{method}-r{r}') for arrival in ['sync','staggered'] for method in ['fine','standard'] for r in range(3)]
    for stage,cell in cells:
        path=BANK/stage/cell;cfg=read(path/'config.json');rs=read(path/'worker_records.jsonl',True)
        es=read(path/'events.jsonl',True);cs=read(path/'consumer.jsonl',True);t0=es[0]['t0_perf']
        for w in [5,6]:
            matches=[r for r in rs if r['job']['role']=='proposal' and r['job']['source_id']=='1993-147149-0020' and r['job']['end_window']==w]
            if not matches:
                comparison.append({'stage':stage,'cell':cell,'window':w,'status':'not dispatched; retain in denominator, inspect covered skip',
                  'relevant_skips':[e for e in es if e['kind']=='proposal-skip' and e['session_id']==8 and e['window']==w]});continue
            assert len(matches)==1
            rec=matches[0];j,r=rec['job'],rec['result'];ctx=r['execution_context_audit']
            covers=[e for e in es if e['kind']=='commit' and e['session_id']==8 and e['audio_end_sample']>=j['audio_end_sample']]
            views=[c for c in cs if c['session_id']==8 and c['valid_visible_frontier']>=j['audio_end_sample']]
            comparison.append({'stage':stage,'cell':cell,'window':w,'status':'actual dispatched row',
              'job_id':j['job_id'],'parent':j['parent'],'declared_root_prompt_digest':j['parent_prompt_digest'],
              'actual_prompt_sha256_compact_json':sha_value(ctx['executed_prompt_tokens']),
              'actual_prompt_tokens':ctx['executed_prompt_tokens'],'actual_audio_sha256':ctx['actual_audio_sha256'],
              'token_count':r['generated_tokens'],'cap':r['hit_token_limit'],'output_sha256':sha_value(r['token_ids']),
              'actual_override':ctx['fault_override'],'enqueue_run_s':j['enqueue_perf']-t0,
              'terminal_run_s':r['row_terminal_perf']-t0,
              'canonical_cover_run_s':min((c['installed'] for c in covers),default=None),
              'first_actual_consumer_cover_run_s':min((c['observed_perf']-t0 for c in views),default=None),
              'raw_records':(path/'worker_records.jsonl').relative_to(ROOT).as_posix(),
              'clean_control_limitation':'C Fine no-hold shares model/audio/declared parent; D has no same-pool clean Standard cell. New unified service needs both clean carriers.'})
    dump('PROBE_SHORTLIST.json',probes)
    operator_probes=[]
    operator_cells=[('D_development','development-staggered-mixed-standard-r0',15,'cap256-standard-staggered-r0'),
                    ('D_development','development-sync-mixed-standard-r0',5,'medium37-standard-sync-r0'),
                    ('C','development-sync-clean-hold_0-r0',5,'clean14-fine-sync-r0')]
    for stage,cell,sequence,probe_id in operator_cells:
        path=BANK/stage/cell;cfg=read(path/'config.json');rs=read(path/'worker_records.jsonl',True)
        es=read(path/'events.jsonl',True);bs=read(path/'worker_batch_accounting.jsonl',True)
        command=read(path.parent/(path.name+'.COMMAND.json'))
        batch=next(b for b in bs if b['worker'].startswith('proposal') and b['batch_id'].endswith(':'+str(sequence)))
        byid={r['job']['job_id']:r for r in rs};phase=batch['phases'][0];t0=es[0]['t0_perf']
        jobs=[byid[jid]['job'] for jid in batch['job_ids']];schedule=[];expectations=[]
        for job in jobs:
            r=byid[job['job_id']]['result'];covers=[e for e in es if e['kind']=='commit' and e['session_id']==job['session_id'] and e['audio_end_sample']>=job['audio_end_sample']]
            cover=min(covers,key=lambda e:e['installed']) if covers else None
            if cover is not None and t0+cover['installed']<r['row_terminal_perf']:
                schedule.append({'job_id':job['job_id'],
                  'delay_from_phase_start_seconds':max(0.,t0+cover['installed']-phase['started_perf']),
                  'reason':'trusted-coverage','original_installed_run_s':cover['installed'],
                  'original_cover_commit_job_id':cover['job_id'],'target_audio_end_sample':job['audio_end_sample']})
            expectations.append({'job_id':job['job_id'],'token_ids':r['token_ids'],'state_tokens':r['state_tokens'],
              'text':r['text'],'generated_tokens':r['generated_tokens'],'terminated_by_eos':r['terminated_by_eos'],
              'hit_token_limit':r['hit_token_limit'],'row_terminal_perf':r['row_terminal_perf'],
              'execution_context_audit':r['execution_context_audit'],'model_input_audit':r['model_input_audit']})
        operator_probes.append({'probe_id':probe_id,'source_commit':command['source_commit'],
          'source_run':path.relative_to(ROOT).as_posix(),'original_batch_id':batch['batch_id'],
          'jobs':jobs,'cancel_schedule':schedule,'original_config':{k:v for k,v in cfg.items() if k!='ces_study'},
          'original_full_config_path':(path/'config.json').relative_to(ROOT).as_posix(),
          'original_full_config_sha256':hashlib.sha256((path/'config.json').read_bytes()).hexdigest(),
          'original_study_metadata':{k:v for k,v in cfg['ces_study'].items() if k in ['method','traffic','fault_plan','display_slo','commit_slo','v6','proposer_order','proposer_policy']},
          'original_proposal_runtime':cfg['proposal_runtime'],
          'model_path':command['argv'][command['argv'].index('--model')+1],
          'manifest_path':command['argv'][command['argv'].index('--manifest')+1],
          'manifest_sha256':cfg['manifest_sha256'],'phase_original_times':phase,
          'original_row_expectations':expectations,
          'input_replay_scope':'Full original peer order and actual wrong-context input; observed outputs are comparison evidence only. Replace run/runtime identity for the new source rather than relabel archival source.'})
    dump('OPERATOR_PROBES.json',{'schema':'physical-retirement-archival-operator-probes-v1',
      'scope':'Fixed-timing archival coverage replay for physical executor control; no online-serving or speedup claim',
      'probes':operator_probes})
    dump('F2_INPUT_FIXTURE.json',fixture)
    dump('LOGICAL_TARGET_COMPARISON.json',comparison)
    dump('ENRICH_INPUT_MANIFEST.json',inputs)
    print(json.dumps({'shortlisted_batches':len(probes),'logical_target_records':len(comparison),
      'fixture_donors':len(donors),'no_GPU_calls':True,'shortlist_bytes':(HERE/'PROBE_SHORTLIST.json').stat().st_size}))

if __name__=='__main__':main()
