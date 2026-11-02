"""Observer validity controls, not measurements or legal serving baselines."""
from __future__ import annotations
import json
import multiprocessing as mp
import os
import pathlib
import tempfile
import unittest
from cost_probe import CostProbe


def spawn_control(out):
    class Work:
        @staticmethod
        def call():
            return sum(i*i for i in range(50))
    probe=CostProbe(out,'spawn_control',True)
    probe.wrap(Work,'call','control.child')
    try:
        assert Work.call()==40425
    finally:
        probe.close()


class Controls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=pathlib.Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()

    def test_off_retains_original_callable_identity(self):
        class Work:
            @staticmethod
            def value(x):return x+1
        original=Work.value
        p=CostProbe(self.path,'off',False);p.wrap(Work,'value','unused')
        self.assertIs(Work.value,original);self.assertEqual(Work.value(8),9)
        p.close();self.assertEqual(len(p.rows),0)

    def test_nested_calls_are_not_additive_roots(self):
        class Work:
            @staticmethod
            def inner():return sum(i*i for i in range(1000))
            @staticmethod
            def outer():return Work.inner()+1
        p=CostProbe(self.path,'nested',True)
        p.wrap(Work,'inner','inner');p.wrap(Work,'outer','outer')
        self.assertEqual(Work.outer(),332833501);p.close()
        by={r['label']:r for r in p.rows}
        self.assertEqual(by['inner']['parent_span_id'],by['outer']['span_id'])
        self.assertLessEqual(by['outer']['exclusive_wall_ns'],by['outer']['wall_ns'])
        self.assertLessEqual(by['inner']['wall_ns'],by['outer']['wall_ns'])
        self.assertEqual(by['outer']['exclusive_wall_ns']+by['inner']['wall_ns'],by['outer']['wall_ns'])

    def test_same_exception_object_propagates_and_restores(self):
        problem=ValueError('same original failure')
        class Work:
            @staticmethod
            def fail():raise problem
        original=Work.fail;p=CostProbe(self.path,'exception',True);p.wrap(Work,'fail','fail')
        try:
            Work.fail()
        except ValueError as caught:
            self.assertIs(caught,problem)
        else:self.fail('observer swallowed exception')
        p.close();self.assertIs(Work.fail,original);self.assertTrue(p.rows[0]['exception'])

    def test_fsync_is_actual_original_syscall_and_bytes_survive(self):
        original=os.fsync;p=CostProbe(self.path/'spans','sync',True);p.wrap(os,'fsync','fsync')
        path=self.path/'real_file'
        try:
            with path.open('xb') as f:
                f.write(b'real complete original bytes');f.flush();os.fsync(f.fileno())
        finally:p.close()
        self.assertIs(os.fsync,original);self.assertEqual(path.read_bytes(),b'real complete original bytes')
        self.assertEqual(len(p.rows),1)

    def test_overflow_fails_study_not_original_work(self):
        class Work:
            @staticmethod
            def call():return 7
        p=CostProbe(self.path,'overflow',True,max_spans=1);p.wrap(Work,'call','call')
        self.assertEqual(Work.call(),7);self.assertEqual(Work.call(),7)
        with self.assertRaisesRegex(RuntimeError,'span limit'):p.close()
        self.assertTrue(p.overflow)

    def test_spawn_child_has_its_own_probe(self):
        proc=mp.get_context('spawn').Process(target=spawn_control,args=(str(self.path),))
        proc.start();proc.join(20)
        self.assertEqual(proc.exitcode,0)
        summaries=list(self.path.glob('*_SUMMARY.json'))
        self.assertEqual(len(summaries),1)
        row=json.loads(summaries[0].read_text(encoding='utf8'))
        self.assertEqual(row['pid'],proc.pid);self.assertNotEqual(row['pid'],os.getpid())
        self.assertEqual(row['span_count'],1)

    def test_parallel_thread_roots_not_nested(self):
        import threading
        class Work:
            @staticmethod
            def call():return sum(i for i in range(200))
        p=CostProbe(self.path,'threads',True);p.wrap(Work,'call','call')
        threads=[threading.Thread(target=Work.call) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join()
        p.close();self.assertEqual(len(p.rows),2)
        self.assertTrue(all(r['parent_span_id'] is None for r in p.rows))

if __name__=='__main__':
    unittest.main()
