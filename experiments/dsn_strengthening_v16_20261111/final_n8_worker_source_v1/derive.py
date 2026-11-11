"""Existing closed-cell host timers only; no model imports or new measurements."""
import argparse,datetime,hashlib,json,os,pathlib,platform,subprocess,sys,unittest
R=pathlib.Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def put(p,x):
    assert not p.exists(),p
    p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def terminal_times(events):
    unique={};duplicates=0
    for event in events:
        if event.get('kind') not in ('completed','abandoned'):continue
        record=event.get('record',{})
        if record:worker=record.get('worker_job_wall_seconds');infer=record.get('model_seconds')
        elif event.get('worker_job_begin_perf') is not None and event.get('worker_job_end_perf') is not None:
            worker=event['worker_job_end_perf']-event['worker_job_begin_perf'];infer=None
        else:worker=infer=None
        row=dict(job_id=event['job_id'],kind=event['kind'],source_id=event.get('source_id'),worker_wall_seconds=worker,observed_infer_wall_seconds=infer)
        if row['job_id'] in unique:
            if unique[row['job_id']]!=row:raise ValueError('contradictory duplicate terminal '+row['job_id'])
            duplicates+=1;continue
        if worker is not None and worker<0:raise ValueError('negative worker timer')
        if infer is not None and (infer<0 or worker is not None and infer>worker+1e-6):raise ValueError('invalid nested infer timer')
        unique[row['job_id']]=row
    return list(unique.values()),duplicates
