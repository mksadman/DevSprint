import logging
import threading
from dataclasses import dataclass, field
from typing import List


logger = logging.getLogger(__name__)


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
            self._latencies_ms.append(latency_ms)
            if len(self._latencies_ms) > 1000:
                self._latencies_ms = self._latencies_ms[-1000:]

    def snapshot(self) -> dict:
        with self._lock:
            avg = (
                sum(self._latencies_ms) / len(self._latencies_ms)
                if self._latencies_ms
                else 0.0
            )
            return {
                "total_orders": self._total_orders,
                "successful_orders": self._successful_orders,
                "rejected_orders": self._rejected_orders,
                "auth_failures": self._auth_failures,
                "cache_short_circuits": self._cache_short_circuits,
                "downstream_failures": self._downstream_failures,
                "average_response_time_ms": round(avg, 3),
            }


metrics = _Metrics()
