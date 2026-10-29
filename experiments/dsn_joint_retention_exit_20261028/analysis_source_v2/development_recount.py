"""Recompute pre-study legal-pressure witnesses from four archived pilot raws."""
from pathlib import Path
import argparse, hashlib, json
from joint_recount import compatible_input, read, verify_source, INPUTS

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--source-manifest',type=Path,required=True)
    a=p.parse_args();commit=verify_source(a.source_manifest);out=[]
    for name in ['row_complete-F2-r0','covered-F2-r0','row_complete-F2-r1','covered-F2-r1']:
        d=a.raw_root/name/'attempt0';events=read(d/'events.jsonl',True);records=read(d/'worker_records.jsonl',True)
        start=next(e['t0_perf'] for e in events if e['kind']=='run-start')
        byid={r['job']['job_id']:r for r in records};pub={e['job_id']:start+e['displayed'] for e in events if e['kind']=='display'}
        rows=[]
        for row in records:
            j,z=row['job'],row['result'];context=z.get('execution_context_audit',{})
            if (j['role']!='proposal' or context.get('fault_override') or
                context.get('executed_prompt_tokens',j.get('fault_actual_prompt_tokens',j['prompt_tokens']))!=j['prompt_tokens']):continue
            for e in events:
                if (e['kind']=='commit' and e['session_id']==j['session_id'] and
                    z['model_started_perf']<=start+e['installed']<z['row_terminal_perf'] and e['audio_end_sample']<j['audio_end_sample']):
                    ok,reason,chain=compatible_input(j,e['audio_end_sample'],e['next_prompt_tokens'],byid,pub)
                    rows.append(dict(job_id=j['job_id'],tokens=z['generated_tokens'],
                        model_to_terminal_seconds=z['row_terminal_perf']-z['model_started_perf'],compatible=ok,reason=reason,chain=chain))
        out.append(dict(cell=name,witnesses=rows))
    result=dict(analysis_id='REVTRACE-JOINT-DEVELOPMENT-PRESSURE-v3',analysis_code_commit=commit,
        neural_execution_commit='1d8c30804a945570429d85d934b3bfcba6171a43',
        method='Nonfault actual decode overlaps installed Canonical update while target F remains uncovered; exact earlier published ancestry reaches selected F/P.',
        scope='Retrospective diagnosis of known development inputs; not every-condition guarantee, natural prevalence or prospective service effect.',
        analysis_source_sha256={n:hashlib.sha256((Path(__file__).parent/n).read_bytes()).hexdigest() for n in ['joint_recount.py','development_recount.py']},
        inputs=INPUTS,cells=out,source_manifest_sha256=hashlib.sha256(a.source_manifest.read_bytes()).hexdigest())
    assert verify_source(a.source_manifest)==commit
    with a.out.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps([dict(cell=r['cell'],count=len(r['witnesses']),compatible=sum(w['compatible'] is True for w in r['witnesses']),
        longest_seconds=max([w['model_to_terminal_seconds'] for w in r['witnesses']],default=0)) for r in out]))

if __name__=='__main__':main()
