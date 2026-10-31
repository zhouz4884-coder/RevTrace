"""Accept b867's real zero-NN wrapper without relabelling original4eb FAIL.

This is a narrow schema for the four already executed cells. It separately
checks posthoc completion, original task/reference success, mechanism evidence,
and the preserved original reader/CLI/watchdog failure. A wrapper PASS alone
cannot satisfy this prerequisite, and never becomes end-to-end execution PASS.
"""
from __future__ import annotations
import pathlib,re
from common import need,read,sha,canonical,disk_path,verify_checkout,FINAL

READER='b8670073141a94a550abe5113222a508b63b5624'
READER_MANIFEST='bd5160ac716084beeaf3280a958b1eb0320e2d970a9253dc2857bfb4f34c9e74'
EXECUTION='4eb03d6f4f9a918cce693c979e9cfa07e3d6bb28'
EXECUTION_MANIFEST='1e5a787221fc37bb8118e1f070dfed0f7bb433053bd737c86c9f42ac9d9cfe4b'
FROZEN_CONFIG_SHA='7288383bb234aa9751d497298da42516a27f58c4322b6a23b49aed0c4e67e49c'
FROZEN_PLAN_SHA='c0258c50088c1cccf8f47de782fdda7b9c69d2a7e393a7e2720779df6d86552d'
TASK_PASS='PASS_RESIDENT_COMPLETE_TASK_PER_REQUEST_CLOCK_AND_REFERENCE'
COMPOUND_FAIL='NO_GO_COMPLETE_BUFFER4_NEGATIVES_PRESERVED'
MECHANISM={True:'PASS_CONTROLLED_REAL_NN_BUFFER_POST_PRODUCER_DEATH_MATCH',False:'PASS_CONTROLLED_REAL_NN_BUFFER_POST_PRODUCER_DEATH_MISMATCH_REJECTED'}

def receipt(item):
    path=disk_path(item['path']);need(sha(path)==item['sha256'],'posthoc prerequisite receipt bytes changed: '+str(path));return read(path)

def index_rows(rows):
    found={}
    for row in rows:
        path=pathlib.PurePosixPath(row['path']);need(not path.is_absolute() and '..' not in path.parts and '\\' not in row['path'] and str(path)==row['path'],'raw index path escapes/cannot be normalized')
        need(row['path'] not in found and type(row['bytes']) is int and row['bytes']>=0 and re.fullmatch('[0-9a-f]{64}',row['sha256']) is not None,'invalid/duplicate complete raw binding');found[row['path']]=row
    return found

