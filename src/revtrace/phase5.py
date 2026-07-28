"""Phase 5 control and measurement primitives.

The helpers in this module deliberately separate three evidence tiers:

* online contract control, where an epoch switch invalidates all old evidence;
* physical slack admission, where a non-preemptive audit is launched only when
  it fits before the next mandatory release; and
* consequential-pair bookkeeping, which measures observed damage without
  turning a targeted corpus into a prevalence estimate.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from .risk_window import WindowCertificate, certify_risk_window


class NvidiaPowerSampler:
    """Low-rate physical-GPU power sampler backed by nvidia-smi."""

    def __init__(
        self,
        gpu_ids: Sequence[int],
        *,
        interval_seconds: float = 0.1,
    ) -> None:
        self.gpu_ids = {int(value) for value in gpu_ids}
        self.interval_seconds = float(interval_seconds)
        self.samples: list[dict[str, float]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        started = time.perf_counter()

        def collect() -> None:
            while not self._stop.is_set():
                completed = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=index,power.draw",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                total = 0.0
                if completed.returncode == 0:
                    for line in completed.stdout.splitlines():
                        fields = [
                            item.strip() for item in line.split(",")
                        ]
                        if (
                            len(fields) == 2
                            and int(fields[0]) in self.gpu_ids
                        ):
                            total += float(fields[1])
                    self.samples.append(
                        {
                            "time": time.perf_counter() - started,
                            "power_watts": total,
                        }
                    )
                self._stop.wait(self.interval_seconds)

        self._thread = threading.Thread(target=collect, daemon=True)
        self._thread.start()

    def stop(self) -> list[dict[str, float]]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        return list(self.samples)


@dataclass
class ContractEpoch:
    fingerprint: str
    epoch: int
    switched_at_event: int
    threshold: float | None = None
    fast_path_window: float = 0.0
    certificate: WindowCertificate | None = None
    audit_records: list[dict[str, object]] = field(default_factory=list)
    certified_at_event: int | None = None


class LiveRiskWindowController:
    """Fail-closed split-sample controller for live contract epochs."""

    def __init__(
        self,
        *,
        minimum_audits: int = 1350,
        delta: float = 0.005,
        alpha: float = 0.05,
        calibration_fraction: float = 0.55,
    ) -> None:
        if minimum_audits < 2:
            raise ValueError("minimum_audits must be at least two")
        self.minimum_audits = minimum_audits
        self.delta = delta
        self.alpha = alpha
        self.calibration_fraction = calibration_fraction
        self.event_index = 0
        self.current: ContractEpoch | None = None
        self.history: list[ContractEpoch] = []

    def switch(self, fingerprint: str) -> ContractEpoch:
        """Start a fresh fail-closed epoch; no prior evidence is reused."""

        if self.current is not None:
            self.history.append(self.current)
        epoch = len(self.history) + 1
        self.current = ContractEpoch(
            fingerprint=fingerprint,
            epoch=epoch,
            switched_at_event=self.event_index,
        )
        return self.current

    def observe(
        self,
        *,
        minimum_margin: float,
        state_error: bool,
    ) -> WindowCertificate | None:
        if self.current is None:
            raise RuntimeError("switch() must be called before observe()")
        self.event_index += 1
        self.current.audit_records.append(
            {
                "minimum_margin": float(minimum_margin),
                "state_error": bool(state_error),
            }
        )
        if self.current.certificate is not None:
            return self.current.certificate
        if len(self.current.audit_records) < self.minimum_audits:
            return None
        certificate = certify_risk_window(
            self.current.audit_records,
            delta=self.delta,
            alpha=self.alpha,
            calibration_fraction=self.calibration_fraction,
        )
        if certificate.certified:
            self.current.certificate = certificate
            self.current.threshold = certificate.threshold
            self.current.fast_path_window = certificate.fast_path_window
            self.current.certified_at_event = self.event_index
        return certificate

    @property
    def fail_closed(self) -> bool:
        return self.current is None or self.current.certificate is None

    def requires_verification(
        self,
        *,
        minimum_margin: float | None,
        terminal: bool,
    ) -> bool:
        if terminal or self.fail_closed or minimum_margin is None:
            return True
        assert self.current is not None
        assert self.current.threshold is not None
        return float(minimum_margin) <= self.current.threshold


def adaptation_regret(
    goodput: Sequence[float],
    oracle_goodput: Sequence[float],
    durations: Sequence[float],
) -> float:
    """Piecewise-constant adaptation regret area."""

    if not (
        len(goodput) == len(oracle_goodput) == len(durations)
    ):
        raise ValueError("all trajectories must have equal length")
    return sum(
        max(0.0, float(oracle) - float(actual)) * float(duration)
        for actual, oracle, duration in zip(
            goodput, oracle_goodput, durations
        )
    )


def release_aware_audit_admissible(
    *,
    now: float,
    verifier_backlog_seconds: float,
    audit_p99_seconds: float,
    guard_seconds: float,
    next_mandatory_release: float,
) -> bool:
    """Admission test for a non-preemptive full-request audit."""

    values = (
        now,
        verifier_backlog_seconds,
        audit_p99_seconds,
        guard_seconds,
        next_mandatory_release,
    )
    if any(not math.isfinite(float(value)) for value in values):
        raise ValueError("slack inputs must be finite")
    if any(
        float(value) < 0.0
        for value in (
            verifier_backlog_seconds,
            audit_p99_seconds,
            guard_seconds,
        )
    ):
        raise ValueError("costs and guard must be non-negative")
    return (
        float(now)
        + float(verifier_backlog_seconds)
        + float(audit_p99_seconds)
        + float(guard_seconds)
        < float(next_mandatory_release)
    )


def pair_digest(payload: Mapping[str, object]) -> str:
    """Stable corpus identity over the semantic pair fields."""

    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def contamination_damage(
    *,
    state_disagreement: bool,
    raf: float,
    persistent: bool,
    terminal_difference: bool,
) -> float:
    """Observed damage score; not a probability or production expectation."""

    if not state_disagreement:
        return 0.0
    value = max(1.0, float(raf))
    if persistent:
        value *= 2.0
    if terminal_difference:
        value *= 2.0
    return value


def clopper_zero_upper(sample_size: int, alpha: float = 0.05) -> float:
    """Explicit zero-failure upper bound used in Phase 5 reports."""

    if sample_size <= 0:
        return 1.0
    return 1.0 - alpha ** (1.0 / sample_size)


def summarize_energy(
    samples: Iterable[Mapping[str, float]],
    *,
    completed_audio_seconds: float,
) -> dict[str, float]:
    """Trapezoidal integration of total GPU power samples."""

    rows = sorted(
        (
            {
                "time": float(row["time"]),
                "power_watts": float(row["power_watts"]),
            }
            for row in samples
        ),
        key=lambda row: row["time"],
    )
    joules = 0.0
    for left, right in zip(rows, rows[1:]):
        elapsed = max(0.0, right["time"] - left["time"])
        joules += elapsed * (
            left["power_watts"] + right["power_watts"]
        ) / 2.0
    return {
        "sample_count": float(len(rows)),
        "joules": joules,
        "completed_audio_seconds": float(completed_audio_seconds),
        "joules_per_audio_second": (
            joules / float(completed_audio_seconds)
            if completed_audio_seconds > 0
            else math.inf
        ),
    }
