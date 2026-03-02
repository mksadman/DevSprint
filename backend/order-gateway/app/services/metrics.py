import logging
import threading
import time
from dataclasses import dataclass, field
from typing import List, Tuple


logger = logging.getLogger(__name__)

_ROLLING_WINDOW_SECONDS: float = 30.0
_LATENCY_ALERT_THRESHOLD_MS: float = 1000.0


@dataclass
class _Metrics:
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _total_orders: int = 0
    _successful_orders: int = 0
    _rejected_orders: int = 0
    _auth_failures: int = 0
    _cache_short_circuits: int = 0
    _downstream_failures: int = 0
    _latencies_ms: List[float] = field(default_factory=list)
    # Each entry: (monotonic_timestamp, latency_ms)
    _rolling_window: List[Tuple[float, float]] = field(default_factory=list)

    def increment_total_attempts(self) -> None:
        with self._lock:
            self._total_orders += 1

    def increment_successful(self) -> None:
        with self._lock:
            self._successful_orders += 1

    def increment_rejected(self) -> None:
        with self._lock:
            self._rejected_orders += 1

    def increment_auth_failures(self) -> None:
        with self._lock:
            self._auth_failures += 1

    def increment_cache_short_circuits(self) -> None:
        with self._lock:
            self._cache_short_circuits += 1

    def increment_downstream_failures(self) -> None:
        with self._lock:
            self._downstream_failures += 1

    def record_latency(self, latency_ms: float) -> None:
        with self._lock:
            now = time.monotonic()
            # All-time list (capped at 1 000 entries)
            self._latencies_ms.append(latency_ms)
            if len(self._latencies_ms) > 1000:
                self._latencies_ms = self._latencies_ms[-1000:]
            # Rolling 30-second window
            self._rolling_window.append((now, latency_ms))
            cutoff = now - _ROLLING_WINDOW_SECONDS
            self._rolling_window = [
                (ts, ms) for ts, ms in self._rolling_window if ts >= cutoff
            ]

    def snapshot(self) -> dict:
        with self._lock:
            avg = (
                sum(self._latencies_ms) / len(self._latencies_ms)
                if self._latencies_ms
                else 0.0
            )
            # Rolling-window average (only entries within the last 30 s)
            now = time.monotonic()
            cutoff = now - _ROLLING_WINDOW_SECONDS
            recent = [ms for ts, ms in self._rolling_window if ts >= cutoff]
            rolling_avg = sum(recent) / len(recent) if recent else 0.0
            latency_alert = rolling_avg > _LATENCY_ALERT_THRESHOLD_MS

            return {
                "total_orders": self._total_orders,
                "successful_orders": self._successful_orders,
                "rejected_orders": self._rejected_orders,
                "auth_failures": self._auth_failures,
                "cache_short_circuits": self._cache_short_circuits,
                "downstream_failures": self._downstream_failures,
                "average_response_time_ms": round(avg, 3),
                "rolling_window_avg_ms": round(rolling_avg, 3),
                "latency_alert": latency_alert,
            }


metrics = _Metrics()
