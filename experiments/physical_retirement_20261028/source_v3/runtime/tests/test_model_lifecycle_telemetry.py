"""CPU interface test; no model or GPU timing claim."""
import importlib.util,queue
from pathlib import Path
spec=importlib.util.spec_from_file_location('lifecycle_worker',Path(__file__).resolve().parents[1]/'scripts/tc_live_worker.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_distinguishes_worker_preprocess_model_and_postprocess():
    worker=object.__new__(m.GPUExecutor);worker.results=queue.Queue();worker._held_result=None;worker._telemetry=[]
    for kind,phase in [('batch-started','preprocessing'),('model-started','model-executing'),('model-completed','postprocessing')]:
        worker.results.put({'kind':kind,'job_ids':['p1']})
        assert worker.poll() is None and worker.execution_phase==phase
    assert [r['kind'] for r in worker.drain_telemetry()]==['batch-started','model-started','model-completed']