def audit_schema(doc):
    """Pure actual-output schema audit, also used on bounded local mirrors."""
    cfg,index,cpu,gate,summary,record,plan=(doc[k] for k in ('config','input_index','cpu_gate','gate','summary','run_record','execution_plan'))
    need(index['source_commit']==READER and index['source_manifest_sha256']==READER_MANIFEST and index['old_execution_source']==EXECUTION and index['original_execution_gates_must_remain_failed_and_unchanged'] is True,'wrong frozen reader/input-index identity')
    need(index['config']['sha256']==FROZEN_CONFIG_SHA,'wrong input-index frozen config hash')
    need(cfg['new_neural_calls']==0 and cfg['analysis_id']==index['analysis_id']==record['experiment_id']==gate['analysis_id']==summary['analysis_id'],'posthoc analysis ID/new-NN binding differs')
    deps={d['source_commit']:d for d in cfg['analysis_dependencies']};need(READER in deps and deps[READER]['source_manifest_sha256']==READER_MANIFEST and FINAL in deps,'wrong posthoc source dependencies')
    need(index['config']['remote']==str(pathlib.PurePosixPath(deps[READER]['source_root']).parent/'BUFFER4_POSTHOC_REAUDIT_v2_FROZEN.json'),'wrong input-index frozen config path')
    need(cfg['original_execution_plan_sha256']==FROZEN_PLAN_SHA and cfg['original_execution_fixture_manifest_sha256']==EXECUTION_MANIFEST,'wrong original frozen execution identity')
    need(record['code_commit']==READER and record['source_manifest_sha256']==READER_MANIFEST and record['original_execution_fixture_commit']==EXECUTION and record['new_neural_calls']==0,'posthoc run record changed execution identity')
    need(record['raw_result_location']==cfg['raw_result_location']==index['output'] and record['aggregate_summary_location']==cfg['aggregate_summary_location'] and record['gate_decision_location']==cfg['gate_decision_location'],'posthoc recorded output paths differ')
    need(cpu['status']=='PASS_FORMAL_READER31_LINUX_CPU_ZERO_SKIP' and cpu['source_commit']==READER and cpu['source_manifest_sha256']==READER_MANIFEST and cpu['new_neural_calls']==0 and cpu['tests']==31 and cpu['failures']==cpu['errors']==cpu['skipped']==0 and cpu['successful'] is True,'formal31 real reader CPU prerequisite missing/failed')
    need(gate['status']=='PASS_COMPLETE_ZERO_NN_BUFFER4_POSTHOC_REAUDIT' and gate['source_commit']==READER and gate['checked_cases']==gate['passed_cases']==4 and gate['new_neural_calls']==0 and gate['all_complete_raw_and_watchdog_bytes_unchanged'] is True and gate['original_execution_gates_unchanged'] is True,'posthoc aggregate gate incomplete/changed raw')
    need(summary['analysis_source_commit']==READER and summary['original_execution_source_commit']==EXECUTION and summary['new_neural_calls']==0 and summary['original_execution_CLI_watchdog_failures_retained'] is True,'posthoc summary relabelled old execution')
    need(plan['source_commit']==EXECUTION and plan['actual_NN_source_commit']==FINAL and plan['expected_cells']==4 and plan['positive_trials']==plan['negative_trials']==2,'not original fixed two-positive/two-negative plan')
    cells={r['cell_id']:r for r in plan['cells']};rows={r['row']['cell_id']:r for r in doc['cases']};aggregated={r['cell_id']:r for r in summary['cases']}
    need(len(cells)==len(rows)==len(aggregated)==len(doc['cases'])==len(summary['cases'])==4 and set(cells)==set(rows)==set(aggregated),'posthoc case partition missing/duplicated/foreign')
    compound,oldsummary=doc['original_compound_gate'],doc['original_compound_summary'];need(compound['status']==oldsummary['status']==COMPOUND_FAIL and compound['completed_cells']==compound['planned_cells']==oldsummary['completed_cells']==oldsummary['planned_cells']==4,'old compound execution FAIL was changed/incomplete')
    oldcells={r['cell_id']:r for r in oldsummary['cells']};need(len(oldcells)==4 and set(oldcells)==set(cells),'old CLI case partition differs')
    for cid,cell in cells.items():
        item=rows[cid];row=item['row'];mechanism=row['mechanism'];execution_config=item['execution_config'];spec=execution_config['timing_fixture'];raw=item['resident_summary']
        need(canonical(row)==canonical(aggregated[cid]),'per-case wrapper does not match hashed aggregate summary')
        need(row['status']=='PASS_ZERO_NN_POSTHOC_MECHANISM_REAUDIT' and row['complete_raw_and_watchdog_bytes_unchanged'] is True and row['original_execution_gates_relabelled'] is False,'wrapper failed or relabelled original execution')
        need(type(cell['expect_match']) is bool and mechanism['status']==MECHANISM[cell['expect_match']] and mechanism['actual_parent_full_input_matches'] is cell['expect_match'] and mechanism['experiment_id']==cid and mechanism['base_nn_commit']==FINAL,'nested actual NN mechanism is not original expected positive/negative PASS')
        need(spec['experiment_id']==cid and spec['expect_match'] is cell['expect_match'] and spec['base_nn_commit']==FINAL and spec['historical_parent_prediction_sha']==mechanism['predicted_full_sha'] and spec['historical_parent_actual_sha']==mechanism['actual_parent_full_sha'],'mechanism differs from immutable predeclared full-state premise')
        need(canonical(mechanism['fixture_identity'])==canonical(execution_config['execution_dependencies']),'nested mechanism changed original execution dependencies')
        need(execution_config['request_order']==cell['request_order'] and [r['source_id'] for r in mechanism['requests']]==cell['request_order'],'post-fault requests differ from original plan')
        fence=mechanism['physical_fence'];need(fence['job_id']==mechanism['original_child_job_id'] and fence['incarnation']==mechanism['original_worker_incarnation']==0 and fence['confirmed_perf']<=fence['cuda_release_perf']<=fence['fence_observed_perf']<=fence['replacement_started_perf'],'nested physical UID/incarnation/fence ordering failed')
        previous=None
        for request in mechanism['requests']:
            need(request['complete_perf']>=max(request['admission_perf'],fence['fence_observed_perf']) and (previous is None or request['admission_perf']>=previous),'post-fault actual EOS/request ordering failed');previous=request['complete_perf']
        expected=sum((s['frames']+7999)//8000 for s in execution_config['settings']['sources']);reference=raw['integrity']['original_reference'];clock=raw['integrity']['request_clock']
        need(raw['gate']==TASK_PASS and raw['integrity']['all_original_obligations_eventually_processed'] is True and reference['status']=='PASS_COMPLETE_SELECTED_TRACE_REFERENCE' and reference['actual_NN_source_commit']==FINAL and reference['checked_steps']==expected and reference['sources']==len(cell['request_order']),'actual original task/reference failed or incomplete underneath wrapper')
        need(clock['status']=='PASS_CLOSED_LOOP_ACTUAL_EOS_AND_ALL_ORIGINAL_REQUEST_OFFERS' and clock['requests']==len(cell['request_order']) and clock['accepted_frontiers_checked']==expected and clock['EOS_included'] is True,'original actual-EOS/request-clock prerequisite failed')
        original=row['original_execution_gates'];need(set(original)=={'resident','buffer','watchdog'},'missing original execution gate bodies')
        need(original['resident']['body']['status']==TASK_PASS and original['resident']['body']['actual_NN_source_commit']==FINAL and original['resident']['body']['cell_id']==cid,'actual original resident task gate failed')
        need(original['buffer']['body']['status']=='FAIL_CONTROLLED_BUFFER_FIXTURE_PRESERVED' and 'conflicting original worker receipts' in original['buffer']['body']['failure'] and 'audit_buffer_witness.py' in original['buffer']['body']['failure'],'old FAIL is not the known receipt-reader failure')
        watchdog=original['watchdog']['body'];need(watchdog['status']=='FAIL_CHILD_PRESERVED' and watchdog['returncode']==1 and watchdog['timed_out'] is False and watchdog['cleanup']['original_trial_stays_failed'] is True and watchdog['cleanup']['status']=='PASS_EXTERNAL_WATCHDOG_OWNED_GROUPS_AND_CUDA_RELEASE','old CLI/watchdog failure or actual cleanup proof differs')
        need(watchdog['cleanup']['releases'] and all(r['all_CUDA_owners_released'] is True and r['confirmed_no_executing_members'] is True for r in watchdog['cleanup']['releases']),'old actual physical cleanup unresolved')
        old=oldcells[cid];need(old['returncode']==1 and old['outer_timed_out'] is False and old['all_three_gates_and_exit_pass'] is False,'old compound per-cell failure was relabelled')
        for kind,field in (('resident','resident_gate'),('buffer','buffer_gate'),('watchdog','watchdog_gate')):
            need(original[kind]['path']==cell[field] and canonical(original[kind]['body'])==canonical(old['gates'][kind]),'wrapper changed original gate/CLI body binding')
        need(item['before']==item['after'] and set(item['before'])=={'raw','watchdog'},'complete raw/watchdog before-after differs')
        indexed={kind:index_rows(item['before'][kind]) for kind in ('raw','watchdog')};inputs=index_rows(mechanism['inputs'])
        need(set(inputs)>={'CONFIG.json','owner_e0/dispatch.jsonl','owner_e0/worker_results.jsonl','owner_e0/owner_events.jsonl','owner_e0/policy_audit.jsonl','publications.jsonl','consumer.jsonl','facts.wal','timing_fixture/controller.jsonl','timing_fixture/parent.ready.json','timing_fixture/child.ready.json','timing_fixture/parent.release.json','timing_fixture/parent.resumed.json'},'mechanism omitted original raw input')
        for name,binding in inputs.items():need(binding==indexed['raw'].get(name),'mechanism raw hash differs from complete before/after')
        need({'SUMMARY.json','ENVIRONMENT.json','BUFFER_FIXTURE_RUN_RECORD.json'}<=set(indexed['raw']),'complete raw index omitted task/config/environment record')
        for kind,scope,name in (('resident','raw','GATE.json'),('buffer','raw','BUFFER_WITNESS_GATE.json'),('watchdog','watchdog','WATCHDOG_GATE.json')):need(original[kind]['sha256']==indexed[scope][name]['sha256'],'original gate hash not in unchanged complete raw tree')
        result=mechanism['result'];expected_install=int(cell['expect_match']);need(result['old_uid_post_fence_canonical_install']==result['old_uid_post_fence_certified_consume']==expected_install,'nested install/consume contradicts original match/mismatch')
        if cell['expect_match']:need(result['consumer_observed_perf']>=fence['fence_observed_perf'] and type(result['canonical_sequence']) is int and result['canonical_sequence']>1,'positive old UID lacked actual post-fence durable consumption')
        if not cell['expect_match']:need(result['original_same_frontier_discard']==1,'mismatch lacks actual same-frontier rejection')
    return dict(status='PASS_ORIGINAL_REAL_BUFFER4_MECHANISMS_VIA_B867_ZERO_NN_REAUDIT',analysis_source_commit=READER,original_execution_source_commit=EXECUTION,original_execution_status=COMPOUND_FAIL,original_execution_failures_retained=True,new_neural_calls=0,checked_cases=4,scope='Accepts mechanism/task/input evidence only; original4eb CLI/watchdog/compound remain FAIL. No retrospective execution/performance PASS.')

def verify_tree(root,rows):
    root=disk_path(root);need(root.is_dir() and not root.is_symlink(),'original raw tree missing or linked');expected=index_rows(rows);found={}
    for path in root.rglob('*'):
        need(not path.is_symlink(),'original raw tree gained a symlink')
        if path.is_file():found[path.relative_to(root).as_posix()]=dict(path=path.relative_to(root).as_posix(),bytes=path.stat().st_size,sha256=sha(path))
    need(found==expected,'original complete raw/watchdog bytes changed since zero-NN reaudit')

def validate_buffer_reaudit(prior):
    names={'input_index','frozen_config','formal_cpu_gate','aggregate_gate','aggregate_summary','run_record','original_compound_gate','original_compound_summary','cases'}
    need(set(prior)==names,'expected explicit hash-bound b867 posthoc wrapper receipts; legacy four top-level gates are insufficient')
    cfg=receipt(prior['frozen_config']);need(prior['frozen_config']['sha256']==FROZEN_CONFIG_SHA,'wrong frozen zero-NN configuration bytes')
    doc=dict(config=cfg,input_index=receipt(prior['input_index']),cpu_gate=receipt(prior['formal_cpu_gate']),gate=receipt(prior['aggregate_gate']),summary=receipt(prior['aggregate_summary']),run_record=receipt(prior['run_record']),original_compound_gate=receipt(prior['original_compound_gate']),original_compound_summary=receipt(prior['original_compound_summary']))
    record=doc['run_record'];need(prior['frozen_config']['path']==doc['input_index']['config']['remote'],'input-index config path differs')
    need(prior['aggregate_gate']['path']==cfg['gate_decision_location'] and prior['aggregate_summary']['path']==cfg['aggregate_summary_location'] and prior['run_record']['path']==cfg['raw_result_location']+'/RUN_RECORD.json','aggregate/runtime receipt path differs')
    need(sha(disk_path(record['frozen_config']))==record['frozen_config_sha256'] and canonical(read(disk_path(record['frozen_config'])))==canonical(cfg) and sha(disk_path(record['environment_record']))==record['environment_record_sha256'],'actual analysis config/environment not bound to run record')
    need(sha(disk_path(cfg['original_execution_plan']))==cfg['original_execution_plan_sha256']==FROZEN_PLAN_SHA,'original frozen four-cell execution plan changed');doc['execution_plan']=read(disk_path(cfg['original_execution_plan']))
    for dependency in cfg['analysis_dependencies']:
        need(sha(disk_path(dependency['source_manifest']))==dependency['source_manifest_sha256'],'analysis dependency manifest changed');verify_checkout(dependency['source_root'],dependency['source_manifest'],dependency['source_commit'])
    need(sha(disk_path(cfg['original_execution_fixture_manifest']))==EXECUTION_MANIFEST and read(disk_path(cfg['original_execution_fixture_manifest']))['source_commit']==EXECUTION,'original execution fixture manifest changed')
    plan=doc['execution_plan'];need(prior['original_compound_gate']['path']==plan['gate_decision_location'] and prior['original_compound_summary']['path']==plan['aggregate_summary_location'],'original compound FAIL receipt path differs')
    need(len(prior['cases'])==4,'requires all four posthoc wrappers');doc['cases']=[];by={r['cell_id']:r for r in plan['cells']}
    for item in prior['cases']:
        need(set(item)=={'reaudit','raw_before','raw_after'},'per-case receipt fields differ');row=receipt(item['reaudit']);cid=row['cell_id'];need(cid in by,'foreign posthoc case');cell=by[cid]
        for kind,suffix in (('reaudit','_REAUDIT.json'),('raw_before','_RAW_BEFORE.json'),('raw_after','_RAW_AFTER.json')):need(item[kind]['path']==cfg['raw_result_location']+'/'+cid+suffix,'per-case wrapper/index path differs')
        need(sha(disk_path(cell['config']))==cell['config_sha256'],'original per-case frozen config changed');execution=read(disk_path(cell['config']))
        raw=disk_path(cell['out']);runtime=read(raw/'BUFFER_FIXTURE_RUN_RECORD.json');need(runtime['code_commit']==EXECUTION and sha(raw/'CONFIG.json')==runtime['frozen_config_sha256'] and canonical(read(raw/'CONFIG.json'))==canonical(execution) and sha(raw/'ENVIRONMENT.json')==runtime['environment_record_sha256'] and canonical(runtime['execution_dependencies'])==canonical(execution['execution_dependencies']),'actual original execution config/environment/commit changed')
        doc['cases'].append(dict(row=row,before=receipt(item['raw_before']),after=receipt(item['raw_after']),execution_config=execution,resident_summary=read(raw/'SUMMARY.json')))
    result=audit_schema(doc)
    for item in doc['cases']:
        cell=by[item['row']['cell_id']]
        for scope,field in (('raw','out'),('watchdog','watchdog_out')):verify_tree(cell[field],item['before'][scope])
        for original in item['row']['original_execution_gates'].values():need(sha(disk_path(original['path']))==original['sha256'] and canonical(read(disk_path(original['path'])))==canonical(original['body']),'original FAIL/task gate bytes changed after reaudit')
    result['all_original_raw_bytes_rechecked_before_probe']=True;return result

def collect_receipts(frozen_config,input_index,formal_cpu_gate):
    """Read-only convenience for root's PRELAUNCH construction; launches nothing."""
    def binding(path):
        path=disk_path(path);return dict(path=str(path),sha256=sha(path))
    cfg=read(disk_path(frozen_config));plan=read(disk_path(cfg['original_execution_plan']));root=cfg['raw_result_location']
    result=dict(input_index=binding(input_index),frozen_config=binding(frozen_config),formal_cpu_gate=binding(formal_cpu_gate),aggregate_gate=binding(cfg['gate_decision_location']),aggregate_summary=binding(cfg['aggregate_summary_location']),run_record=binding(root+'/RUN_RECORD.json'),original_compound_gate=binding(plan['gate_decision_location']),original_compound_summary=binding(plan['aggregate_summary_location']),cases=[])
    for cell in plan['cells']:
        cid=cell['cell_id'];result['cases'].append(dict(reaudit=binding(root+'/'+cid+'_REAUDIT.json'),raw_before=binding(root+'/'+cid+'_RAW_BEFORE.json'),raw_after=binding(root+'/'+cid+'_RAW_AFTER.json')))
    return result
