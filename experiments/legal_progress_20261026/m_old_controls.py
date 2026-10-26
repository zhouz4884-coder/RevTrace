"""Truthful old/current facts on original FP16 consumer: diagnostic only."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8');os.environ['HF_HUB_OFFLINE']='1'
from pathlib import Path
import sys,json,time,subprocess,traceback
from memory_gpu_pilot import Neural
from memory_app import answer_messages
W=Path(__file__).resolve().parent;B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
def main():
    import torch
    D=B/'results/revtrace/dependability_20261025/lp1_20261026/m_old_truth_controls_v1';D.mkdir();out=[]
    try:
        assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.use_deterministic_algorithms(True);torch.set_num_threads(4)
        N=Neural(B/'models/Qwen2.5-0.5B-Instruct',0,torch.float16,48)
        tasks=[t for t in json.loads((W/'MEMORY_TASKS_v4.json').read_text())['tasks'] if t['split']=='development']
        (D/'FREEZE.json').write_text(json.dumps(dict(source=json.loads((W/'SOURCE_MANIFEST.json').read_text()),tasks=tasks,contract=N.contract,
            scope='16 original-model truthful-memory diagnostic calls; not application performance nor retry repair'),indent=2)+'\n')
        for t in tasks:
            for state in ['old','new']:
                req=N.prepare(answer_messages(t,t['expected_'+state]))
                for rep in [0,1]:
                    r=N.generate(req);out.append(dict(task=t['id'],state=state,repeat=rep,actual=r,faithful=r['value']==t['expected_'+state],
                        matches_current_fact=r['value']==t['expected_new']))
        classes=[]
        for t in tasks:
            old=[r['matches_current_fact'] for r in out if r['task']==t['id'] and r['state']=='old'];new=[r['matches_current_fact'] for r in out if r['task']==t['id'] and r['state']=='new']
            assert len(set(old))==len(set(new))==1
            classes.append(dict(task=t['id'],category=('current-correct_old-wrong' if new[0] and not old[0] else 'current-wrong_old-correct' if old[0] and not new[0] else 'both-correct' if old[0] else 'both-wrong')))
        (D/'SUMMARY.json').write_text(json.dumps(dict(status='COMPLETE',calls=len(out),rows=out,classes=classes),indent=2)+'\n')
    except BaseException:(D/'STOP.json').write_text(json.dumps(dict(error=traceback.format_exc(),calls=out),indent=2)+'\n');raise
if __name__=='__main__':main()
