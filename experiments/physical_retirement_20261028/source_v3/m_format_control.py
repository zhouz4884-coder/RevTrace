"""64 validation-only content-preserving-shape controls. Old320 frozen."""
from pathlib import Path
import json,sys,subprocess,traceback,multiprocessing as mp
from m_orthogonal import Actor,episode,stable_tasks,Power,put,sha,METHODS,B
W=Path(__file__).resolve().parent;O=B/'results/revtrace/dependability_20261025/lp1_20261026'
def main():
    D=O/'m_format_v1';D.mkdir();log=[];rows=[];actors=[];power=None
    try:
        assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
        source=json.loads((W/'SOURCE_MANIFEST.json').read_text())
        import hashlib
        for r in source['files']:assert hashlib.sha256((W/r['path']).read_bytes()).hexdigest()==r['sha256']
        prior=json.loads((O/'m_gpu_v2/SELF_CHECKS.json').read_text());assert all(c['repeat_equal'] and c['full_self_accept'] for c in prior)
        tasks=[t for t in stable_tasks() if t['split']=='validation']
        put(D/'FREEZE.json',dict(source=source,tasks=tasks,conditions=['current-coherent-content-only'],methods=METHODS,repeats=2,expected=64,
            gate='same native provider/effective selection as passed M v2; no re-tuning; preserve all non-destination bytes and outside token IDs plus EOS',
            diagnosis='Main320 coherent substitutions were schema-valid but normalized whitespace. This extension isolates content from that formatting cue; old results unchanged.'))
        ctx=mp.get_context('spawn');P=Actor(ctx,'proposal',0,log);actors.append(P);A=Actor(ctx,'authority',1,log);actors.append(A)
        all_tasks=stable_tasks();contract=sha(dict(A=A.contract,P=P.contract,adapter='orthogonal-stable-id-memory-v1',tasks=all_tasks));power=Power(D/'power.jsonl')
        for rep in range(2):
            for task in tasks:
                k=(rep+int(task['id'].split('-')[-1]))%4
                for method in METHODS[k:]+METHODS[:k]:
                    E=D/f'{len(rows):03}-{task["id"]}-{method}-r{rep}'
                    rows.append(episode(E,task,'current-coherent',method,rep,P,A,power,contract,log,True))
                    put(D/'PROGRESS.json',dict(status='RUNNING',completed=len(rows),expected=64))
        put(D/'SUMMARY.json',dict(status='COMPLETE',episodes=64,rows=rows))
    except BaseException:put(D/'STOP.json',dict(error=traceback.format_exc(),completed=len(rows)));raise
    finally:
        put(D/'CALLS.json',log)
        if power:power.close()
        for actor in actors:actor.close()
if __name__=='__main__':main()
