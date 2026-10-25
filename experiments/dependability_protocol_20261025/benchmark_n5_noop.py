"""CPU-only final-idle snapshot benchmark, not a GPU/end-to-end speedup."""
from pathlib import Path
from types import SimpleNamespace as N
import hashlib,json,statistics,sys,time
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime_n5_v2/src'))
from revtrace.certified_envelope import CertifiedEnvelopeScheduler
from revtrace.degradation_state import CreditBook,Mode
E=W/'n5_pilot_collected_v1/pilot/cde_full-c16-staggered-r0'
r=json.loads((E/'attempt0/result.json').read_text());specs=json.loads((E/'attempt0/sessions.json').read_text())
cfg=json.loads((E/'attempt0/config.json').read_text());snap=r['final_input_snapshot']
states={s['session_id']:N(audio_frontier_window=s['state']['audio_frontier_window'],checkpoint_id=s['state']['checkpoint_id']) for s in r['final_states']}
def build(disabled):
    a=object.__new__(CertifiedEnvelopeScheduler);a.options=cfg['envelope'];a.method='cde_full';a.owner_epoch=1
    a.origin=cfg['episode_origin_perf'];a.fine=2.;a.sample_rate=16000;a.rho=3;a.quantum=96000
    a.sessions={s['session_id']:N(sid=s['session_id'],duration=s['duration'],offset=s['offset'],state=states[s['session_id']],
        audio=bytes(round(s['duration']*64000))) for s in specs}
    a.clock=lambda:a.origin+max(s['offset']+s['duration'] for s in specs)+1
    a.book=CreditBook.restore(snap,states,epoch=1,origin_perf=a.origin)
    a.mode=Mode.NORMAL;a._grant_cursor=0;a._last_ingress_trigger=None;a._ingress_transactions=0;a._ingress_noop_skips=0
    a._diagnostic_disable_ingress_cache=disabled;a._last_input_signature=a._input_signature(a.book)
    def forbidden(*args,**kwargs):raise AssertionError('idle oracle must not write a receipt or change obligations')
    a.input_journal=N(checkpoint=forbidden);a._event=forbidden
    return a
rows=[]
for repeat in range(4):
    for disabled in [False,True]:
        a=build(disabled);before=a.book.snapshot(a.origin);a._ingress()
        cpu=time.thread_time();host=time.perf_counter()
        for _ in range(10000):a._ingress()
        row=dict(repeat=repeat,cache_disabled=disabled,CPU_seconds=time.thread_time()-cpu,
            host_seconds=time.perf_counter()-host,transactions=a._ingress_transactions,noop_skips=a._ingress_noop_skips)
        assert before==a.book.snapshot(a.origin);rows.append(row)
out=dict(status='PASS_CPU_NOOP_ORACLE_ALL_FIELDS_UNCHANGED',rows=rows,neural_GPU_calls=0,
    scope='10000 no-op calls on one16-source final idle snapshot; zero input or canonical actions; no projection or real-time serving counterfactual; Windows thread CPU quantization retained',
    source_sha256=hashlib.sha256((W/'runtime_n5_v2/src/revtrace/certified_envelope.py').read_bytes()).hexdigest())
(W/'N5_NOOP_CPU_BENCHMARK_v2.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'cached_median_CPU':statistics.median(r['CPU_seconds'] for r in rows if not r['cache_disabled']),
    'uncached_median_CPU':statistics.median(r['CPU_seconds'] for r in rows if r['cache_disabled']),
    'scope':out['scope']}))
