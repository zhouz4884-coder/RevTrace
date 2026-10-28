"""Bounded six-arm fresh-process development pilot with all actual costs.

No formal validation, cap selection or success assumption. Source/config gates
precede GPU use; any failed child stops this queue and retains its output.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
import traceback

W=Path(__file__).resolve().parent
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
from memory_gpu_pilot import Power
from x_service_metrics import audit_episode


def put(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source-manifest',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--sessions',type=int,default=4)
    p.add_argument('--arrival',choices=['sync','staggered'],default='sync')
    p.add_argument('--repeat',type=int,default=0)
    p.add_argument('--rho',type=int,choices=[1,3],default=1)
    p.add_argument('--eta-mode',choices=['conditional','legacy'],default='conditional')
    p.add_argument('--prior-bank',type=Path)
    p.add_argument('--prior-bank-sha256')
    p.add_argument('--implementation',choices=['revtrace','standard'],default='revtrace')
    p.add_argument('--max-wait',type=float,choices=[.15,.4,.75],default=.75)
    p.add_argument('--deadline-reserve',choices=['full_service','raw_slack'],default='raw_slack')
    p.add_argument('--policies',default='immediate,fixed,pending_eta,backpressure,recent_gain,state_aware')
    a=p.parse_args();D=a.output
    if not D.is_relative_to(B/'results/revtrace/freeze_boundary_20261027'):raise ValueError('scoped8TBresult path required')
    if D.exists():raise FileExistsError(D)
    D.mkdir(parents=True);completed=[];summaries=[]
    try:
        if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU already in use; no worker started')
        source=json.loads(a.source_manifest.read_text())
        for f in source['files']:
            if sha(W/f['path'])!=f['sha256']:raise ValueError('source bytes changed: '+f['path'])
        manifest=json.loads(a.manifest.read_text())
        if a.sessions>len(manifest['sessions']):raise ValueError('independent audio required; no session duplication')
        selected=dict(sessions=manifest['sessions'][:a.sessions],
            scope='metadata-first prefix of original16 development sources, no outcome selection; not new independent confirmation')
        put(D/'manifest.json',selected)
        env=dict(python=sys.version,platform=platform.platform(),hostname=platform.node(),
            packages={x:importlib.metadata.version(x) for x in ['torch','transformers','qwen-asr','numpy','soundfile']},
            hardware=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,uuid,driver_version,memory.total','--format=csv,noheader'],text=True))
        put(D/'ENVIRONMENT.json',env)
        if a.prior_bank is not None:
            if not a.prior_bank_sha256 or sha(a.prior_bank)!=a.prior_bank_sha256:raise ValueError('prior bank hash')
        elif a.prior_bank_sha256:raise ValueError('hash without prior bank')
        methods=a.policies.split(',')
        allowed=['immediate','fixed','pending_eta','backpressure','recent_gain','state_aware']
        if len(set(methods))!=len(methods) or any(x not in allowed for x in methods):raise ValueError('unfrozen policy')
        methods=methods[a.repeat%len(methods):]+methods[:a.repeat%len(methods)]
        common=dict(max_wait_seconds=a.max_wait,fixed_wait_seconds=a.max_wait,fixed_condition='pending',
            display_slo_seconds=2.,private_cost_default_seconds=.97841 if a.sessions==4 else 1.53325,
            authority_cost_default_seconds=.99258 if a.sessions==4 else 1.94705,
            service_quantile=.9,history_size=64,lead_threshold_windows=2,
            poll_floor_seconds=.005,initial_recent_wait_seconds=a.max_wait/2,recent_step_seconds=.05,recent_backoff=.5,
            deadline_reserve=a.deadline_reserve,eta_mode=a.eta_mode,eta_min_tail_samples=4,install_cost_default_seconds=.3)
        cells=[dict(policy=m,repeat=a.repeat,sessions=a.sessions,arrival=a.arrival,
                    implementation=a.implementation,rho=a.rho,prior_bank_sha256=a.prior_bank_sha256,wait=dict(common,policy=m)) for m in methods]
        put(D/'FREEZE.json',dict(experiment_id='REVTRACE-FREEZE-BOUNDARY-20261027-PILOT',
            code_commit=source['code_commit'],source_manifest_sha256=sha(a.source_manifest),
            original_manifest_sha256=sha(a.manifest),manifest_sha256=sha(D/'manifest.json'),
            environment_sha256=sha(D/'ENVIRONMENT.json'),cells=cells,expected=len(cells),
            resources='FP16 P GPU0 + FP32 A GPU1, full original Row backend, fixedrho declared per cell, D2/C8, fullkernel, WAL and actualConsumer',
            decision='DEVELOPMENT_FEASIBILITY_ONLY; no statistical superiority claim',
            raw_result_location=str(D),aggregate_summary_location=str(D/'SUMMARY.json'),gate_decision_location=str(D/'GATE.json')))
        for i,cell in enumerate(cells):
            name=f'{i:02}-{cell["policy"]}-c{a.sessions}-{a.arrival}-r{a.repeat}';E=D/name;E.mkdir()
            put(E/'wait.json',cell['wait'])
            put(E/'envelope.json',dict(method='standard_fair' if a.implementation=='standard' else 'fine_fair',budget_audio_seconds=1000.,
                warning_age=100.,critical_age=200.,clear_age=10.,display_slo=2.,
                queue_threshold=10000,reject_new_after_seconds=1000.,tick_seconds=.001))
            put(E/'arrivals.json',dict(offsets=[0. if a.arrival=='sync' else sid*.25 for sid in range(a.sessions)]))
            cmd=[sys.executable,str(W/'runtime/scripts/run_tc_live_qwen.py'),
                '--model',str(B/'models/Qwen3-ASR-1.7B'),'--manifest',str(D/'manifest.json'),
                '--output',str(E/'attempt0'),'--code-commit',source['code_commit'],
                '--study-id','REVTRACE-FREEZE-BOUNDARY-PILOT','--sessions',str(a.sessions),
                '--microbatch','16','--max-new-tokens','256','--timeout','240',
                '--trusted-text-binding','--capture-model-inputs','--result-delivery','row',
                '--protocol-kernel','--kernel-copy-mode','event-cow','--phase-n-instrumentation',
                '--dispatch-wait-config',str(E/'wait.json'),'--wait-study-rho',str(a.rho),
                '--envelope-config',str(E/'envelope.json'),'--arrival-schedule',str(E/'arrivals.json'),
                '--episode-context',str(E/'episode.json'),'--input-journal-path',str(E/'input.wal'),
                '--durable-journal-path',str(E/'canonical.wal')]
            if a.prior_bank is not None:
                cmd += ['--dispatch-wait-prior',str(a.prior_bank),'--dispatch-wait-prior-sha256',a.prior_bank_sha256]
            put(E/'COMMAND.json',dict(argv=cmd,code_commit=source['code_commit']))
            power=Power(E/'episode_power.jsonl')
            try:
                started=time.perf_counter()
                with (E/'runner.log').open('x') as log:
                    child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    put(E/'OWNED_RUNNER.json',dict(pid=child.pid,observed_perf=started,
                        linux_start_ticks=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19]))
                    try:rc=child.wait(timeout=420)
                    except subprocess.TimeoutExpired:
                        # This exact process group was created above for this cell.
                        import signal
                        os.killpg(child.pid,signal.SIGTERM)
                        child.wait(timeout=30)
                        raise RuntimeError('bounded cell timeout; all offered work retained as unfinished')
                ended=time.perf_counter()
                if rc:raise RuntimeError(name+' failed with rc='+str(rc))
                measured=json.loads((E/'attempt0/power_samples.json').read_text())
                put(E/'POWER_MEASURED.json',dict(cold_launch_to_exit_both_GPU_joules=power.joules(started,ended),
                    serving_both_GPU_joules=power.joules(measured['measurement_start_perf'],measured['measurement_end_perf'])))
            finally:power.close()
            summary,frontiers=audit_episode(E,selected)
            summary['dispatch_wait_profile']=json.loads((E/'attempt0/dispatch_wait_profile.json').read_text())
            summary.update(policy=cell['policy'],repeat=a.repeat,rho=a.rho,eta_mode=a.eta_mode,prior_bank_sha256=a.prior_bank_sha256,arrival=a.arrival,implementation=a.implementation,
                           deadline_reserve=a.deadline_reserve,scope='DEVELOPMENT_PILOT')
            put(E/'INDEPENDENT_SUMMARY.json',summary)
            put(E/'FRONTIERS.json',frontiers)
            completed.append(name);summaries.append(summary)
            put(D/'PROGRESS.json',dict(status='RUNNING',completed=completed,expected=len(cells)))
            if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():raise RuntimeError('GPU worker did not drain; queue stopped')
        put(D/'SUMMARY.json',dict(status='COMPLETE_DEVELOPMENT_PILOT',expected=len(cells),completed=completed,rows=summaries))
        put(D/'GATE.json',dict(gate='CPU_AND_GPU_FEASIBILITY_RECORDED',
            performance_superiority='NOT_EVALUATED_FROM_SINGLE_REPEAT',source_commit=source['code_commit']))
    except BaseException:
        put(D/'STOP.json',dict(status='FAILED_PRESERVED',completed=completed,error=traceback.format_exc()))
        raise


if __name__=='__main__':main()
