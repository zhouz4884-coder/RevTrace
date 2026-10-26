"""Read-only recovery clocks. Never substitutes final EOF for pre-crash debt."""
from pathlib import Path
import json,csv,struct,hashlib
P=Path(__file__).resolve().parent
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025'/P.name
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(s) for s in p.read_text().splitlines() if s]
def frames(p):
    raw=p.read_bytes();at=0;out=[]
    while at+4<=len(raw):
        n=struct.unpack_from('>I',raw,at)[0];end=at+4+n+32
        if end>len(raw):break
        body=raw[at+4:at+4+n];assert hashlib.sha256(body).digest()==raw[at+4+n:end]
        out.append(json.loads(body));at=end
    return out
def main():
    dest=O/'RECOVERY_CLOCKS_v2.json';assert not dest.exists();out=[]
    for stage in ['post_sync_pilot','fault','post_sync']:
        done=read(O/stage/'SUMMARY.json');freeze=read(O/stage/'FREEZE.json')
        for name,c in zip(done['completed'],freeze['cells']):
            E=O/stage/name;D=E/'attempt1';k=read(E/'KILL.json');at=k['kill_perf']
            init={s['session_id']:s['state']['audio_frontier_window'] for s in read(D/'initial_states.json')}
            source=frames(E/'input.wal.pre-recovery')
            snap=next(r['snapshot'] for r in reversed(source) if r['kind']=='envelope-snapshot')
            A={int(sid):v['accepted'] for sid,v in snap['sessions'].items()}
            for ack in k['server_input_ACKs']:assert A[ack['session_id']]>=ack['to_sample']
            views=rows(D/'consumer.jsonl');old=[];debt=[]
            for sid,F in init.items():
                if F:
                    ts=[v['observed_perf'] for v in views if v['session_id']==sid and v['certified_frontier']>=F]
                    assert ts;old.append(min(ts))
                if A[sid]>F:
                    ts=[v['observed_perf'] for v in views if v['session_id']==sid and v['certified_frontier']>=A[sid]]
                    assert ts;debt.append(min(ts))
            new=[v['observed_perf'] for v in views if v['certified_frontier']>init[v['session_id']]]
            ready=read(D/'EXECUTORS_READY.json')['observed_perf']
            out.append(dict(stage=stage,episode=name,adapter=c['adapter'],method=c['method'],repeat=c['repeat'],
                readiness=c['readiness'],kernel=c['kernel'],
                RTO_view_all_previous_durable_facts=max(old)-at if old else None,
                RTO_new_first_fresh_certified_consumption=min(new)-at if new else None,
                RTO_precrash_accepted_debt=max(debt)-at if debt else None,
                RTO_final_offered_certified_consumption=max(v['observed_perf'] for v in views)-at,
                accepted_uncertified_at_fault_audio_seconds=sum(max(0,A[sid]-F) for sid,F in init.items())/16000,
                all_previous_durable_facts_consumed_before_executors_ready=bool(old) and max(old)<ready,
                all_previous_durable_facts_consumed_before_executors_ready_margin=ready-max(old) if old else None,
                original_arrival_origin=read(E/'CONTEXT.json')['origin_perf'],source_count=len(init),
                scope='process-group cold restart, actual local Consumer, no deadline reset; no browser/network/power-loss claim'))
    dest.write_text(json.dumps(dict(status='PASS_DISTINCT_RECOVERY_CLOCKS',runs=out,
        supersedes='earlier auxiliary kill_to_all_accepted_debt_drain_seconds was final offered consumption, not pre-crash-only debt; use these explicit names'),indent=2)+'\n')
    with (O/'RECOVERY_CLOCKS_v2.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    print(json.dumps(dict(status='PASS',runs=len(out))))
if __name__=='__main__':main()
