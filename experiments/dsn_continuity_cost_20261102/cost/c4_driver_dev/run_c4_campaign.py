"""Close the planned original-C4 actual-trace check for the fixed NN16 bank.

Orchestration only. The original checker and its 35 controls are not modified.
No model or GPU code is imported or launched. Original NN driver gates/raw are
preserved; this writes a separately bound closure gate with pending=false.
"""
from __future__ import annotations
import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
import traceback
from c4_common import (CHECKER,NN4F,GateError,need,read,sha,put,verify_source,disk,
                       prerequisites,input_roles,inventory,checker_config,checker_command)


def canonical(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()


def validate_prelaunch(args, identity):
    cfg=read(args.prelaunch)
    required={'plan_sha256':args.plan,'nn_summary_sha256':args.nn_summary,'nn_gate_sha256':args.nn_gate,
              'nn_run_record_sha256':args.nn_run_record,'controller_manifest_sha256':args.manifest,
              'checker_manifest_sha256':args.checker_manifest}
    for field,path in required.items():
        need(cfg[field]==sha(path),'prelaunch frozen hash differs: '+field)
    need(cfg['checker_timeout_seconds']==args.timeout,'checker timeout differs from prelaunch')
    need(cfg['NN16_complete_and_exclusive_window_released'] is True,'root has not released original NN exclusive window')
    gate_path=cfg['root_noarg_preflight']
    need(sha(gate_path)==cfg['root_noarg_preflight_sha256'],'root no-argument source gate changed')
    root=read(gate_path)
    need(root['gate']=='SOURCE_IDENTITY_PASS' and root['code_commit']==identity['source_commit']
         and root['manifest_sha256']==identity['manifest_sha256'],'root no-argument gate is for another controller source')
    return cfg


def run_child(command, cwd, stdout, stderr, timeout, scratch):
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',CUDA_VISIBLE_DEVICES='',
             TMPDIR=str(scratch),TMP=str(scratch),TEMP=str(scratch))
    with stdout.open('wb') as out,stderr.open('wb') as err:
        child=subprocess.Popen(command,cwd=cwd,env=env,stdout=out,stderr=err,start_new_session=True)
        try:
            return child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # The CPU checker was launched in its own new session. Never
            # signal an unowned process/group or touch original NN workers.
            if child.poll() is None and os.getpgid(child.pid)==child.pid:
                os.killpg(child.pid,signal.SIGKILL)
            child.wait(timeout=10)
            raise GateError('original CPU checker timeout; exact owned CPU group terminated')


