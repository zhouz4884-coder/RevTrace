"""Host-clock sampling of both physical GPUs; no CUDA context is created."""
import json
from pathlib import Path
import subprocess
import threading
import time


def integrate(rows, start, end):
    assert rows and rows[0]["perf"] <= start <= end <= rows[-1]["perf"]
    energy = {0: 0., 1: 0.}
    for a, b in zip(rows, rows[1:]):
        lo, hi = max(start, a["perf"]), min(end, b["perf"])
        if hi <= lo:
            continue
        dt = b["perf"] - a["perf"]
        assert dt > 0
        for gpu in (0, 1):
            wa, wb = a["gpu"][str(gpu)]["watts"], b["gpu"][str(gpu)]["watts"]
            left = wa + (wb - wa) * (lo - a["perf"]) / dt
            right = wa + (wb - wa) * (hi - a["perf"]) / dt
            energy[gpu] += (left + right) * .5 * (hi - lo)
    return {"GPU0_joules": energy[0], "GPU1_joules": energy[1], "both_GPU_joules": sum(energy.values())}


class PowerSampler:
    def __init__(self, path):
        self.path = Path(path)
        assert not self.path.exists()
        self.rows, self.errors = [], []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        limit = time.monotonic() + 12
        while not self.rows and not self.errors and time.monotonic() < limit:
            time.sleep(.05)
        if self.errors or not self.rows:
            self.close()
            raise RuntimeError("GPU power sampler did not produce an actual observation: " + repr(self.errors))

    def _run(self):
        try:
            with self.path.open("x") as f:
                while not self.stop.is_set():
                    start = time.perf_counter()
                    text = subprocess.check_output(["nvidia-smi", "--query-gpu=index,power.draw,memory.used,utilization.gpu",
                        "--format=csv,noheader,nounits"], text=True, timeout=8)
                    end = time.perf_counter()
                    g = {}
                    for line in text.splitlines():
                        idx, watts, memory, util = [x.strip() for x in line.split(",")]
                        if idx in {"0", "1"}:
                            g[idx] = {"watts": float(watts), "memory_MiB": float(memory), "utilization_percent": float(util)}
                    assert set(g) == {"0", "1"}
                    row = {"perf": (start + end) / 2, "wall_ns": time.time_ns(), "query_seconds": end - start, "gpu": g}
                    self.rows.append(row); f.write(json.dumps(row) + "\n"); f.flush()
                    self.stop.wait(.25)
        except BaseException as exc:
            self.errors.append(repr(exc))

    def finish_interval(self, start, end):
        limit = time.monotonic() + 12
        while self.rows[-1]["perf"] < end and not self.errors and time.monotonic() < limit:
            time.sleep(.05)
        if self.errors or self.rows[-1]["perf"] < end:
            return {"status": "UNKNOWN_POWER_COVERAGE", "errors": self.errors}
        value = integrate(self.rows, start, end)
        return {"status": "MEASURED_BOTH_PHYSICAL_GPUS", **value,
                "window_seconds": end - start, "samples": len(self.rows),
                "peak_memory_MiB": {g: max(r["gpu"][g]["memory_MiB"] for r in self.rows) for g in ("0", "1")},
                "scope": "whole cell including required model loads, CPU/native/WAL waits and GPU idle power; not net inference-only energy"}

    def close(self):
        self.stop.set(); self.thread.join(timeout=10)

