"""Controller/schema controls only; never starts checker, model or GPU work."""
from pathlib import Path
import tempfile
import unittest
from c4_common import (CHECKER,NN4F,SOURCES,GateError,nn16,prerequisites,input_roles,
                       checker_config,checker_command,disk)


def synthetic_plan():
    cells=[dict(cell_id=f'{source}_{arm}_{repeat}_{enabled}',source_id=source,arm=arm,
                repeat=repeat,observation=enabled,out=f'/original/{source}_{arm}_{repeat}_{enabled}')
           for source in SOURCES for arm in ('conservative','fullcall')
           for repeat in range(2) for enabled in (False,True)]
    return dict(actual_nn_source_commit=NN4F,fixed_sources=list(SOURCES),expected_NN_trials=16,cells=cells)


def synthetic_terminal(plan):
    rows=[dict(cell_id=cell['cell_id'],raw_result_location=cell['out'],phase='nn',observation=cell['observation'],
               semantic=dict(status='PASS_COMPLETE_SELECTED_TRACE_REFERENCE',actual_NN_source_commit=NN4F))
          for cell in plan['cells']]
    return (dict(status='COMPLETE_FROZEN_COST_NN_CAMPAIGN',completed_cells=16,NN_cells=16,cpu_cells=0,cells=rows),
            dict(status='COMPLETE_FROZEN_COST_NN_CAMPAIGN',completed_cells=16,root_actual_trace_recheck_pending=True))


class Controls(unittest.TestCase):
    def test_complete_fixed_matrix_and_terminal_records_accepted(self):
        plan=synthetic_plan()
        summary,gate=synthetic_terminal(plan)
        self.assertEqual(len(prerequisites(plan,summary,gate)),16)

    def test_missing_or_duplicate_cell_is_not_a_completed_recheck(self):
        plan=synthetic_plan()
        plan['cells'].pop()
        with self.assertRaises(GateError):nn16(plan)
        plan=synthetic_plan()
        plan['cells'][-1]=dict(plan['cells'][0])
        with self.assertRaises(GateError):nn16(plan)

    def test_observation_bool_cannot_be_replaced_with_integer(self):
        plan=synthetic_plan()
        plan['cells'][0]['observation']=0
        with self.assertRaises(GateError):nn16(plan)

    def test_all_actual_NN_terminal_semantics_required_before_C4(self):
        plan=synthetic_plan()
        summary,gate=synthetic_terminal(plan)
        summary['cells'][-1]['semantic']['status']='INCOMPLETE'
        with self.assertRaises(GateError):prerequisites(plan,summary,gate)

    def test_actual_raw_cannot_be_substituted_by_old_reference_trace(self):
        plan=synthetic_plan()
        summary,gate=synthetic_terminal(plan)
        summary['cells'][0]['raw_result_location']='/old_diagnostic_reference'
        with self.assertRaises(GateError):prerequisites(plan,summary,gate)

    def test_every_owner_attempt_and_required_log_is_mapped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ['CONFIG.json','facts.wal','publications.jsonl','consumer.jsonl','ORIGIN.json','ingress.jsonl']:
                (root/name).write_bytes(b'{}')
            for epoch in (10,0,2):
                owner=root/f'owner_e{epoch}'
                owner.mkdir()
                for name in ['dispatch.jsonl','worker_results.jsonl','owner_events.jsonl','policy_audit.jsonl']:
                    (owner/name).write_bytes(b'')
            roles,owners,files=input_roles(root)
            self.assertEqual([path.name for path in owners],['owner_e0','owner_e2','owner_e10'])
            self.assertEqual(len(files),18)
            self.assertEqual(roles['fact_journal'],root/'facts.wal')

    def test_missing_complete_worker_result_log_does_not_become_empty_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ['CONFIG.json','facts.wal','publications.jsonl','consumer.jsonl','ORIGIN.json','ingress.jsonl']:
                (root/name).write_bytes(b'{}')
            owner=root/'owner_e0'
            owner.mkdir()
            for name in ['dispatch.jsonl','owner_events.jsonl','policy_audit.jsonl']:
                (owner/name).write_bytes(b'')
            with self.assertRaises(GateError):input_roles(root)

    def test_original_checker_CLI_cannot_launch_observer_or_neural_entry(self):
        command=checker_command('/original_c4','/frozen_config','/checker_manifest','/new_output')
        self.assertIn('/original_c4/run_trace.py',command)
        self.assertIn('-B',command)
        self.assertNotIn('observed_trial.py',' '.join(command))
        self.assertNotIn('resilience_trial.py',' '.join(command))

    def test_controller_checker_and_NN_roles_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            cfg=checker_config(dict(cell_id='scripted',out=str(root)),
                dict(manifest_sha256='a'*64),{},dict(runtime_config=root/'CONFIG.json'),[],root/'out')
            self.assertEqual(cfg['checker_source_commit'],CHECKER)
            self.assertEqual(cfg['actual_runtime_source_commit'],NN4F)
            self.assertNotEqual(cfg['checker_source_commit'],cfg['actual_runtime_source_commit'])
            self.assertFalse(cfg['allow_incomplete_uncommitted_tail'])

    def test_output_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'intended'
            root.mkdir()
            self.assertEqual(disk(root/'new',root),root/'new')
            with self.assertRaises(GateError):disk(root/'..'/'outside',root)


if __name__=='__main__':
    unittest.main(verbosity=2)
