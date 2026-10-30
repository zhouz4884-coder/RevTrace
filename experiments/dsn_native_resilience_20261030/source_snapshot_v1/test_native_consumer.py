import pathlib,tempfile,unittest
from native_service import Consumer
from test_feedback_contract import state

def chain(*cuts):return [dict(job_id=str(i),start=a.state,end=b.state) for i,(a,b) in enumerate(zip(cuts,cuts[1:]))]
def scratch():
    root=pathlib.Path(__file__).resolve().parent.parent/'cpu_scratch';root.mkdir(exist_ok=True)
    return tempfile.TemporaryDirectory(dir=root)
class ActualQueueConsumer(unittest.TestCase):
    def test_actual_queue_preserves_compatible_ahead_view(self):
        a,b,c=state(0,''),state(8,'你'),state(16,'你好')
        with scratch() as d:
            v=Consumer({'s':a},pathlib.Path(d)/'c.jsonl',0.)
            v.publish(dict(kind='private',source_id='s',canonical_sha=a.sha256,steps=chain(a,b,c)))
            v.publish(dict(kind='canonical',source_id='s',state=b.state,processed_frontier=8));v.close()
            self.assertEqual(v.rows[-1]['visible_frontier'],16);self.assertEqual(v.rows[-1]['certified_frontier'],8)
    def test_actual_queue_withdraws_same_text_different_native_state(self):
        a,b,c=state(0,''),state(8,'你'),state(16,'你好');new=state(8,'你',last_attend_frame=999)
        with scratch() as d:
            v=Consumer({'s':a},pathlib.Path(d)/'c.jsonl',0.)
            v.publish(dict(kind='private',source_id='s',canonical_sha=a.sha256,steps=chain(a,b,c)))
            v.publish(dict(kind='canonical',source_id='s',state=new.state,processed_frontier=8));v.close()
            self.assertEqual(v.rows[-1]['visible_frontier'],8);self.assertIsNone(v.rows[-1]['private_job'])
    def test_recomputed_shorter_view_does_not_retract_existing_legal_ahead(self):
        a,b,c=state(0,''),state(8,'你'),state(16,'你好');mid=state(12,'你好')
        with scratch() as d:
            v=Consumer({'s':a},pathlib.Path(d)/'c.jsonl',0.)
            v.publish(dict(kind='private',source_id='s',canonical_sha=a.sha256,steps=chain(a,b,c)))
            v.publish(dict(kind='canonical',source_id='s',state=b.state,processed_frontier=8))
            v.publish(dict(kind='private',source_id='s',canonical_sha=b.sha256,steps=chain(b,mid)));v.close()
            self.assertEqual(v.rows[-1]['visible_frontier'],16)
    def test_queue_rejects_gapped_native_causal_chain(self):
        a,b,c=state(0,''),state(8,'你'),state(16,'你好')
        with scratch() as d:
            v=Consumer({'s':a},pathlib.Path(d)/'c.jsonl',0.)
            v.publish(dict(kind='private',source_id='s',canonical_sha=a.sha256,steps=chain(b,c)))
            with self.assertRaises(RuntimeError):v.close()
    def test_queue_rejects_wrong_canonical_binding(self):
        a,b=state(0,''),state(8,'你')
        with scratch() as d:
            v=Consumer({'s':a},pathlib.Path(d)/'c.jsonl',0.)
            v.publish(dict(kind='private',source_id='s',canonical_sha='wrong',steps=chain(a,b)))
            with self.assertRaises(RuntimeError):v.close()

if __name__=='__main__':unittest.main()
