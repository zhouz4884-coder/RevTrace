"""Bind the predeclared pilot2 to measured full4 references, no neural calls."""
import argparse,pathlib
from confirmation_common import (RUNTIME,REFERENCE_SUCCESS,BOUND_REFERENCE_SUCCESS,read,sha,put,canonical,
    need,selected_sources,reference_binding,verify_source,prespecified_reference_subset)

def derive_subset(parent_path,parent_selection_path,subset_selection_path,out,generator_commit):
    parent_selection=read(parent_selection_path);subset_selection=read(subset_selection_path)
    parent_sources,sources=prespecified_reference_subset(parent_selection,subset_selection)
    parent=reference_binding(parent_path,parent_selection_path,parent_sources,generator_commit)
    need(parent['status']==REFERENCE_SUCCESS,'parent must be directly measured full reference')
    out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=False);wanted={s['source_id'] for s in sources}
    rows=[r for r in read(parent['reference_details']['path']) if r['source_id'] in wanted]
    genesis0=read(parent['genesis']['path']);genesis={s['source_id']:genesis0[s['source_id']] for s in sources}
    put(out/'REFERENCE_DETAILS.json',rows);put(out/'GENESIS.json',genesis)
    pmeta=dict(path=str(parent_path),sha256=sha(parent_path));smeta=dict(path=str(parent_selection_path),sha256=sha(parent_selection_path))
    steps=sum((s['frames']+7999)//8000 for s in sources)
    gate=dict(status=BOUND_REFERENCE_SUCCESS,actual_NN_source_commit=RUNTIME,generator_source_commit=generator_commit,
        all_original_full_state_C_IDs_equal=True,expected_original_steps=steps,expected_sources=2,completed_sources=2,
        new_neural_verification=False,new_model_calls=0,measured_parent_reference=pmeta,
        scope='logical exact source-row subset of newly measured full4 parent; not additional neural verification')
    put(out/'GATE.json',gate)
    ref=dict(status=BOUND_REFERENCE_SUCCESS,actual_NN_source_commit=RUNTIME,generator_source_commit=generator_commit,
        selection_receipt=dict(path=str(subset_selection_path),sha256=sha(subset_selection_path)),sources=sources,
        source_ids=[s['source_id'] for s in sources],speaker_ids=[s['speaker_id'] for s in sources],
        reference_details=dict(path=str(out/'REFERENCE_DETAILS.json'),sha256=sha(out/'REFERENCE_DETAILS.json'),bytes=(out/'REFERENCE_DETAILS.json').stat().st_size,expected_steps=steps),
        reference_gate=dict(path=str(out/'GATE.json'),sha256=sha(out/'GATE.json')),
        genesis=dict(path=str(out/'GENESIS.json'),sha256=sha(out/'GENESIS.json')),
        reference_only=True,actual_serving_runs=0,original_continuous_no_between_step_restore=True,restored_repeats_per_edge=2,
        reference_origin='prespecified_exact_source_subset',measured_parent_reference=pmeta,measured_parent_selection=smeta,
        reference_cost_source=dict(parent_reference_receipt=pmeta,rule='all paid full4 reference cost/call ledger remains in unchanged measured parent; child new calls0 does not mean total reference cost0'),
        new_model_calls=0,new_neural_verification=False)
    put(out/'REFERENCE_RECEIPT.json',ref)
    reference_binding(out/'REFERENCE_RECEIPT.json',subset_selection_path,sources,generator_commit)
    return ref

def main():
    p=argparse.ArgumentParser()
    for n in ('manifest','parent-receipt','parent-selection','subset-selection','out'):p.add_argument('--'+n,required=True)
    a=p.parse_args();own=verify_source(pathlib.Path(__file__).parent,a.manifest)
    derive_subset(a.parent_receipt,a.parent_selection,a.subset_selection,a.out,own['source_commit'])
if __name__=='__main__':main()
