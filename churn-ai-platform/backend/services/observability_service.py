from __future__ import annotations

import math
import os
import time
from collections import deque
from dataclasses import dataclass


@dataclass
class _RequestEvent:
    ts: float
    duration_ms: float
    status_code: int


class ObservabilityService:
    def __init__(self) -> None:
        self._started_at = time.time()
        self._window_seconds = int(os.getenv("OBSERVABILITY_WINDOW_SECONDS", "300"))
        self._events: deque[_RequestEvent] = deque()

        self._latency_slo_ms = float(os.getenv("SLO_LATENCY_P95_MS", "500"))
        self._error_rate_slo = float(os.getenv("SLO_ERROR_RATE_MAX", "0.01"))
        self._uptime_slo_percent = float(os.getenv("SLO_UPTIME_PERCENT", "99.9"))

    def uptime_seconds(self) -> float:
        return round(time.time() - self._started_at, 3)

    def _trim(self) -> None:
        threshold = time.time() - self._window_seconds
        while self._events and self._events[0].ts < threshold:
            self._events.popleft()

    def record_request(self, duration_ms: float, status_code: int) -> None:
        self._events.append(_RequestEvent(ts=time.time(), duration_ms=duration_ms, status_code=status_code))
        self._trim()

    def request_summary(self) -> dict[str, float | int]:
        self._trim()
        if not self._events:
            return {
                "window_seconds": self._window_seconds,
                "request_count": 0,
                "error_count": 0,
                "error_rate": 0.0,
                "latency_p95_ms": 0.0,
                "latency_avg_ms": 0.0,
            }

        latencies = sorted(event.duration_ms for event in self._events)
        idx = max(0, min(len(latencies) - 1, math.ceil(0.95 * len(latencies)) - 1))
        error_count = sum(1 for event in self._events if event.status_code >= 500)
        request_count = len(self._events)

        return {
            "window_seconds": self._window_seconds,
            "request_count": request_count,
            "error_count": error_count,
            "error_rate": error_count / request_count,
            "latency_p95_ms": round(latencies[idx], 3),
            "latency_avg_ms": round(sum(latencies) / request_count, 3),
        }

    def slo_status(self, dependencies_ok: bool) -> dict[str, object]:
        summary = self.request_summary()
        latency_p95_ms = float(summary["latency_p95_ms"])
        error_rate = float(summary["error_rate"])
        uptime_percent = 100.0 if dependencies_ok else 0.0

        latency_ok = latency_p95_ms <= self._latency_slo_ms if int(summary["request_count"]) > 0 else True
        error_rate_ok = error_rate <= self._error_rate_slo
        uptime_ok = uptime_percent >= self._uptime_slo_percent

        return {
            "targets": {
                "latency_p95_ms": self._latency_slo_ms,
                "error_rate_max": self._error_rate_slo,
                "uptime_percent": self._uptime_slo_percent,
            },
            "current": {
                "latency_p95_ms": latency_p95_ms,
                "error_rate": round(error_rate, 6),
                "uptime_percent": uptime_percent,
            },
            "status": {
                "latency_ok": latency_ok,
                "error_rate_ok": error_rate_ok,
                "uptime_ok": uptime_ok,
                "overall_ok": latency_ok and error_rate_ok and uptime_ok,
            },
            "window_seconds": summary["window_seconds"],
            "request_count": summary["request_count"],
        }


observability_service = ObservabilityService()