def run(args):
    need(sys.platform.startswith('linux'),'formal original-disk orchestration runs on the Linux experiment host')
    source=Path(__file__).resolve().parent
    controller=verify_source(source,args.manifest)
    checker=verify_source(args.checker_source,args.checker_manifest,CHECKER)
    plan=read(args.plan)
    summary,original_gate,nn_record=read(args.nn_summary),read(args.nn_gate),read(args.nn_run_record)
    by_id=prerequisites(plan,summary,original_gate)
    need(sha(nn_record['frozen_config'])==nn_record['frozen_config_sha256'], 'completed NN driver config changed')
    original_driver_config=read(nn_record['frozen_config'])
    need(original_driver_config['plan_sha256']==sha(args.plan), 'trace closure plan is not the plan actually executed by NN16')
    dep=plan['original_dependency']
    nn_source=verify_source(dep['source_root'],dep['source_manifest'],NN4F)
    need(nn_source['manifest_sha256']==dep.get('source_manifest_sha256',dep.get('manifest_sha256')),
         'original NN4f dependency manifest differs')
    need(nn_record['execution_roles']['actual_NN']['source_commit']==NN4F
         and nn_record['execution_roles']['observer']['source_commit']==plan['observer_source_commit'],
         'completed NN controller record mixes execution roles')
    original_driver=nn_record['execution_roles']['driver']
    original_driver_identity=verify_source(original_driver['source_root'],original_driver['source_manifest'],
                                           nn_record['code_commit'])
    need(original_driver_identity['manifest_sha256']==original_driver['manifest_sha256'],
         'completed original NN driver manifest binding changed')
    need(Path(sys.executable).resolve()==Path(plan['environment_python']).resolve(), 'formal checker interpreter differs from frozen environment')
    need(sha(plan['environment_record'])==plan['environment_sha256'], 'original frozen environment record changed')
    pre=validate_prelaunch(args,controller)
    out=disk(args.out)
    need(not out.exists(),'refusing to overwrite an existing closure attempt')
    out.mkdir(parents=True)
    for name in ['configs','checks','records','logs','scratch']:
        (out/name).mkdir()
    roles=dict(controller=controller,actual_checker=checker,actual_NN=nn_source,
               original_NN_driver=original_driver_identity,
               original_observer=nn_record['execution_roles']['observer'])
    cfg=dict(experiment_id='REVTRACE-COST-NN16-ORIGINAL-C4-CLOSURE-20261102',
             plan=str(args.plan),plan_sha256=sha(args.plan),NN_summary=str(args.nn_summary),
             NN_summary_sha256=sha(args.nn_summary),NN_terminal_gate=str(args.nn_gate),
             NN_terminal_gate_sha256=sha(args.nn_gate),prelaunch_sha256=sha(args.prelaunch),
             checker_timeout_seconds=args.timeout,complete_fixed_cases=16,roles=roles,
             controls_scope='35 distinct original checker controls rerun per case; not 560 independent fault types')
    put(out/'CONFIG.json',cfg)
    put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
                                  new_model_calls=0,GPU_calls=0,CUDA_VISIBLE_DEVICES='',roles=roles))
    put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=controller['source_commit'],
        execution_roles=roles,frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),
        environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),
        raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),
        gate_decision_location=str(out/'GATE.json'),root_noarg_preflight=pre['root_noarg_preflight'],
        root_noarg_preflight_sha256=pre['root_noarg_preflight_sha256'],new_model_calls=0,GPU_calls=0))
    results=[]
    for position,cell in enumerate(plan['cells']):
        cid=cell['cell_id']
        case_record=dict(cell_id=cid,position=position,original_raw_result_location=cell['out'],
                         actual_checker_source_commit=CHECKER,actual_NN_source_commit=NN4F,
                         controller_source_commit=controller['source_commit'])
        try:
            verify_source(source,args.manifest,controller['source_commit'])
            verify_source(args.checker_source,args.checker_manifest,CHECKER)
            raw=disk(cell['out'])
            need(read(raw/'GATE.json')['status']=='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK',
                 'original NN case terminal gate did not pass')
            need(sha(raw/'SUMMARY.json')==by_id[cid]['summary_sha256'], 'actual NN case summary differs from completed driver binding')
            need(sha(cell['config'])==cell['config_sha256'],'original frozen planned NN config changed')
            need(canonical(read(raw/'CONFIG.json'))==canonical(read(cell['config'])), 'actual runtime CONFIG differs from frozen planned config')
            need(read(raw/'CONFIG.json')['fault']['kind']=='none','normal NN16 checker cannot relabel fault trace')
            mapping,owners,files=input_roles(raw)
            inputs=inventory(files)
            config=checker_config(cell,checker,inputs,mapping,owners,out)
            config_path=out/'configs'/(cid+'.json')
            put(config_path,config)
            case_record.update(frozen_config=str(config_path),frozen_config_sha256=sha(config_path),
                environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),
                actual_checker_source_manifest=checker['source_manifest'],actual_checker_manifest_sha256=checker['manifest_sha256'],
                controller_manifest_sha256=controller['manifest_sha256'],
                raw_result_location=str(raw),aggregate_summary_location=str(out/'checks'/cid/'SUMMARY.json'),
                gate_decision_location=str(out/'checks'/cid/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
            put(out/'records'/(cid+'_RUN_RECORD_PRECHECK.json'),case_record)
            command=checker_command(args.checker_source,config_path,args.checker_manifest,out/'checks'/cid)
            put(out/'records'/(cid+'_COMMAND.json'),command)
            scratch=out/'scratch'/cid
            scratch.mkdir()
            returncode=run_child(command,Path(args.checker_source),out/'logs'/(cid+'.stdout'),
                                 out/'logs'/(cid+'.stderr'),args.timeout,scratch)
            need(returncode==0,'unchanged original C4 CLI failed; preserve its full output')
            checked=read(out/'checks'/cid/'SUMMARY.json')
            gate=read(out/'checks'/cid/'GATE.json')
            need(checked['status']=='PASS_ACTUAL_ORIGINAL_FULLCALL_DURABLE_AND_CONSUMER_REFINEMENT'
                 and gate['status']==checked['status'],'original C4 actual-trace gate did not pass')
            need(checked['checker_source_commit']==CHECKER and checked['actual_runtime_source_commit']==NN4F,
                 'checker/NN roles changed in actual output')
            need(checked['CPU_controls']==35,'original distinct checker control set changed')
            need(inputs==inventory(files),'original NN raw bytes changed during C4 check')
            verify_source(args.checker_source,args.checker_manifest,CHECKER)
            results.append(dict(status='PASS_UNCHANGED_C4_ACTUAL_TRACE',**case_record,
                checker_summary=checked,checker_summary_sha256=sha(out/'checks'/cid/'SUMMARY.json'),
                checker_gate_sha256=sha(out/'checks'/cid/'GATE.json'),input_SHA_before_after_equal=True,
                root_actual_trace_recheck_pending=False,new_model_calls=0,GPU_calls=0))
        except BaseException as exc:
            failure=dict(status='FAIL_ORIGINAL_C4_ACTUAL_TRACE_PRESERVED',**case_record,
                         error=repr(exc),traceback=traceback.format_exc(),root_actual_trace_recheck_pending=True)
            put(out/'records'/(cid+'_FAILURE.json'),failure)
            results.append(failure)
        put(out/'PARTIAL_RESULTS.json',results,replace=True)
        print(json.dumps(dict(cell_id=cid,status=results[-1]['status'],completed=len(results),planned=16)),flush=True)
    passed=sum(row['status']=='PASS_UNCHANGED_C4_ACTUAL_TRACE' for row in results)
    complete=passed==16 and len(results)==16
    closure=dict(status='PASS_COMPLETE_ORIGINAL_C4_NN16_TRACE_CLOSURE' if complete else 'FAIL_OR_INCOMPLETE_ORIGINAL_C4_CLOSURE_PRESERVED',
        experiment_id=cfg['experiment_id'],code_commit=controller['source_commit'],execution_roles=roles,
        planned_cells=16,completed_cells=len(results),passed_cells=passed,failed_cells=len(results)-passed,
        distinct_original_checker_controls=35,control_repetitions_per_complete_case=35,
        controls_are_repeated_not_new_independent_fault_types=True,
        original_NN_driver_gate=str(args.nn_gate),original_NN_driver_gate_sha256=sha(args.nn_gate),
        original_pending_gate_preserved=True,root_actual_trace_recheck_pending=not complete,
        new_model_calls=0,GPU_calls=0,cells=results,
        scope='Close the already planned original C4 actual-trace check; no new research branch or arithmetic/quality guarantee')
    put(out/'SUMMARY.json',closure)
    put(out/'GATE.json',{key:value for key,value in closure.items() if key!='cells'})
    # A separate closure receipt binds the old pending gate without rewriting
    # historical NN driver output or any original trace/result file.
    put(out/'ROOT_ACTUAL_TRACE_RECHECK_CLOSURE.json',dict(
        status=closure['status'],root_actual_trace_recheck_pending=not complete,
        original_NN_driver_gate=str(args.nn_gate),original_NN_driver_gate_sha256=sha(args.nn_gate),
        closure_summary_sha256=sha(out/'SUMMARY.json'),closure_gate_sha256=sha(out/'GATE.json'),
        actual_checker_source_commit=CHECKER,controller_source_commit=controller['source_commit']))
    verify_source(source,args.manifest,controller['source_commit'])
    return 0 if complete else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ['plan','manifest','checker-source','checker-manifest','prelaunch','nn-summary','nn-gate','nn-run-record','out']:
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--timeout',type=float,default=120.)
    raise SystemExit(run(parser.parse_args()))
