"""Freeze metadata-only acquisition config; does not read WAV or transcripts."""
from __future__ import annotations
import argparse,pathlib
from acquisition_common import ARCHIVE_URL,need,read,sha,put,validate_metadata
def main():
    p=argparse.ArgumentParser()
    for n in ('selection-dir','rule','reference-metadata','out','dataset-root','raw-out'):p.add_argument('--'+n,required=True)
    p.add_argument('--expected-sources',type=int,required=True);p.add_argument('--staged-ranges')
    a=p.parse_args();root=pathlib.Path(a.selection_dir);selection=read(root/'METADATA_SELECTION.json');rule=read(a.rule)
    validate_metadata(selection,rule,a.expected_sources)
    need(selection['selection_recipe_sha256']==sha(a.rule),'selection recipe bytes differ')
    need(sha(root/'HISTORICAL_EXCLUSION_INPUTS.json')==selection['exclusion_ledger_sha256'],'historical exclusion ledger changed')
    # Reference bytes are not opened by this metadata-only builder. The already
    # established official metadata hash is frozen here and checked after lock.
    cfg=dict(experiment_id='REVTRACE_STRICT_NEW_TEST_AUDIO_ACQUISITION_20261102_V1',
        metadata_selection=str(root/'METADATA_SELECTION.json'),metadata_selection_sha256=sha(root/'METADATA_SELECTION.json'),metadata_gate=str(root/'GATE.json'),metadata_gate_sha256=sha(root/'GATE.json'),
        rule=a.rule,rule_sha256=sha(a.rule),historical_exclusion_inputs=str(root/'HISTORICAL_EXCLUSION_INPUTS.json'),historical_exclusion_sha256=selection['exclusion_ledger_sha256'],
        archive_public_url=ARCHIVE_URL,expected_sources=a.expected_sources,reference_metadata=a.reference_metadata,reference_metadata_sha256='e040232c00a431bc04cf7696dd1c9cfb138933800df50f848c1ad5485c1e89c6',
        network_attempts_per_same_member=3,staged_ranges=read(a.staged_ranges) if a.staged_ranges else {},
        dataset_root=a.dataset_root,raw_result_location=a.raw_out,
        technical_failure_policy='CRC-correct header/duration failure: next locked same-speaker candidate; transport/CRC retry same member only; exhaustion/hash collision STOP, never silently reduceN')
    put(a.out,cfg)
if __name__=='__main__':main()

