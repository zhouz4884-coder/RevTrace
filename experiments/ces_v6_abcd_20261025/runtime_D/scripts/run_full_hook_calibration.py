"""Matched entire-hook on/off cost; correctness publication remains enabled."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--data-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--code-commit',required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    for r in json.loads((ROOT/'SOURCE_MANIFEST.json').read_text())['files']:assert hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256']
    config={'experiment_id':'PHASE-N-FULL-HOOK-CALIBRATION','code_commit':a.code_commit,'repeats':3,
        'modes':['fine_certified','coarse'],'hooks':[False,True],
        'scope':'Toggle lifecycle CUDA synchronization markers/IPC telemetry, enriched enqueue/WAL events, wait observer and rich capture. Retain A/B/C and required publication/ACK in BOTH arms.'}
    (a.output/'RUN.json').write_text(json.dumps(config,indent=2)+'\n');done=[]
    try:
        for repeat in range(3):
            for mode in config['modes']:
                for enabled in ([False,True] if repeat%2==0 else [True,False]):
                    assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True).strip()
                    name=f'{mode}-hooks{int(enabled)}-r{repeat}';(a.output/'logs').mkdir(exist_ok=True)
                    command=[sys.executable,'-u',str(ROOT/'scripts/run_tc_live_qwen.py'),'--model',str(a.data_root/'models/Qwen3-ASR-1.7B'),
                        '--manifest',str(a.data_root/'datasets/tc_live_20260906/manifest.json'),'--output',str(a.output/name),'--code-commit',a.code_commit,
                        '--study-id',config['experiment_id'],'--mode',mode,'--sessions','16','--microbatch','16',
                        '--proposal-barrier','decoupled','--proposal-reconciliation','lazy','--display-protocol','canonical-snapshot-v1','--publish-canonical-display',
                        '--durable-journal-path',str(a.output/'journals'/(name+'.wal')),'--journal-sync-mode','group_ready']
                    if enabled:command+=['--phase-n-instrumentation','--capture-model-inputs']
                    else:command+=['--full-diagnostic-hooks-off']
                    with (a.output/'logs'/(name+'.log')).open('w') as log:r=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                    assert r.returncode==0,name+' failed; preserve raw'
                    done.append(name);(a.output/'PROGRESS.json').write_text(json.dumps({'completed':done,'expected':12},indent=2)+'\n')
                    print(json.dumps({'complete':name,'count':len(done)}),flush=True)
        (a.output/'SUMMARY.json').write_text(json.dumps({'status':'COMPLETE','completed':done},indent=2)+'\n')
    except BaseException as exc:
        (a.output/'STOP.json').write_text(json.dumps({'error':repr(exc),'completed':done},indent=2)+'\n');raise
if __name__=='__main__':main()
