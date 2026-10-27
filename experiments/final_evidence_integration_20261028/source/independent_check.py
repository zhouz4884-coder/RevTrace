"""Second implementation: reconstruct integration facts from archived raw members.

Does not import the integration calculators, scorer, production runtime or admit.
This is an evidence recount, not a second model experiment or semantic proof.
"""
from pathlib import Path
import argparse,hashlib,json,platform,subprocess,sys,tarfile


def sha(b):return hashlib.sha256(b).hexdigest()
def norm(x):return sha(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode())
def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    root=a.repo;S=Path(__file__).parent;m=json.loads(a.source_manifest.read_text())
    assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==m['code_commit']
    assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain'],text=True).strip()
    for r in m['files']:assert sha((S/r['path']).read_bytes())==r['sha256']
    C=root/'experiments/context_recovery_20261028';I=root/'experiments/final_evidence_integration_20261028';a.out.mkdir()
    save(a.out/'ENVIRONMENT.json',dict(python=sys.version,platform=platform.platform(),GPU_calls=0))
    save(a.out/'FREEZE.json',dict(experiment_id='REVTRACE-INDEPENDENT-FINAL-RECOUNT-20261028',code_commit=m['code_commit'],source_manifest_sha256=sha(a.source_manifest.read_bytes()),environment_sha256=sha((a.out/'ENVIRONMENT.json').read_bytes()),raw_result_location=str(a.out),aggregate_summary_location=str(a.out/'RESULT.json'),gate_decision_location=str(a.out/'GATE.json'),input_cuts=['publication_update_v2','publication_update_v7','publication_update_v9'],scope='independent code over the same frozen real observations; zero new GPU calls'))
    opened={};used={}
    for v in ['v2','v7','v9']:
        D=C/('publication_update_'+v)
        if not D.exists():D=C/'updates/20261028_bounded_terminal'/('publication_update_'+v)
        t=tarfile.open(D/'COMPLETED_RAW_RECORDS.tar.gz');ix=json.loads((D/'RAW_INDEX.json').read_text());opened[v]=(t,{r['path']:r for r in ix['files']})
    def raw(v,name):
        t,ix=opened[v];b=t.extractfile(name).read();q=ix[name];assert len(b)==q['bytes'] and sha(b)==q['sha256'];used[v+':'+name]=sha(b);return b
    def obj(v,name):return json.loads(raw(v,name))
    def lines(v,name):return [json.loads(x) for x in raw(v,name).splitlines() if x]
    try:
        D=I/'records_v2';ci=json.loads((D/'RAW_INDEX.json').read_text())
        for r in ci['files']:b=(D/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
        cost=json.loads((D/'cost_v2/RESULT.json').read_text());native=json.loads((D/'native_v2/RESULT.json').read_text())
        bcount=0;fcount=0
        for r in cost['rows']:
            pre='dev_v10_c16_staggered_r0_revtrace_b040_prior/'+r['policy']+'/attempt0/'
            # Cell folder includes an arm prefix; use the frozen summary mapping.
            summ=obj('v9','dev_v10_c16_staggered_r0_revtrace_b040_prior/SUMMARY.json')
            cell=next(c for c,q in zip(summ['completed'],summ['rows']) if q['policy']==r['policy'])
            pre='dev_v10_c16_staggered_r0_revtrace_b040_prior/'+cell+'/attempt0/'
            trace=obj('v9',pre+'kernel_trace.json')['events'];batches=lines('v9',pre+'worker_batch_accounting.jsonl');events=lines('v9',pre+'events.jsonl')
            workers={b['worker'] for b in batches}
            for w in workers:
                le=[x for x in trace if x.get('operation')==w and x['kind'] in ['dispatch','batch-drained']]
                assert len(le)%2==0 and all(x['kind']==('dispatch' if i%2==0 else 'batch-drained') for i,x in enumerate(le))
                intervals=[(le[i]['observed_perf'],le[i+1]['observed_perf']) for i in range(0,len(le),2)]
                bs=sorted([b for b in batches if b['worker']==w],key=lambda b:b['worker_started_perf']);assert len(bs)==len(intervals)
                role='proposal' if w.startswith('proposal') else 'authority';q=r['costs'][role]
                assert q['rows']==sum(len(b['job_ids']) for b in bs)
                assert abs(q['receipt_bound_paid_lease']['sum']-sum(y-x for x,y in intervals))<1e-7
                assert abs(q['physical_worker_span']['sum']-sum(b['batch_drained_perf']-b['worker_started_perf'] for b in bs))<1e-7
                assert abs(q['synchronized_model_call_wall']['sum']-sum(p['completed_perf']-p['started_perf'] for b in bs for p in b['phases']))<1e-7
                assert abs(sum(q['parts_seconds'].values())-q['receipt_bound_paid_lease']['sum'])<1e-7
                assert q['batches']==sum(x['batches'] for x in q['nonuse_partition'].values())
                bcount+=len(bs)
            covered={(x['session_id'],x['window']) for x in events if x['kind']=='proposal-skip'}
            expired={(x['session_id'],x['window']) for x in events if x['kind']=='private-deadline-retired'}
            assert not covered&expired and len(covered)==r['canonical_covered_unissued'] and len(expired)==r['deadline_expired_unissued']
            frontiers=[x for x in cost['authority_frontiers'] if x['policy']==r['policy']];assert len(frontiers)==135
            for f in frontiers:
                ks=['prerequisite_wait','owner_queue','IPC_to_worker','worker_to_host_row','host_row_to_install','install_to_actual_consumer']
                assert min(f[k] for k in ks)>=-1e-5 and abs(sum(f[k] for k in ks)-f['latency'])<1e-7
            fcount+=len(frontiers)
        ncount=0;edges=0;bad=0
        for study,v in [('native_v8_pilot_v1','v2'),('native_strong_v10_v1','v7')]:
            stage=obj(v,study+'/SMOKE_SUMMARY.json')
            for cell in stage['rows']:
                pre=study+'/cells/'+cell['id']+'/'
                db=obj(v,pre+'DATABASE_DUMP.json');au=obj(v,pre+'INDEPENDENT_AUDIT.json')
                requests={x['op']:json.loads(x['frozen']) for x in db['requests']}
                sel={x['op']:json.loads(x['evidence']) for x in db['selections']}
                for x in db['events']:
                    if x['kind']=='model-unfulfilled':y=json.loads(x['payload']);sel[y['op']]=y['evidence']
                receipts={x['seq']:json.loads(x['receipt']) for x in db['admissions']}
                for op,f in requests.items():
                    x=next(r for r in native['rows'] if (r['study'],r['cell'],r['cycle'])==(study,cell['id'],f['cycle']))
                    e=sel[op];assert norm(e['actual_input_ids'])==x['actual_neural_input_ids_sha256']
                    assert json.loads(e['request']['messages'][-1]['content'])['prior_memory']==receipts[f['parent']]['value']==x['prior_memory']
                    assert norm(e.get('value'))==x['returned_value_sha256']
                    assert x['actual_downstream_input']==(f['parent']>0)
                    if x['committed']:
                        score=next(y['score'] for y in au['task_scores'] if y['op']==op)
                        assert x['step_success']==score['current_step_success']
                    else:assert x['step_success'] is False
                    ncount+=1;edges+=x['actual_downstream_input'];bad+=x['consumed_unauthorized_previous_value']
        assert ncount==60 and edges==36 and bad==4 and fcount==810
        formal=subprocess.check_output([sys.executable,'-B',str(root/'experiments/input_freeze_20261027/formal/verify_delivery.py')],text=True)
        save(a.out/'RESULT.json',dict(gate='PASS_SECOND_IMPLEMENTATION_RAW_RECOUNT',real_physical_batches=bcount,authority_paths=fcount,offered_native_cycles=ncount,actual_later_consumption_edges=edges,unauthorized_later_consumption_edges=bad,formal_delivery=json.loads(formal),input_members=used,GPU_calls=0,scope='same observations independently recounted, not statistical replication or a second model generation'))
        save(a.out/'GATE.json',dict(gate='PASS_SECOND_IMPLEMENTATION_RAW_RECOUNT',GPU_calls=0))
    except BaseException:
        import traceback
        save(a.out/'STOP.json',dict(error=traceback.format_exc(),GPU_calls=0));raise
    finally:
        for t,ix in opened.values():t.close()


if __name__=='__main__':main()
