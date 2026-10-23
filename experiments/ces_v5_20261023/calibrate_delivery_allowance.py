"""CPU reconstruction of historical row-complete to durable/Consumer delay.

Only V4 development cells are read. No model is run. The P90 allowance is an
empirical scheduling estimate shared by all arms, not a deadline guarantee.
"""
from pathlib import Path
from collections import defaultdict
import csv
import gzip
import hashlib
import json
import math
import statistics

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'causal_evidence_scheduling_20261023'
OUT=HERE/'calibration_v3'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf8'))
def q(values,p):
    values=sorted(values);x=(len(values)-1)*p;i=int(x);f=x-i
    return values[i] if not f else values[i]+f*(values[i+1]-values[i])
def stats(values):
    return {'count':len(values),'minimum_s':min(values),'median_s':statistics.median(values),
            'mean_s':statistics.mean(values),'p90_s':q(values,.90),'p95_s':q(values,.95),
            'p99_s':q(values,.99),'maximum_s':max(values)}


def main():
    if OUT.exists():raise FileExistsError('Never overwrite a calibration version')
    OUT.mkdir()
    targets_path=OLD/'collected/evidence/formal_diagnosis_v1/TARGETS.csv'
    fronts_path=OLD/'collected/evidence/formal_v1_independent_audit_final/COMMON_FRONTIERS.csv'
    targets={};fronts={};sources=[]
    for path,table,kind in [(targets_path,targets,'targets'),(fronts_path,fronts,'fronts')]:
        sources.append({'path':str(path.relative_to(OLD)),'sha256':sha(path)})
        with path.open(newline='',encoding='utf8') as stream:
            for row in csv.DictReader(stream):
                if not row['cell'].startswith('development-'):continue
                key=(row['cell'],int(row['session']),int(row['window'])) if kind=='targets' else (
                    row['cell'],row['source_id'],int(row['frontier_sample']))
                if key in table:raise AssertionError(('duplicate source key',kind,key))
                table[key]=row
    rows=[];anomalies=[];cell_origins=defaultdict(list)
    for path in sorted((OLD/'collected/canonical_witnesses').glob('development-*.jsonl.gz')):
        cell=path.name[:-9]
        sources.append({'path':str(path.relative_to(OLD)),'sha256':sha(path)})
        metadata=OLD/'collected/cell_metadata'/(cell+'-sessions.json.gz')
        sources.append({'path':str(metadata.relative_to(OLD)),'sha256':sha(metadata)})
        with gzip.open(metadata,'rt',encoding='utf8') as stream:
            sessions={r['session_id']:r for r in json.load(stream)}
        with gzip.open(path,'rt',encoding='utf8') as stream:
            for line in stream:
                witness=json.loads(line);j=witness['job'];event=witness['actual_commit_event']
                receipt=witness['selected']['_row_receipt'];sid=j['session_id']
                try:
                    target=targets[cell,sid,j['end_window']]
                    frontier=fronts[cell,j['source_id'],j['audio_end_sample']]
                    session=sessions[sid]
                    assert session['source_id']==j['source_id']
                    assert j['role']=='authority' and event['job_id']==j['job_id']
                    assert event['audio_end_sample']==j['audio_end_sample']
                    release=float(session['offset'])+j['audio_end_sample']/16000
                    origin=j['audio_ready_perf']-release
                    origin_event=j['audio_ready_perf']-event['audio_ready']
                    row_end=j['enqueue_perf']+float(target['worker_queue_s'])+float(target['row_result_after_start_s'])
                    install=j['audio_ready_perf']+float(frontier['commit'])
                    consumer=j['audio_ready_perf']+float(frontier['certified_consumer'])
                    install_event=origin_event+event['installed']
                    row_to_owner=install-row_end;row_to_consumer=consumer-row_end
                    item={'cell':cell,'source_id':j['source_id'],'session_id':sid,'job_id':j['job_id'],
                        'operation':j['ces_operation'],'frontier_sample':j['audio_end_sample'],
                        'enqueue_perf':j['enqueue_perf'],'audio_ready_perf':j['audio_ready_perf'],
                        'worker_queue_s':float(target['worker_queue_s']),
                        'row_result_after_start_s':float(target['row_result_after_start_s']),
                        'reconstructed_row_result_perf':row_end,'receipt_terminal_perf':receipt['terminal_perf'],
                        'receipt_rendered_perf':receipt['rendered_perf'],'receipt_emitted_perf':receipt['emitted_perf'],
                        'reconstructed_owner_install_perf':install,'event_owner_install_perf':install_event,
                        'reconstructed_certified_consumer_perf':consumer,
                        'row_to_owner_install_s':row_to_owner,'row_to_certified_consumer_s':row_to_consumer,
                        'owner_to_certified_consumer_s':consumer-install,
                        'row_vs_rendered_abs_error_s':abs(row_end-receipt['rendered_perf']),
                        'install_crosscheck_abs_error_s':abs(install-install_event),
                        't0_from_sessions':origin,'t0_from_commit_audio_ready':origin_event,
                        't0_crosscheck_abs_error_s':abs(origin-origin_event)}
                    rows.append(item);cell_origins[cell].append(origin)
                    # Preserve every signed raw difference. The tolerance only
                    # recognizes sub-microsecond floating-clock arithmetic.
                    checks={'t0_crosscheck':abs(origin-origin_event)<=1e-7,
                        'row_result_crosscheck':abs(row_end-receipt['rendered_perf'])<=1e-7,
                        'install_crosscheck':abs(install-install_event)<=1e-7,
                        'row_clock_order':receipt['terminal_perf']<=row_end+1e-7 and row_end<=receipt['emitted_perf']+1e-7,
                        'nonnegative_owner_delivery':row_to_owner>=-1e-7,
                        'nonnegative_consumer_delivery':row_to_consumer>=-1e-7,
                        'consumer_after_install':consumer>=install-1e-7,
                        'finite_clocks':all(math.isfinite(v) for v in [origin,row_end,install,consumer])}
                    if not all(checks.values()):anomalies.append({'cell':cell,'job_id':j['job_id'],'checks':checks,'raw':item})
                except Exception as error:
                    anomalies.append({'cell':cell,'job_id':j.get('job_id'),'error':repr(error)})
    for cell,values in cell_origins.items():
        if max(values)-min(values)>1e-7:
            anomalies.append({'cell':cell,'error':'inconsistent reconstructed run t0','range_s':max(values)-min(values)})
    with (OUT/'DELIVERY_ROWS.csv').open('w',newline='',encoding='utf8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (OUT/'ANOMALIES.json').write_text(json.dumps(anomalies,indent=2,allow_nan=False)+'\n')
    if anomalies:
        (OUT/'STOP.json').write_text(json.dumps({'status':'ALIGNMENT_FAILED_NO_ALLOWANCE_FROZEN',
            'observations':len(rows),'anomalies':len(anomalies),'raw_differences_retained':True},indent=2)+'\n')
        raise AssertionError(('Historical clock alignment has anomalies',len(anomalies)))
    assert len(cell_origins)==90
    assert len(rows)==len(targets)==len(fronts),(len(rows),len(targets),len(fronts))
    owner_stats=stats([r['row_to_owner_install_s'] for r in rows])
    consumer_stats=stats([r['row_to_certified_consumer_s'] for r in rows])
    source_cal=HERE/'calibration_v2/CALIBRATION.json';cal=read(source_cal)
    value=consumer_stats['p90_s']
    provenance={'source_pool':'V4 development only; validation excluded',
        'scope':'Historical actual row-result to certified local Consumer; CPU reconstruction, no new GPU inference',
        'rows':len(rows),'cells':len(cell_origins),'owner_install_delay':owner_stats,
        'certified_consumer_delay':consumer_stats,'selected_quantile':.90,
        'owner_delivery_seconds':value,'selected_endpoint':'actual certified Consumer application',
        'interpretation':'Empirical common allowance used by all arms; not a deterministic bound. Owner install and Consumer clocks remain distinct metrics.',
        'source_calibration_sha256':sha(source_cal),'code_sha256':sha(Path(__file__)),
        'raw_csv_sha256':sha(OUT/'DELIVERY_ROWS.csv'),'sources':sources,
        'maximum_row_clock_crosscheck_error_s':max(r['row_vs_rendered_abs_error_s'] for r in rows),
        'maximum_install_crosscheck_error_s':max(r['install_crosscheck_abs_error_s'] for r in rows),
        'maximum_t0_crosscheck_error_s':max(r['t0_crosscheck_abs_error_s'] for r in rows),
        'anomalies':0,'fresh_GPU_calls':0}
    cal['v5_risk_model']['owner_delivery_seconds']=value
    cal['v5_risk_model']['delivery_calibration']=provenance
    cal['schema']='CES-V5-shared-physical-risk-v3-with-delivery'
    (OUT/'CALIBRATION.json').write_text(json.dumps(cal,indent=2,allow_nan=False)+'\n',encoding='utf8')
    summary=dict(provenance,calibration_sha256=sha(OUT/'CALIBRATION.json'))
    (OUT/'SUMMARY.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in summary.items() if k!='sources'},indent=2))


if __name__=='__main__':main()
