"""Development-only spawn wiring probe, substituting no neural evidence."""
import json
import os


def probe(context, event, result_pipe, report):
    import stage_worker
    from buffer_fixture import timing_worker_entry, SPEC_ENV, FixtureError
    os.environ[SPEC_ENV] = json.dumps(context)
    def synthetic_worker(name, gpu, mode, settings, commands, results, hints):
        report.put(dict(kind="sender_class", value=type(results).__name__, neural_calls=0))
        results.put(event)
    stage_worker.worker_main = synthetic_worker
    try:
        timing_worker_entry("full1", 1, {}, None, result_pipe, None, None, 0,
                            dict(kind="none"), None, None)
    except FixtureError as exc:
        report.put(dict(kind="expected_cpu_timeout", value=str(exc), neural_calls=0))
    else:
        report.put(dict(kind="unexpected_return", neural_calls=0))
    finally:
        result_pipe.close()
