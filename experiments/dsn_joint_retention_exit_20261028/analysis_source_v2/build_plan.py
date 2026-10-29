"""Materialize a metadata-frozen 2x2 R x K campaign without model calls."""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, random

B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_physical_retirement_20261028'
O=B+'/results/revtrace/physical_retirement_20261028'
COMMIT='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf'
SOURCE_SHA='19547df369c2899d4cb0eec49d137eff7f160802668072033ae9197565771625'
MANIFEST=B+'/results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json'
MANIFEST_SHA='8904fa5b16cb5d2c1f75d101079c6b7f640c2817b873cb92e816eecb694ea1bc'
FIXTURE=P+'/F2_INPUT_FIXTURE_v1.json'
FIXTURE_SHA='b86566894c0db85c85e9a4bd4ffefb33c5db14067d42aeb0e75cebd42ba12892'
SEED=2026102802

def build():
    rng=random.Random(SEED)
    blocks=[(arrival,repeat) for arrival in ['sync','staggered'] for repeat in range(3)]
    rng.shuffle(blocks)
    cells=[]
    for arrival,repeat in blocks:
        arms=[(r,k) for r in range(2) for k in range(2)]
        rng.shuffle(arms)
        for r,k in arms:
            cid=f'joint-{arrival}-r{repeat}-R{r}K{k}'
            output=O+'/dsn_joint_v1/'+cid
            policy='covered' if k else 'no_cancel'
            retain='yes' if r else 'no'
            argv=[B+'/envs/revbatch-cu128/bin/python','-B','-u',P+'/source_v3/retirement_service.py',
                  '--out',output,'--source-manifest',P+'/SOURCE_v3.json','--manifest',MANIFEST,
                  '--model',B+'/models/Qwen3-ASR-1.7B','--adapter','qwen','--policy',policy,
                  '--method','dgft_original','--rho','1','--sessions','16','--arrival',arrival,
                  '--repeat',str(repeat),'--fixture',FIXTURE,'--retain',retain,
                  '--confirmation-consumer','two_lane','--service-timeout','240','--wall-timeout','420']
            cells.append(dict(cell_id=cid,phase='retention_exit_joint',cohort='OLD_DEVELOPMENT_16',
                arm=f'R{r}K{k}',R=r,K=k,adapter='qwen',arrival=arrival,repeat=repeat,rho=1,sessions=16,
                policy=policy,retain=retain,method='dgft_original',confirmation_consumer='two_lane',
                manifest=MANIFEST,manifest_sha256=MANIFEST_SHA,fixture=FIXTURE,fixture_sha256=FIXTURE_SHA,
                output=output,argv=argv,paired_block=f'joint|{arrival}|r{repeat}',run_order_index=len(cells)))
    return dict(experiment_id='REVTRACE-DSN-RXK-JOINT-20261028-v1',
        status='FROZEN_BEFORE_ANY_NEW_GPU_RESULT',code_commit=COMMIT,source_manifest_sha256=SOURCE_SHA,
        execution_source=P+'/source_v3',source_manifest=P+'/SOURCE_v3.json',randomization_seed=SEED,
        selection='all original metadata-first development sources; no new output-dependent selection',
        evidence_tier='actual controlled F2 service; independent temporal repeats, not new source cohorts',
        primary_question='Does physical coverage exit translate into useful progress through compute retention?',
        inference='A zero or separable interaction is a complete scientific outcome; no runtime retuning on outcomes.',
        primary_interaction='Y_R1K1 - Y_R1K0 - Y_R0K1 + Y_R0K0',
        original_display_seconds=2.,original_commit_seconds=8.,cells=cells)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();plan=build()
    with args.out.open('x',encoding='utf8') as stream:json.dump(plan,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(plan=str(args.out),sha256=hashlib.sha256(args.out.read_bytes()).hexdigest(),cells=len(plan['cells']))))

if __name__=='__main__':main()
