metrics: dict = {
    "total_requests": 0,
    "total_deductions": 0,
    "failed_deductions": 0,
    "total_latency_ms": 0.0,
    "request_count_per_route": {},
}


def record_request(path: str, process_time_ms: float) -> None:
    metrics["total_requests"] += 1
    metrics["total_latency_ms"] += process_time_ms
    if path not in metrics["request_count_per_route"]:
        metrics["request_count_per_route"][path] = 0
    metrics["request_count_per_route"][path] += 1


def record_deduction(failed: bool = False) -> None:
    metrics["total_deductions"] += 1
    if failed:
        metrics["failed_deductions"] += 1


def get_snapshot() -> dict:
    avg_latency = 0.0
    if metrics["total_requests"] > 0:
        avg_latency = metrics["total_latency_ms"] / metrics["total_requests"]
    return {
        "total_requests": metrics["total_requests"],
        "total_deductions": metrics["total_deductions"],
        "failed_deductions": metrics["failed_deductions"],
        "average_latency_ms": round(avg_latency, 2),
        "request_count_per_route": metrics["request_count_per_route"],
    }
