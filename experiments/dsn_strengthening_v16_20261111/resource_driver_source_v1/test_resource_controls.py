"""CPU-only grouped scope and actual Owner/Pipe/Consumer/WAL controls."""
import copy,json,pathlib,tempfile,types,unittest,multiprocessing as mp
from unittest.mock import patch
from resource_common import groups_from_sources,blocks,validate_matrix,validate_cell
from confirmation_common import GateError

def sources():return [dict(source_id='s'+str(i),speaker_id='p'+str(i),frames=16000) for i in range(4)]
def cells(groups):
    rows=[]
    for b in blocks(groups)[0]:
        for arm in b['strategies']:rows.append(dict(cell_id=str(len(rows)),group_id=b['group']['group_id'],source_count=b['group']['source_count'],source_ids=b['group']['source_ids'],strategy=arm,repeat=b['repeat'],primary_gpu=b['primary_gpu'],position=len(rows)))
    return rows
class MatrixControls(unittest.TestCase):
    def test_nested_two_four_complete_eight_reversed_cells(self):
        gs=groups_from_sources(sources());cs=cells(gs);validate_matrix(cs,gs)
        self.assertEqual(len(cs),8);self.assertEqual(gs[0]['source_ids'],gs[1]['source_ids'][:2])
    def test_omitted_waiting_chain_or_missing_policy_rejected(self):
        gs=groups_from_sources(sources());cs=cells(gs);cs[0]['source_ids']=cs[0]['source_ids'][:1]
        with self.assertRaises(GateError):validate_matrix(cs,gs)
    def test_repeat_order_or_GPU_role_cannot_be_reused(self):
        gs=groups_from_sources(sources());cs=cells(gs);cs[-1]['primary_gpu']=0
        with self.assertRaises(GateError):validate_matrix(cs,gs)

class PipeIntegrationControls(unittest.TestCase):
    def test_actual_two_source_owner_pipe_and_all_source_audit(self):
        from test_round_robin_dispatch import MultiHarness
        import test_round_robin_dispatch as rr_fixture
        from test_resilience_storage import body,cut
        from feedback_contract import FeedbackCut
        from resilience_storage import scan
        from group_audit import audit_group
        import audit_results,endpoints,external_power
        def tagged_cut(frontier,text=''):
            value=cut(frontier,text).state;value['contract']['stage_execution']={'source_commit':'f'*40};return FeedbackCut(value)
        class PipeHarness(MultiHarness):
            def __init__(self,p):
                super().__init__(p,arm='conservative',n=2);self.root=tagged_cut(0);self.initials={s:self.root.state for s in self.sids};self.rx,self.tx=mp.get_context('spawn').Pipe(duplex=False);self.pipe_rows=0
            def send(self,message):
                self.tx.send(message);wire=self.rx.recv();self.pipe_rows+=1;super().send(wire)
            def close(self):super().close();self.rx.close();self.tx.close()
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);h=PipeHarness(root)
            try:
                with patch.object(rr_fixture,'storage_cut',tagged_cut):h.run()
                self.assertGreater(h.pipe_rows,0);cfg=copy.deepcopy(h.config);cfg['settings']['source_commit']='f'*40
                (root/'CONFIG.json').write_text(json.dumps(cfg));(root/'ORIGIN.json').write_text(json.dumps({'origin_perf':h.origin.value}));(root/'ENERGY.json').write_text('{}');(root/'SUMMARY.json').write_text('{}')
                reference=[]
                for sid in h.sids:
                    parent=tagged_cut(0)
                    for end in (8000,16000):
                        nxt=tagged_cut(end,sid+'-'+str(end));record=body(parent,nxt)['record'];reference.append(dict(source_id=sid,end=end,original_full_start_cut=parent.state,original_full_cut=nxt.state,original_full_result=dict(token_ids=record['token_ids'],selected_correction=record['selected_correction'])));parent=nxt
                rows=[json.loads(r) for r in (root/'consumer.jsonl').read_text().splitlines()];last=max(r['observed'] for r in rows)
                observer=types.SimpleNamespace(path=root/'synthetic_power.jsonl',drain={'confirmed_perf':last+.01})
                # Synthetic power is intentionally injected, never GPU evidence.
                with patch.object(audit_results,'energy',return_value={'total_joules':0.,'scope':'CPU synthetic fixture only'}):
                    r=audit_group(dict(cell_id='CPU_PIPE_ONLY',group_id='sync2',strategy='conservative',repeat=0,out=str(root)),cfg,reference,observer,audit_results=audit_results,endpoints=endpoints,scan=scan)
                    self.assertEqual(set(r['per_source_primary']),{'a','b'});self.assertEqual(r['source_count'],2)
                    self.assertEqual(r['job_accounting']['dispatches'],4);self.assertEqual(r['conditional_dispatches'],0)
                    broken=reference[:-1]
                    with self.assertRaises(Exception):audit_group(dict(cell_id='CPU_BAD_REFERENCE',group_id='sync2',strategy='conservative',repeat=0,out=str(root)),cfg,broken,observer,audit_results=audit_results,endpoints=endpoints,scan=scan)
            finally:h.close()
if __name__=='__main__':unittest.main()
