from pathlib import Path
import csv,json,statistics
W=Path(__file__).resolve().parent;R=W/'formal_collected/formal'
rows=[]
for name in json.loads((R/'SUMMARY.json').read_text())['completed']:
    C=R/name;e=[json.loads(v) for v in (C/'events.jsonl').read_text().splitlines()]
    result=json.loads((C/'result.json').read_text())
    sync=[r for r in e if r['kind']=='wal-physical-timing' and r['phase']=='fsync']
    writes=[r for r in e if r['kind']=='wal-physical-timing' and r['phase']=='write']
    starts={tuple(r['job_ids']):r for r in e if r['kind']=='wal-owner-start'}
    complete=[r for r in e if r['kind']=='wal-owner-complete']
    assert len(sync)==len(writes)==len(starts)==len(complete)
    for r in sync+writes:assert r['completed']>=r['started']
    rows.append({'cell':name,'actual_fsync_calls':len(sync),
        'actual_fsync_seconds':sum(r['completed']-r['started'] for r in sync),
        'actual_write_seconds':sum(r['completed']-r['started'] for r in writes),
        'owner_WAL_call_seconds':sum(r['time']-starts[tuple(r['job_ids'])]['time'] for r in complete),
        'trusted_render_host_wall_seconds':sum(r['host_cpu_wall_seconds'] for r in e if r['kind']=='render-checked'),
        'consumer_CPU_seconds':result['consumer']['consumer_cpu_seconds'],
        'WAL_bytes':(R/'journals'/(name+'.wal')).stat().st_size,
        'IPC_complete_payload_holds':sum(r['kind']=='ipc-complete-delivered' for r in e),
        'sum_observed_row_delivery_hold_seconds_not_GPU_seconds':sum(r['hold_seconds'] for r in e if r['kind']=='ipc-complete-delivered')})
with (W/'N1_AUX_COSTS_v1.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(W/'N1_AUX_COSTS_v1.json').write_text(json.dumps({'status':'PASS_NONADDITIVE_WAL_RENDER_CONSUMER_RECOUNT','cells':54,'rows':rows,
 'limits':'fsync/write counted once per actual WAL call, not repeated per commit; render is host wall not process CPU; total owner CPU and broker serialization CPU are not separately measured; IPC row holds overlap and are not summed into GPU time'},indent=2)+'\n')
print(json.dumps({'cells':54,'fsync_calls':sum(r['actual_fsync_calls'] for r in rows),'WAL_bytes':sum(r['WAL_bytes'] for r in rows)}))
