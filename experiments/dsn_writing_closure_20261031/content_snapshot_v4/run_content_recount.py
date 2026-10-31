"""Frozen single-process CPU controls or one complete20 existing-trace recount.

The parent launches this with stdout/stderr files on 8TB. No GPU API is called.
All actual input paths are explicit in CONFIG; no recursive raw scan/copy.
"""
from __future__ import annotations
import argparse
import datetime
import io
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time
import traceback
import unittest
from evidence_io import Inputs, disk, need, put, read, sha, source_gate, control_hashes, verify_controls_unchanged

SOURCE=Path(__file__).resolve().parent

def model_absence():
    forbidden=('torch','transformers','tensorflow','jax','native_service','native_worker','stage_worker','resilience_owner')
    found=[k for k in sys.modules if any(k==x or k.startswith(x+'.') for x in forbidden)]
    need(not found,'model/runtime module was imported: '+','.join(found))
    need(os.environ.get('CUDA_VISIBLE_DEVICES')=='','CUDA_VISIBLE_DEVICES must be explicitly empty')
    return dict(new_model_calls=0,model_initializations=0,forbidden_imports_found=[],CUDA_VISIBLE_DEVICES='')

def current_environment():
    return dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
        backend='Python standard library CPU only',**model_absence())

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    began=time.monotonic()
    a=p.parse_args();disk(SOURCE);disk(a.config);disk(a.manifest);out=disk(a.out);cfg=read(a.config)
    need(disk(cfg['analysis_source_root']).resolve()==SOURCE and disk(cfg['analysis_source_manifest']).resolve()==a.manifest.resolve(),'source/manifest paths differ from frozen config')
    need(str(out)==cfg['intended_output'] and str(out/'SUMMARY.json')==cfg['aggregate_summary_location'] and str(out/'GATE.json')==cfg['gate_decision_location'],'output paths differ from frozen config')
    identity=source_gate(SOURCE,a.manifest,cfg['analysis_source_manifest_sha256'],cfg['analysis_source_commit'])
    need(cfg['mode'] in ('controls','complete20'),'unknown mode')
    env_path=disk(cfg['environment_record']);need(sha(env_path)==cfg['environment_record_sha256'],'frozen environment changed')
    environment=current_environment();need(read(env_path)==environment,'actual CPU environment differs from frozen record')
    gate_path=disk(cfg['root_noarg_preflight']);need(sha(gate_path)==cfg['root_noarg_preflight_sha256'],'root gate receipt changed')
    gate=read(gate_path)
    need(gate['gate']=='SOURCE_IDENTITY_PASS' and gate['code_commit']==cfg['analysis_source_commit'] and gate['manifest_sha256']==cfg['analysis_source_manifest_sha256'],'root CURRENT must identify this actual CPU analysis source; the original NN identity remains separate')
    need(gate['setup_pointer'].replace('\\','/').endswith('/CURRENT.json') and 'setup_pointer_sha256' in gate,'not a no-argument CURRENT gate receipt')
    control_paths=[a.config,a.manifest,env_path,gate_path]
    controls_before=control_hashes(control_paths)
    need(not out.exists(),'output already exists; no overwrite or resume')
    for cell in cfg['cells']:
        raw_root=disk(cell['raw_root']).resolve()
        need(not out.resolve().is_relative_to(raw_root) and not raw_root.is_relative_to(out.resolve()),'analysis output overlaps immutable original raw')
    out.parent.mkdir(parents=True,exist_ok=True)
    need(os.stat(out.parent).st_dev==os.stat(disk('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')).st_dev,'output not on designated device')
    need(shutil.disk_usage(out.parent).free>=cfg['minimum_free_bytes'],'insufficient 8TB free space')
    out.mkdir(exist_ok=False)
    # O_EXCL creates a fixed experiment lease. Existing lease is a blocker; the
    # runner never silently recycles it or sends a signal to another process.
    lock=disk(cfg['lease_path']);lock.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    os.write(fd,json.dumps(dict(experiment_id=cfg['experiment_id'],pid=os.getpid(),source_commit=cfg['analysis_source_commit'])).encode());os.close(fd)
    record=dict(experiment_id=cfg['experiment_id'],code_commit=cfg['analysis_source_commit'],
        source_manifest=str(a.manifest),source_manifest_sha256=sha(a.manifest),
        frozen_config=str(a.config),frozen_config_sha256=sha(a.config),
        environment_record=str(env_path),environment_record_sha256=sha(env_path),
        actual_NN_execution_commit='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',
        dependency_record=str(SOURCE/'DEPENDENCIES.json'),dependency_record_sha256=sha(SOURCE/'DEPENDENCIES.json'),
        raw_result_location=[c['raw_root'] for c in cfg['cells']],
        raw_input_index=str(a.config),raw_input_index_sha256=sha(a.config),
        stdout_location=str(disk(cfg['stdout_path'])),stderr_location=str(disk(cfg['stderr_path'])),
        temporary_fixture_location='RAM only; no raw/fixture file is written',
        aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),
        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_model_calls=0,
        mode=cfg['mode'],source_gate=identity,root_noarg_preflight_sha256=sha(gate_path),
        control_file_hashes_before=controls_before)
    put(out/'RUN_RECORD_PRELAUNCH.json',record);put(out/'CONFIG_FROZEN.json',cfg);put(out/'ENVIRONMENT.json',environment)
    try:
        put(out/'CONTROL_HASHES_BEFORE.json',controls_before)
        need(cfg['max_input_bytes']<=256*1024*1024 and cfg['max_output_bytes']<=8*1024*1024,'unbounded budgets')
        sys.path.insert(0,str(SOURCE/'vendor'))
        from content_reader import analyze_trial, aggregate
        stream=io.StringIO()
        tests=unittest.defaultTestLoader.discover(str(SOURCE),pattern='test_content_reader.py')
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(tests)
        (out/'CPU_CONTROLS.log').write_text(stream.getvalue(),encoding='utf8')
        need(result.wasSuccessful() and not result.skipped,'CPU counterexample controls failed')
        if cfg['mode']=='controls':
            summary=dict(status='PASS_FROZEN_LINUX_CPU_CONTROLS_ONLY',tests=result.testsRun,skips=0,
                actual_raw_scanned=False,new_model_calls=0)
        else:
            cells=cfg['cells'];need(len(cells)==20 and len({c['cell_id'] for c in cells})==20,'complete20 coverage missing')
            need(sum(c['cohort']=='paired' for c in cells)==16 and sum(c['cohort']=='resident' for c in cells)==4,'fixed cohort changed')
            need({(c['arm'],c['repeat']) for c in cells if c['cohort']=='resident'}=={(arm,r) for arm in ('conservative','fullcall') for r in (0,1)},'resident distribution changed')
            sources=set(cfg['acoustic_source_ids']);need(len(sources)==4,'four fixed acoustic sources required')
            need({(tuple(c['source_ids']),c['arm'],c['repeat']) for c in cells if c['cohort']=='paired'}=={((sid,),arm,r) for sid in sources for arm in ('conservative','fullcall') for r in (0,1)},'paired exact four-source distribution changed')
            need(all(set(c['source_ids'])==sources for c in cells if c['cohort']=='resident'),'resident source set changed')
            raw=Inputs(cfg['inputs'],cfg['max_input_bytes']);before=raw.verify_all();put(out/'INPUT_HASHES_BEFORE.json',before)
            # Bind the selected white list back to the original complete raw
            # inventories, instead of trusting an independently typed path list.
            indexed={}
            for inventory in cfg['original_raw_inventories']:
                original=raw.json(inventory['path'])
                need(sha(inventory['path'])==inventory['sha256'],'original RAW_INDEX identity changed')
                need(original['file_count']==len(original['files']) and original['total_bytes']==sum(r['bytes'] for r in original['files']),'original RAW_INDEX count/bytes')
                for r in original['files']:
                    indexed[str(Path(original['raw_root'])/r['path'])]=r
            inventory_paths={r['path'] for r in cfg['original_raw_inventories']}
            for item in cfg['inputs']:
                if item['path'] in inventory_paths:continue
                need(item['path'] in indexed and item['bytes']==indexed[item['path']]['bytes'] and item['sha256']==indexed[item['path']]['sha256'],'selected input not bound to original inventory')
            summaries=[];requests=[];first=[];events=[];intervals=[];segments=[]
            for cell in cells:
                need(time.monotonic()-began<=cfg['max_elapsed_seconds'],'bounded CPU time exceeded')
                values=analyze_trial(cell,raw)
                summaries.append(values[0]);requests.extend(values[1]);first.extend(values[2]);events.extend(values[3]);intervals.extend(values[4]);segments.extend(values[5])
            need(len(requests)==32 and len({(r['cell_id'],r['source_id']) for r in requests})==32,'all32 request instances required')
            groups=aggregate(requests,summaries)
            for arm,supported,mismatch,credit in [('conservative',22.5,7.5,30.),('fullcall',51.,14.821625,65.821625)]:
                g=groups['paired/'+arm];need(abs(g['original_dual_credit_audio_seconds']-credit)<1e-7,'paired original credit conservation')
                for mode in ('raw','whitespace_stripped'):
                    content=g['content'][mode];need([content[k] for k in ('introduced_code_point_occurrences','retracted_occurrence_code_points','still_visible_occurrence_code_points')]==[180,14,166],'paired actual chars conservation')
                    x=g['posterior_whole_text_support'][mode];need(abs(x['original_credit_supported_seconds']-supported)<1e-7 and abs(x['original_credit_mismatching_seconds']-mismatch)<1e-7 and x['original_credit_unknown_seconds']==0,'paired first-G conservation')
            for name,value in [('PER_TRIAL',summaries),('PER_REQUEST',requests),('FIRST_G_SUPPORT',first),('AVAILABILITY_EVENTS',events),('AVAILABILITY_INTERVALS',intervals),('COMPLETE_TIP_SEGMENTS',segments)]:put(out/(name+'.json'),value)
            after=raw.verify_all();need(before==after,'raw changed during CPU read');put(out/'INPUT_HASHES_AFTER.json',after)
            put(out/'ACCESSED_INPUTS.json',sorted(raw.accessed))
            summary=dict(status='PASS_COMPLETE20_CPU_CONTENT_EXACT_G_AND_DEPENDENCY_CONTINUITY',
                actual_NN_trials_reused=20,request_instances=32,independent_acoustic_sources=4,
                new_model_calls=0,CPU_controls=result.testsRun,skips=0,raw_input_files=len(before),
                raw_input_bytes=sum(r['bytes'] for r in before.values()),all_inputs_SHA_before_after_unchanged=True,
                paired_existing_fields_independently_conserved=True,groups=groups,
                scope='Read-only CPU reanalysis of completed real-service logs. No new GPU/NN trials, no human correctness or physical browser/network availability claim.')
        need(time.monotonic()-began<=cfg['max_elapsed_seconds'],'bounded CPU time exceeded')
        model_absence();source_gate(SOURCE,a.manifest,cfg['analysis_source_manifest_sha256'],cfg['analysis_source_commit'])
        controls_after=verify_controls_unchanged(control_paths,controls_before)
        put(out/'CONTROL_HASHES_AFTER.json',controls_after)
        summary['frozen_config_environment_rootgate_manifest_SHA_before_after_unchanged']=True
        put(out/'SUMMARY.json',summary)
        record.update(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),summary_sha256=sha(out/'SUMMARY.json'),status=summary['status'])
        put(out/'RUN_RECORD_FINAL.json',record)
        current_bytes=sum(p.stat().st_size for p in out.iterdir() if p.is_file())
        need(current_bytes<cfg['max_output_bytes']-4096,'output budget exceeded')
        put(out/'GATE.json',dict(gate=summary['status'],summary_sha256=sha(out/'SUMMARY.json'),new_model_calls=0,output_bytes_before_gate=current_bytes))
        print(json.dumps(summary,ensure_ascii=False))
    except BaseException as exc:
        (out/'FAILURE.txt').write_text(traceback.format_exc(),encoding='utf8')
        put(out/'GATE.json',dict(gate='FAIL_PRESERVED_CPU_RECOUNT',error_type=type(exc).__name__,reason=str(exc),new_model_calls=0))
        raise
    finally:
        # The exclusive lease belongs to this process and is removed only after
        # its result/failure is durable; no external worker lease is touched.
        lock.unlink()

if __name__=='__main__':
    main()
