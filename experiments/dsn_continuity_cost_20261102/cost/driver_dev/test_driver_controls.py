"""Small driver contract controls; no models, CUDA, launch or raw benchmark."""
from __future__ import annotations
import pathlib,tempfile,types,unittest
from driver_common import matrix_shape,SOURCES,OBSERVER,NN4F,GateError,disk
from run_campaign import command_for

def plan():
    cpu=[dict(cell_id=f'cpu_{s}_{a}_{r}',source_id=s,arm=a,repeat=r) for s in SOURCES for a in ('conservative','fullcall') for r in range(3)]
    nn=[dict(cell_id=f'nn_{s}_{a}_{r}_{on}',source_id=s,arm=a,repeat=r,primary_gpu=r,observation=on) for s in SOURCES for a in ('conservative','fullcall') for r in range(2) for on in (False,True)]
    return dict(fixed_sources=list(SOURCES),observer_source_commit=OBSERVER,actual_nn_source_commit=NN4F,cpu_cases=cpu,cells=nn)

class Controls(unittest.TestCase):
    def test_complete_scope_accepted(self):matrix_shape(plan())
    def test_missing_cell_cannot_be_success(self):
        p=plan();p['cpu_cases'].pop()
        with self.assertRaises(GateError):matrix_shape(p)
    def test_duplicate_does_not_replace_frozen_source(self):
        p=plan();p['cells'][-1]=dict(p['cells'][0])
        with self.assertRaises(GateError):matrix_shape(p)
    def test_instrumentation_boolean_is_not_implicit_integer(self):
        p=plan();p['cells'][0]['observation']=0
        with self.assertRaises(GateError):matrix_shape(p)
    def test_disk_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=pathlib.Path(tmp)/'intended';b.mkdir()
            self.assertEqual(disk(b/'new',b),b/'new')
            with self.assertRaises(GateError):disk(b/'..'/'outside',b)
    def test_command_separates_observer_and_original_NN(self):
        a=types.SimpleNamespace(observer_source='/observer',observer_manifest='/observer_manifest')
        p=dict(original_dependency=dict(source_root='/actual_4f',source_manifest='/actual_4f_manifest'))
        c=dict(input_raw='/old_real_trace',output='/new_CPU',config='/new_config',out='/new_NN')
        cpu=command_for('cpu',c,a,p);nn=command_for('nn',c,a,p)
        self.assertIn('/observer/trace_cost.py',cpu);self.assertIn('/observer/observed_trial.py',nn)
        self.assertEqual(nn[nn.index('--base-source')+1],'/actual_4f')
        self.assertEqual(nn[nn.index('--observer-manifest')+1],'/observer_manifest')
        self.assertNotIn('shell=True',str(nn))

if __name__=='__main__':unittest.main()

