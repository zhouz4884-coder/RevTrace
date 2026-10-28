"""Freeze 36 old-development cells; preparation performs no model calls."""
from pathlib import Path
from collections import Counter
import hashlib,json,random

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_physical_retirement_20261028'
O=B+'/results/revtrace/physical_retirement_20261028'
COMMIT='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf'
SOURCE_SHA='19547df369c2899d4cb0eec49d137eff7f160802668072033ae9197565771625'
MANIFEST=B+'/results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json'
SEED=2026102801

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    m=ROOT/'experiments/ces_v6_abcd_20261025/evidence/inputs/development_manifest.json'
    source=ROOT/'experiments/physical_retirement_20261028/packages/SOURCE_v3.json'
    assert sha(m)=='8904fa5b16cb5d2c1f75d101079c6b7f640c2817b873cb92e816eecb694ea1bc'
    assert sha(source)==SOURCE_SHA and json.loads(source.read_text())['code_commit']==COMMIT
    old=json.loads(m.read_text());rows=old['sessions'];assert len(rows)==16
    # Metadata-nested load; no H3 source selection or outcome is consumed.
    points=[dict(point='c8-sync',sessions=8,arrival='sync',question='low-overlap convergence and known feasible development region'),
      dict(point='c8-staggered',sessions=8,arrival='staggered',question='same eight sources near the D2 boundary with fragmented batches'),
      dict(point='c16-staggered',sessions=16,arrival='staggered',question='nested higher offered concurrency; source-mixture change reported explicitly')]
    arms=['R0_S0','R0_S1','R1_S0','R1_S1'];rng=random.Random(SEED)
    base=arms[:];rng.shuffle(base)
    blocks=[]
    for repeat in range(3):
        order=points[:];rng.shuffle(order)
        blocks.extend((repeat,p) for p in order)
    rotations=[i%4 for i in range(9)];rng.shuffle(rotations)
    cells=[]
    for block_index,((repeat,p),rotation) in enumerate(zip(blocks,rotations)):
        order=base[rotation:]+base[:rotation]
        for position,arm in enumerate(order):
            retain='yes' if arm.startswith('R1') else 'no'
            consumer='two_lane' if arm.endswith('S1') else 'checked_snapshot'
            cid=f"stability-{p['point']}-{arm.lower()}-r{repeat}"
            out=O+'/dsn_service_stability_v1/'+cid
            argv=[B+'/envs/revbatch-cu128/bin/python','-B',P+'/source_v3/retirement_service.py',
                '--out',out,'--source-manifest',P+'/SOURCE_v3.json','--manifest',MANIFEST,
                '--model',B+'/models/Qwen3-ASR-1.7B','--adapter','qwen','--policy','row_complete',
                '--method','dgft_original','--rho','1','--sessions',str(p['sessions']),
                '--arrival',p['arrival'],'--repeat',str(repeat),'--retain',retain,
                '--confirmation-consumer',consumer,'--watchdog-seconds','2.0',
                '--service-timeout','240.0','--wall-timeout','420.0']
            cells.append(dict(cell_id=cid,phase='service_stability',cohort=p['point'],
                arm=arm,adapter='qwen',rho=1,arrival=p['arrival'],repeat=repeat,
                sessions=p['sessions'],retain=retain,confirmation_consumer=consumer,
                policy='row_complete',method='dgft_original',fixture=None,
                model=B+'/models/Qwen3-ASR-1.7B',manifest=MANIFEST,manifest_sha256=sha(m),
                output=out,argv=argv,run_order_index=len(cells),block_index=block_index,
                within_block_position=position,paired_block=f"stability-{p['point']}-r{repeat}",
                scope='old-development timing repeat; never independent source confirmation'))
    assert len(cells)==36 and len({c['output'] for c in cells})==36
    balance={arm:dict(Counter(c['within_block_position'] for c in cells if c['arm']==arm)) for arm in arms}
    assert all(max(x.values())-min(x.values())<=1 for x in balance.values())
    plan=dict(experiment_id='REVTRACE-DSN-SERVICE-STABILITY-20261028-V1',
        status='FROZEN_36_CELLS_NOT_LAUNCHED_BY_PREPARATION',code_commit=COMMIT,
        source_manifest_sha256=SOURCE_SHA,execution_source=P+'/source_v3',source_manifest=P+'/SOURCE_v3.json',
        original_manifest=MANIFEST,original_manifest_sha256=sha(m),
        points=points,cohorts=[dict(cohort=p['point'],source_ids=[r['source_id'] for r in rows[:p['sessions']]],
            speakers=[r['source_id'].split('-')[0] for r in rows[:p['sessions']]],
            selected_audio_seconds=sum(r['duration'] for r in rows[:p['sessions']])) for p in points],
        cells=cells,randomization=dict(seed=SEED,method='randomized point order in each of three waves; randomized near-balanced Latin rotations within paired four-arm blocks',
            arm_position_counts=balance,all_fresh_processes=True),
        shared_contract=dict(display_slo_seconds=2.,commit_slo_seconds=8.,authority_rho=1,
            fine_seconds=2.,max_new_tokens=256,microbatch=16,proposal_dtype='float16',authority_dtype='float32',
            proposal_GPU=0,authority_GPU=1,physical_retirement='row_complete',fixtures=None,
            protocol_kernel=True,D1=True,input_WAL=True,canonical_WAL=True,actual_Consumer=True,
            no_deadline_reset=True,denominator='all offered source audio/frontiers, including misses'),
        primary=dict(endpoints=['whole-run original D2/C8 P99 pass','all-offered dual-deadline audio credit',
            'actual Consumer audio-frontier rollback and deficit area','per-run quality and board energy'],
            interaction='Y11-Y10-Y01+Y00 per point and timing repeat; keep all 9 paired blocks',
            mechanism='complete witnessed compatible/incompatible ahead updates and actual critical-path stages; no posthoc time-shift or idealized replay',
            unit='16 reused development sources nested at 8/16; three timing replicates are not three independent audio samples',
            decision='describe measured operating region, natural convergence and miss causes; failure does not authorize more parameter search or relaxed deadlines'),
        before_results=dict(hypotheses=['c8-sync should contain few compatible-ahead opportunities and arms may converge',
            'c8-staggered changes batch formation/host synchronization and probes the observed D2 boundary',
            'c16-staggered increases concurrency and may fail D2; extra preservation cannot fix all overload'],
            adaptive_extension='none without a separately stated scientific reason and a new frozen plan',
            holdout_outcome_used_for_selection=False,source_selection='original metadata order first8 and all16'),
        evidence_paths=dict(raw_results=O+'/dsn_service_stability_v1',controller=O+'/dsn_service_stability_controller_v1',
            aggregate=O+'/dsn_service_stability_analysis_v1',local_family='experiments/dsn_service_stability_20261028'),
        required_prelaunch='no-argument local repository preflight; clean source/full byte manifest; full commit locally resolvable; idle GPU; environment/config/raw/summary/decision records before first model call',
        old_development_basis=dict(sync_D99=1.413405722752213,sync_C99=1.6947506848722693,
            staggered_D99=2.034259559167548,staggered_C99=2.2068458401598026,
            sync_batches=27,staggered_batches=50,sync_input_syncs=18,staggered_input_syncs=67,
            basis='dev_v3 actual Qwen R1_S1 cells only; raw critical-path recount is a separate artifact'),
        new_model_calls_by_preparation=0)
    out=HERE/'PLAN_v1.json'
    with out.open('x',encoding='utf8') as f:json.dump(plan,f,indent=2,allow_nan=False);f.write('\n')
    receipt=dict(plan_file=out.name,plan_sha256=sha(out),plan_bytes=out.stat().st_size,
        source_commit=COMMIT,source_manifest_sha256=SOURCE_SHA,builder_sha256=sha(Path(__file__)),
        remote_plan=P+'/DSN_SERVICE_STABILITY_PLAN_v1_FROZEN.json',GPU_calls=0)
    with (HERE/'PLAN_RECEIPT_v1.json').open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
