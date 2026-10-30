import json,pathlib,tempfile,unittest
from diagnose_long_memory import DurableRows,failure_start
class Cut:
 state={'frontier':752000,'scope':'synthetic CPU fixture only'}
def continuous_transitions():
 start=Cut();end=760000;previous=752000
 raise MemoryError('synthetic CPU exception, no CUDA/model')
class Controls(unittest.TestCase):
 def test_durable_complete_row_survives_close(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'rows';w=DurableRows(p);w.write({'a':1});self.assertEqual(w.count,1);self.assertEqual(json.loads(p.read_bytes()),{'a':1});w.close()
 def test_append_forbidden(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'rows';w=DurableRows(p);w.close()
   with self.assertRaises(FileExistsError):DurableRows(p)
 def test_complete_failure_input_from_actual_failing_frame(self):
  try:continuous_transitions()
  except MemoryError as e:self.assertEqual(failure_start(e.__traceback__),{'start':Cut.state,'end':760000,'previous':752000})
 def test_unrelated_failure_cannot_invent_a_cut(self):
  try:raise MemoryError('synthetic')
  except MemoryError as e:self.assertIsNone(failure_start(e.__traceback__))
 def test_none_has_no_failure_cut(self):self.assertIsNone(failure_start(None))
if __name__=='__main__':unittest.main()
