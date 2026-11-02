"""Metadata/controller controls only. No original checker/NN/GPU execution."""
from pathlib import Path
import tempfile,unittest
from c4_common import (CHECKER,NN4F,SUPPORT,GateError,confirmation32,prerequisites,
                       input_roles,checker_config,checker_command,disk)


def synthetic_plan():
    sources=[dict(source_id=f'scripted-source-{i}',speaker_id=f'scripted-speaker-{i}',frames=128000+i) for i in range(8)]
    cells=[]
    for repeat in (0,1):
        for source in sources:
            order=['conservative','fullcall'] if repeat==0 else ['fullcall','conservative']
            for strategy in order:
                cid=f"{source['source_id']}-{strategy}-{repeat}"
                cells.append(dict(cell_id=cid,source_id=source['source_id'],speaker_id=source['speaker_id'],
                    strategy=strategy,repeat=repeat,primary_gpu=repeat,position=len(cells),out='/original/'+cid))
    return dict(actual_NN=dict(source_commit=NN4F),production_support=dict(source_commit=SUPPORT),
                sources=sources,expected_source_count=8,expected_trials=32,cells=cells)


def synthetic_terminal(plan):
    rows=[dict(cell_id=cell['cell_id'],source_id=cell['source_id'],strategy=cell['strategy'],repeat=cell['repeat'],
               raw_result_location=cell['out'],primary=dict(complete_coverage_and_original_quantile_pass=False),
               semantic=dict(status='PASS_COMPLETE_SELECTED_TRACE_REFERENCE',actual_NN_source_commit=NN4F))
          for cell in plan['cells']]
    return (dict(status='COMPLETE_FROZEN_NEW_TEST_CONFIRMATION_TASK_AND_ENDPOINTS',planned_trials=32,completed_trials=32,
                 independent_speakers=8,actual_NN_source_commit=NN4F,cells=rows),
            dict(status='COMPLETE_FROZEN_NEW_TEST_CONFIRMATION_TASK_AND_ENDPOINTS',completed_trials=32,Root_actual_trace_audit_pending=True))


class Controls(unittest.TestCase):
    def test_complete_fixed_32_matrix_and_all_terminal_rows(self):
        plan=synthetic_plan();summary,gate=synthetic_terminal(plan)
        self.assertEqual(len(prerequisites(plan,summary,gate)),32)

    def test_SLO_failure_does_not_remove_cell_from_structural_check(self):
        plan=synthetic_plan();summary,gate=synthetic_terminal(plan)
        self.assertTrue(all(not row['primary']['complete_coverage_and_original_quantile_pass'] for row in summary['cells']))
        self.assertEqual(len(prerequisites(plan,summary,gate)),32)

    def test_missing_or_duplicate_cell_cannot_be_complete(self):
        plan=synthetic_plan();plan['cells'].pop()
        with self.assertRaises(GateError):confirmation32(plan)
        plan=synthetic_plan();plan['cells'][-1]=dict(plan['cells'][0])
        with self.assertRaises(GateError):confirmation32(plan)

    def test_eight_speakers_are_not_32_pseudoreplicated_sources(self):
        plan=synthetic_plan();plan['sources'][-1]['speaker_id']=plan['sources'][0]['speaker_id']
        with self.assertRaises(GateError):confirmation32(plan)

    def test_per_speaker_reverse_and_GPU_roles_are_frozen(self):
        plan=synthetic_plan();plan['cells'][-1]['primary_gpu']=0
        with self.assertRaises(GateError):confirmation32(plan)
        plan=synthetic_plan();plan['cells'][-1]['position'],plan['cells'][-2]['position']=plan['cells'][-2]['position'],plan['cells'][-1]['position']
        with self.assertRaises(GateError):confirmation32(plan)

    def test_old_reference_path_cannot_substitute_actual_service_trace(self):
        plan=synthetic_plan();summary,gate=synthetic_terminal(plan)
        summary['cells'][0]['raw_result_location']='/reference-only'
        with self.assertRaises(GateError):prerequisites(plan,summary,gate)

    def test_incomplete_actual_semantic_gate_blocks_closure(self):
        plan=synthetic_plan();summary,gate=synthetic_terminal(plan)
        summary['cells'][-1]['semantic']['status']='INCOMPLETE'
        with self.assertRaises(GateError):prerequisites(plan,summary,gate)

    def test_every_normal_or_recovery_owner_directory_is_mapped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ['CONFIG.json','facts.wal','publications.jsonl','consumer.jsonl','ORIGIN.json','ingress.jsonl']:(root/name).write_bytes(b'{}')
            for epoch in (10,0,2):
                owner=root/f'owner_e{epoch}';owner.mkdir()
                for name in ['dispatch.jsonl','worker_results.jsonl','owner_events.jsonl','policy_audit.jsonl']:(owner/name).write_bytes(b'')
            roles,owners,files=input_roles(root)
            self.assertEqual([path.name for path in owners],['owner_e0','owner_e2','owner_e10'])
            self.assertEqual(len(files),18)

    def test_missing_worker_result_is_not_an_empty_valid_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ['CONFIG.json','facts.wal','publications.jsonl','consumer.jsonl','ORIGIN.json','ingress.jsonl']:(root/name).write_bytes(b'{}')
            owner=root/'owner_e0';owner.mkdir()
            for name in ['dispatch.jsonl','owner_events.jsonl','policy_audit.jsonl']:(owner/name).write_bytes(b'')
            with self.assertRaises(GateError):input_roles(root)

    def test_original_C4_CLI_never_launches_neural_entry(self):
        command=checker_command('/unchanged_c4','/frozen_config','/checker_manifest','/new_output')
        self.assertIn('/unchanged_c4/run_trace.py',command)
        self.assertIn('-B',command)
        self.assertNotIn('resilience_trial.py',' '.join(command))

    def test_checker_and_actual_NN_source_roles_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg=checker_config(dict(cell_id='scripted',out=tmp),dict(manifest_sha256='a'*64),{},
                               dict(runtime_config=Path(tmp)/'CONFIG.json'),[],Path(tmp)/'out')
            self.assertEqual(cfg['checker_source_commit'],CHECKER)
            self.assertEqual(cfg['actual_runtime_source_commit'],NN4F)
            self.assertNotEqual(cfg['checker_source_commit'],cfg['actual_runtime_source_commit'])

    def test_result_path_cannot_escape_designated_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)/'intended';base.mkdir()
            self.assertEqual(disk(base/'new',base),base/'new')
            with self.assertRaises(GateError):disk(base/'..'/'outside',base)


if __name__=='__main__':unittest.main(verbosity=2)
