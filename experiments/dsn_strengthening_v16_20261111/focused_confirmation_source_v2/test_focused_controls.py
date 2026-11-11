import copy,json,pathlib,tempfile,unittest,multiprocessing as mp
from confirmation_common import MAIN_ARMS,abba_blocks,validate_matrix,GateError
from focused_common import validate_focus_selection
class MatrixControls(unittest.TestCase):
    def test_two_arm_reversal_and_GPU_roles_for_two_or_four_voices(self):
        for n in (2,4):
            sources=[dict(source_id='s'+str(i),speaker_id='p'+str(i)) for i in range(n)];rows=[]
            for block in abba_blocks(sources,False)[0]:
                for arm in block['strategies']:rows.append(dict(cell_id=str(len(rows)),source_id=block['source']['source_id'],strategy=arm,repeat=block['repeat'],primary_gpu=block['primary_gpu'],position=len(rows)))
            validate_matrix(rows,sources,False);self.assertEqual(len(rows),4*n);self.assertEqual(set(r['strategy'] for r in rows),{'fullcall','ready_only'})
            with self.assertRaises(GateError):validate_matrix(rows[:-1],sources,False)
    def test_undeclared_or_pilot_slice_cannot_be_confirmation(self):
        for ix in ([0,1],[1,2],[2,3,4]):
            with self.assertRaises(GateError):validate_focus_selection(dict(selection_use='focused_full_ready_confirmation',comparison_bank_indices=ix),[])
class PipeControls(unittest.TestCase):
    def test_real_owner_pipe_retains_inflight_only_in_full_and_same_selected_G(self):
        from test_resilience_owner_integration import Harness
        from resilience_storage import scan
        class H(Harness):
            def __init__(self,p,arm):super().__init__(p,arm=arm,future_first=True,parent_first=True);self.rx,self.tx=mp.get_context('spawn').Pipe(duplex=False)
            def send(self,value):self.tx.send(value);super().send(self.rx.recv())
            def close(self):super().close();self.rx.close();self.tx.close()
        outputs={}
        for arm in MAIN_ARMS:
            with tempfile.TemporaryDirectory() as folder:
                p=pathlib.Path(folder);h=H(p,arm)
                try:
                    h.run();facts=[o['body'] for o,_ in scan(p/'facts.wal') if o['kind']=='canonical'];outputs[arm]=[f['next_state'] for f in facts]
                    self.assertEqual(len(facts),2);self.assertEqual(len(h.commands),2 if arm=='fullcall' else 3);self.assertEqual(h.consumer.snapshot('s')['certified_frontier'],16000)
                finally:h.close()
        self.assertEqual(outputs['fullcall'],outputs['ready_only'])
if __name__=='__main__':unittest.main()