class Controls(unittest.TestCase):
    def test_duplicate_job_is_counted_once(self):
        e=dict(kind='completed',job_id='e0-j000000001',source_id='s',record=dict(worker_job_wall_seconds=2.,model_seconds=1.5));rows,n=terminal_times([e,e]);self.assertEqual((len(rows),n),(1,1))
    def test_abort_missing_infer_is_NA_not_zero(self):
        rows,n=terminal_times([dict(kind='abandoned',job_id='e0-j000000002',worker_job_begin_perf=10.,worker_job_end_perf=12.)]);self.assertEqual(rows[0]['worker_wall_seconds'],2.);self.assertIsNone(rows[0]['observed_infer_wall_seconds'])
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--selection',required=True);p.add_argument('--out',required=True);a=p.parse_args();m=read(a.manifest)
    def git(*args):return subprocess.check_output(['git','-C',str(R),*args],text=True).strip()
    assert git('rev-parse','HEAD')==m['source_commit'] and not git('status','--porcelain','--untracked-files=all')
    assert set(git('ls-files').splitlines())=={x['path'] for x in m['files']}
    for x in m['files']:assert (R/x['path']).stat().st_size==x['bytes'] and sha(R/x['path'])==x['sha256']
    assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
    selection=read(a.selection);cells=selection['cells'];assert len(cells)==32 and len({c['cell_id'] for c in cells})==32
    out=pathlib.Path(a.out);assert str(out).startswith('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/');out.mkdir(parents=True,exist_ok=False)
    cfg=dict(experiment_id='REVTRACE_FINAL_N8_WORKER_TIMER_DERIVATION_V1',code_commit=m['source_commit'],selection=a.selection,selection_sha256=sha(pathlib.Path(a.selection)),runtime_NN='de0936b2e30179d63aeef6e235cd1af685578c58',input_scope='PILOT first2 Full/Ready8 +next2 Full/Ready8 +last4 Full/Ready16',scope='existing logs finishing arithmetic, not new experiment/model/GPU or CUDA-active-time measurement')
    env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),CUDA_VISIBLE_DEVICES='')
    put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',env);put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=m['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),prelaunch_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    with (out/'controls.log').open('x',encoding='utf8') as f:
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    assert result.wasSuccessful();inputs={};rows=[];jobs=[]
    for cell in cells:
        root=pathlib.Path(cell['raw_result_location']);dispatch={};events=[]
        for attempt in sorted(root.glob('owner_e*')):
            for name in ('dispatch.jsonl','worker_results.jsonl'):
                file=attempt/name;inputs[str(file)]=dict(bytes=file.stat().st_size,sha256=sha(file))
                for line in file.read_bytes().splitlines():
                    record=json.loads(line)
                    if name=='dispatch.jsonl':
                        job=record['job'];assert job['job_id'] not in dispatch;dispatch[job['job_id']]=job
                    else:events.append(record['event'])
        work,dups=terminal_times(events);assert {x['job_id'] for x in work}==set(dispatch),'unclosed/foreign physical job'
        account=cell['job_accounting'];assert account['status']=='PASS_DISJOINT_JOB_ACCOUNTING' and account['dispatches']==len(dispatch)
        counts=account['counts'];expected_completed=counts['selected_installed']+counts['selected_durable_replayed']+counts['fully_discarded'];expected_abort=counts['pre_C_skipped'];assert counts['fenced_terminal']==counts['worker_lifecycle_terminated']==counts['owner_lifecycle_terminated']==0
        assert sum(x['kind']=='completed' for x in work)==expected_completed and sum(x['kind']=='abandoned' for x in work)==expected_abort
        row=dict(cell_id=cell['cell_id'],phase=cell['phase'],source_id=cell['source_id'],speaker_id=cell['speaker_id'],repeat=cell['repeat'],strategy=cell['strategy'],unique_jobs=len(work),duplicate_terminals=dups,
            worker_wall_s_observed=sum(x['worker_wall_seconds'] for x in work if x['worker_wall_seconds'] is not None),worker_timer_missing_jobs=sum(x['worker_wall_seconds'] is None for x in work),
            infer_wall_s_observed=sum(x['observed_infer_wall_seconds'] for x in work if x['observed_infer_wall_seconds'] is not None),infer_timer_missing_jobs=sum(x['observed_infer_wall_seconds'] is None for x in work),
            completed_jobs=expected_completed,abandoned_jobs=expected_abort,completed_worker_wall_s=sum(x['worker_wall_seconds'] for x in work if x['kind']=='completed' and x['worker_wall_seconds'] is not None),abandoned_worker_wall_s=sum(x['worker_wall_seconds'] for x in work if x['kind']=='abandoned' and x['worker_wall_seconds'] is not None))
        assert row['worker_timer_missing_jobs']==0;rows.append(row);jobs.extend(dict(x,cell_id=cell['cell_id']) for x in work)
    for path,identity in inputs.items():assert pathlib.Path(path).stat().st_size==identity['bytes'] and sha(pathlib.Path(path))==identity['sha256']
    aggregates={}
    numeric=('unique_jobs','duplicate_terminals','worker_wall_s_observed','worker_timer_missing_jobs','infer_wall_s_observed','infer_timer_missing_jobs','completed_jobs','abandoned_jobs','completed_worker_wall_s','abandoned_worker_wall_s')
    for arm in ('fullcall','ready_only'):
        own=[r for r in rows if r['strategy']==arm];assert len(own)==16;aggregates[arm]=dict(cells=16,**{k:sum(r[k] for r in own) for k in numeric});aggregates[arm]['total_infer_wall_s']=None if aggregates[arm]['infer_timer_missing_jobs'] else aggregates[arm]['infer_wall_s_observed']
        pilot=[r for r in own if r['phase']=='PILOT24_V2'];observed=sum(r['worker_wall_s_observed'] for r in pilot);assert abs(observed-selection['pilot_expected_worker_s'][arm])<1e-7,'pilot paid-work crosscheck differs'
    put(out/'INPUT_HASHES.json',inputs);put(out/'PER_CELL.json',rows);put(out/'PER_JOB.json',jobs)
    summary=dict(status='PASS_FINAL32_CLOSED_JOB_WORKER_TIMER_DERIVATION',source_commit=m['source_commit'],cells=32,speakers=8,aggregates=aggregates,controls_passed=2,model_calls=0,GPU_calls=0,source_hashes_unchanged=True,original_stage_worker_timer_definition='completed.record.worker_job_wall_seconds; abandoned.end-begin; infer=completed.record.model_seconds; missing abort infer is NA, never0',scope=cfg['scope']);put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['status'],summary_sha256=sha(out/'SUMMARY.json')));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
