"""Frozen CPU controls or explicit acquire-and-header mode; never imports models."""
import argparse,datetime,hashlib,io,json,os,pathlib,platform,subprocess,sys,traceback,unittest
from census import load_catalog,download,scan_archive,sha,snapshot,put,need

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True)
    p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--mode',choices=('controls','acquire_census'),required=True);a=p.parse_args()
    root=pathlib.Path(__file__).resolve().parent;cfg=json.loads(a.config.read_bytes());manifest=json.loads(a.manifest.read_bytes())
    commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    need(commit==manifest['code_commit']==cfg['source_commit'],'source_commit_changed')
    need(not subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=all'],text=True).strip(),'dirty_source')
    need(set(subprocess.check_output(['git','-C',str(root),'ls-files'],text=True).splitlines())=={r['path'] for r in manifest['files']},'incomplete_manifest')
    for row in manifest['files']:need((root/row['path']).stat().st_size==row['bytes'] and sha(root/row['path'])==row['sha256'],'source_bytes_changed')
    need(sha(a.manifest)==cfg['source_manifest_sha256'],'manifest_hash_changed')
    need(os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU_only_CUDA_visibility_required')
    need(a.out.resolve().is_relative_to(pathlib.Path(cfg['experiment_disk']).resolve()),'outputs_must_stay_on_experiment_disk')
    need('torch' not in sys.modules and 'transformers' not in sys.modules,'unexpected_model_import')
    a.out.mkdir(parents=True,exist_ok=False);experiment=cfg['experiment_ids'][a.mode]
    put(a.out/'CONFIG.json',cfg)
    environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),hostname=platform.node(),CUDA_VISIBLE_DEVICES='',model_calls=0,GPU_calls=0)
    for key,value in cfg['expected_environment'].items():need(environment[key]==value,'frozen_environment_changed')
    put(a.out/'ENVIRONMENT.json',environment)
    put(a.out/'RUN_RECORD.json',dict(experiment_id=experiment,code_commit=commit,mode=a.mode,
        frozen_config=str(a.out/'CONFIG.json'),frozen_config_sha256=sha(a.out/'CONFIG.json'),environment_record=str(a.out/'ENVIRONMENT.json'),environment_record_sha256=sha(a.out/'ENVIRONMENT.json'),
        source_manifest_sha256=sha(a.manifest),raw_result_location=str(a.out),aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json')))
    with (a.out/'EVENTS.jsonl').open('x',encoding='utf8') as events:
        def event(kind,**body):
            events.write(json.dumps(dict(kind=kind,snapshot=snapshot(),**body),ensure_ascii=False)+'\n');events.flush()
        event('run_started',experiment_id=experiment,mode=a.mode)
        try:
            stream=io.StringIO();tests=unittest.defaultTestLoader.discover(str(root),pattern='test_*.py');result=unittest.TextTestRunner(stream=stream,verbosity=2).run(tests)
            (a.out/'CONTROLS.log').write_text(stream.getvalue(),encoding='utf8')
            need(result.wasSuccessful() and not result.skipped and result.testsRun==cfg['expected_controls'],'header_or_transport_controls_failed')
            catalog=load_catalog(cfg);event('frozen_official_metadata_join_verified',WAV_members=len(catalog),speakers=len({r['speaker_id'] for r in catalog.values()}))
            if a.mode=='controls':
                summary=dict(status='PASS_FROZEN_TEST_HEADER_CONTROLS_AND_OFFICIAL_METADATA_JOIN_NO_AUDIO_ACQUIRED',experiment_id=experiment,source_commit=commit,
                    controls=result.testsRun,skipped=0,metadata_WAV_members=len(catalog),metadata_test_speakers=len({r['speaker_id'] for r in catalog.values()}),
                    official_test_archive_downloaded=False,model_calls=0,GPU_calls=0,history_census_status='REQUIRED_NOT_COMPLETED',speaker_selection='NONE')
            else:
                event('official_test_download_begin',url=cfg['archive_url'],expected_bytes=cfg['archive_bytes'])
                archive,identity=download(cfg,a.out,event);event('header_scan_begin',archive_sha256=identity['sha256'])
                summary=scan_archive(archive,catalog,a.out,cfg,event)
                summary.update(experiment_id=experiment,source_commit=commit,archive=identity,controls=result.testsRun,
                    official_metadata_archive_sha256=cfg['metadata_archive_sha256'],test_scp_sha256=cfg['test_scp_sha256'],speaker_info_sha256=cfg['speaker_info_sha256'])
            for row in manifest['files']:need(sha(root/row['path'])==row['sha256'],'source_changed_during_run')
            need('torch' not in sys.modules and 'transformers' not in sys.modules,'unexpected_model_import')
            event('run_complete',status=summary['status']);put(a.out/'SUMMARY.json',summary);put(a.out/'GATE.json',dict(status=summary['status'],experiment_id=experiment,source_commit=commit,summary_sha256=sha(a.out/'SUMMARY.json'),model_calls=0,GPU_calls=0))
            print(json.dumps(summary,indent=2))
        except BaseException:
            (a.out/'failure.txt').write_text(traceback.format_exc(),encoding='utf8');event('run_failed_raw_preserved')
            put(a.out/'GATE.json',dict(status='FAIL_HEADER_OR_TRANSPORT_CENSUS_RAW_PRESERVED',experiment_id=experiment,source_commit=commit,model_calls=0,GPU_calls=0));raise

if __name__=='__main__':main()
