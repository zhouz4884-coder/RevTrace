"""Prepare one fixed midpoint locally. Never connects remotely or launches models."""
from pathlib import Path
from collections import Counter
import hashlib,json,math,random,subprocess

F=Path(__file__).resolve().parent;R=F.parents[1];A=F/'analysis_source_v1'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';N=B+'/projects/revtrace_physical_retirement_20261028'
P=B+'/projects/revtrace_dsn_midpoint_continuity_20261029';O=B+'/results/revtrace/physical_retirement_20261028'
COMMIT='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf';SOURCE_SHA='19547df369c2899d4cb0eec49d137eff7f160802668072033ae9197565771625'
MANIFEST=B+'/results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json';SEED=2026102905
def h(p):
    b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')

def main():
    manifest=R/'experiments/ces_v6_abcd_20261025/evidence/inputs/development_manifest.json'
    assert h(manifest)['sha256']=='8904fa5b16cb5d2c1f75d101079c6b7f640c2817b873cb92e816eecb694ea1bc'
    source=R/'experiments/physical_retirement_20261028/packages/SOURCE_v3.json'
    assert h(source)['sha256']==SOURCE_SHA and json.loads(source.read_bytes())['code_commit']==COMMIT
    subprocess.run(['git','cat-file','-e',COMMIT+'^{commit}'],cwd=R,check=True)
    old=json.loads(manifest.read_bytes());assert len(old['sessions'])==16
    rows=old['sessions'][:12];old_plan=json.loads((R/'experiments/dsn_service_stability_20261028/PLAN_v1.json').read_bytes())
    old8=next(x['source_ids'] for x in old_plan['cohorts'] if x['cohort']=='c8-staggered')
    assert [x['source_id'] for x in rows[:8]]==old8
    for key in ['source_id','path','audio_sha256']:assert len({x[key] for x in rows})==12
    selection=dict(source_manifest_path=str(manifest),source_manifest_sha256=h(manifest)['sha256'],
        selection_rule='first12 of original16, original metadata order; no output-based changes',
        first8_exactly_match_existing_c8=True,selected_audio_seconds=sum(x['duration'] for x in rows),
        expected_offered_frontiers=sum(math.ceil(x['duration']/2) for x in rows),
        selected_sources=[dict(original_index=i,**row) for i,row in enumerate(rows)])
    put(F/'SOURCE_SELECTION_v1.json',selection)
    rng=random.Random(SEED);arms=['R0_S0','R0_S1','R1_S0','R1_S1'];base=arms[:];rng.shuffle(base)
    repeats=list(range(3));rng.shuffle(repeats);rotations=[0,1,2];rng.shuffle(rotations);cells=[]
    for block,(rep,rotation) in enumerate(zip(repeats,rotations)):
        order=base[rotation:]+base[:rotation]
        for position,arm in enumerate(order):
            cid=f'midpoint-c12-staggered-{arm.lower()}-r{rep}';out=O+'/dsn_midpoint_v1/'+cid
            retain='yes' if arm.startswith('R1') else 'no';consumer='two_lane' if arm.endswith('S1') else 'checked_snapshot'
            argv=[B+'/envs/revbatch-cu128/bin/python','-B',N+'/source_v3/retirement_service.py','--out',out,
                '--source-manifest',N+'/SOURCE_v3.json','--manifest',MANIFEST,'--model',B+'/models/Qwen3-ASR-1.7B',
                '--adapter','qwen','--policy','row_complete','--method','dgft_original','--rho','1','--sessions','12',
                '--arrival','staggered','--repeat',str(rep),'--retain',retain,'--confirmation-consumer',consumer,
                '--watchdog-seconds','2.0','--service-timeout','240.0','--wall-timeout','420.0']
            cells.append(dict(cell_id=cid,phase='midpoint_continuity',cohort='c12-staggered',arm=arm,adapter='qwen',rho=1,
                arrival='staggered',repeat=rep,sessions=12,retain=retain,confirmation_consumer=consumer,
                policy='row_complete',method='dgft_original',fixture=None,model=B+'/models/Qwen3-ASR-1.7B',
                manifest=MANIFEST,manifest_sha256=h(manifest)['sha256'],output=out,argv=argv,
                run_order_index=len(cells),block_index=block,within_block_position=position,
                paired_block=f'midpoint-c12-staggered-r{rep}',scope='targeted reused-development midpoint, not independent confirmation'))
    counts={arm:{str(p):sum(c['arm']==arm and c['within_block_position']==p for c in cells) for p in range(4)} for arm in arms}
    assert len(cells)==12 and len({c['output'] for c in cells})==12
    assert all(max(v.values())-min(v.values())<=1 for v in counts.values())
    plan=dict(experiment_id='REVTRACE-DSN-MIDPOINT-CONTINUITY-20261029-V1',status='FROZEN_PREPARATION_ONLY_GPU_NOT_LAUNCHED',
        code_commit=COMMIT,source_manifest_sha256=SOURCE_SHA,execution_source=N+'/source_v3',source_manifest=N+'/SOURCE_v3.json',
        original_manifest=MANIFEST,original_manifest_sha256=h(manifest)['sha256'],
        points=[dict(point='c12-staggered',sessions=12,arrival='staggered',question='timely valid progress continuity at one fixed midpoint')],
        cohorts=[dict(cohort='c12-staggered',source_ids=[x['source_id'] for x in rows],speakers=[x['speaker'] for x in rows],
            selected_audio_seconds=selection['selected_audio_seconds'],expected_offered_frontiers=selection['expected_offered_frontiers'])],
        cells=cells,randomization=dict(seed=SEED,repeat_block_order=repeats,base_arm_order=base,rotations=rotations,
            method='randomized three-block order and three distinct Latin arm rotations; approximate positions, not full four-position counterbalance',
            arm_position_counts=counts,all_fresh_processes=True),
        shared_contract=dict(old_plan['shared_contract'],arrival_phase_seconds='sid*0.25',denominator='all offered including EOS/misses; unchanged'),
        strong_witness=dict(joint_and_compute_only_each_P99_pass='3/3 original whole-run D2/C8',
            compute_only_full_non_EOS_timely_compatible_repetitions='>=2/3 with >=1 original full2s nonterminal dual-credited frontier withdrawn',
            joint_compatible_timely_loss_windows='zero across all3',original_first_credit_joint_win_required=False,
            independent_complete_selected_history_equality_required=True),
        primary=dict(endpoints=old_plan['primary']['endpoints'],
            secondary='already frozen timely delivered progress continuity; full2s non-EOS strong-witness flag; D2 read deficits and single-root area separate',
            comparators='Joint versus R-only primary; all four arms retained; first-credit need not favor Joint'),
        stop=dict(after='all twelve cells plus complete CPU analysis',positive_result_required=False,
            forbidden=['10/11 session follow-up','phase/deadline/source retuning','extra repeats until winning','new model/source/cancellation/mechanism'],
            interpretation='Low opportunity or unmet strong condition is a complete STOP, not launch failure'),
        execution_order=['R*K24 execution and CPU analysis','native_v6 prescribed 2 witnesses, gated12 formal, and CPU analysis','this midpoint12'],
        required_root_allocation='ALLOCATION_v1.json must bind actual completion/decision records for BOTH preceding scopes before launch',
        evidence_paths=dict(raw_results=O+'/dsn_midpoint_v1',controller=O+'/dsn_midpoint_controller_v1',aggregate=O+'/dsn_midpoint_analysis_v1',remote_project=P),
        source_selection='original16 first12; first8 nested; no output-based replacement',evidence_tier='development workload exploration; not independent source confirmation/capacity curve',
        new_model_calls_by_preparation=0)
    put(F/'PLAN_v1.json',plan)
    upstream=R/'experiments/dsn_service_stability_20261028/analysis_source_v2';copies=[]
    for name in ['run_analysis.py','aggregate_service_v5.py','canonical_usefulness_v1.py','critical_path.py','interaction_opportunities_v1.py']:
        b=(upstream/name).read_bytes();(A/name).write_bytes(b);copies.append(dict(origin=str(upstream/name),destination=name,**h(A/name)))
    src=R/'experiments/dsn_manuscript_update_20261028/timely_continuity_v1/source_v1'
    for old,new in [('continuity.py','continuity_secondary.py'),('test_continuity.py','test_continuity.py')]:
        b=(src/old).read_bytes()
        if old.startswith('test_'):b=b.replace(b'from continuity import analyze_cell',b'from continuity_secondary import analyze_cell')
        (A/new).write_bytes(b);copies.append(dict(origin=str(src/old),destination=new,**h(A/new),compatibility_repair='test import namespace only' if old.startswith('test_') else None))
    put(A/'UPSTREAM.json',dict(upstream_analysis_commit='fde6272b494db43a66eebea7444d7c9d1037e687',
        timely_continuity_commit='f8cbdb626cf8996643a3cc870594c945a21e744c',copies=copies,
        changes='Five core recounters byte-identical; timely analyze_cell byte-identical; new wrapper decision only, no runtime changes'))
    put(F/'PLAN_RECEIPT_v1.json',dict(plan_file='PLAN_v1.json',**h(F/'PLAN_v1.json'),builder_sha256=h(Path(__file__))['sha256'],
        selected_audio_seconds=selection['selected_audio_seconds'],expected_frontiers=selection['expected_offered_frontiers'],
        planned_cells=12,new_GPU_calls=0))
    print(json.dumps(dict(status='PREPARED_ONLY',plan=h(F/'PLAN_v1.json'),audio_seconds=selection['selected_audio_seconds'],frontiers=selection['expected_offered_frontiers'])))

if __name__=='__main__':main()
