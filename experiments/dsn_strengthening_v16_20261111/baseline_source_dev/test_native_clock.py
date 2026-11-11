import types,unittest
from unittest import mock
import numpy as np
from native_bridge import NativeBridge,export_cut
from test_native_bridge import Engine

class ClockContract(unittest.TestCase):
    def test_author_wall_clock_and_service_monotonic_clock_stay_separate(self):
        model=NativeBridge.__new__(NativeBridge);model.role='private';model.contract={};model.corrector_model=object();model.corrector_processor=None
        model.engine=Engine();model.engine.insert_audio=mock.Mock();model.engine.infer=mock.Mock(return_value=([100],{}));model.engine.tokenizer=types.SimpleNamespace(decode=lambda ids:'中')
        initial=export_cut(model.engine,frontier=0,transcript='',contract={})
        with mock.patch('native_bridge.restore_cut'),mock.patch('native_bridge.export_cut',return_value=initial),mock.patch('torch.cuda.synchronize'),mock.patch('native_bridge.time.perf_counter',side_effect=[10.,12.]),mock.patch('native_bridge.time.time',return_value=1712345.67):
            _,row=model.step(audio=np.zeros(16000,dtype=np.float32),start=initial,end=16000,is_last=False)
        self.assertEqual(model.engine.infer.call_args.kwargs['start_time'],1712345.67)
        self.assertEqual((row['model_start'],row['model_end'],row['model_seconds']),(10.,12.,2.))
        self.assertEqual(row['clock_domains'],dict(service_and_model='perf_counter',author_telemetry='time.time'))

if __name__=='__main__':unittest.main()
